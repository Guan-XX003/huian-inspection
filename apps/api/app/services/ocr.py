from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
from typing import Any, Optional

from app.config import get_settings


class OCRAdapter:
    def analyze(self, file_path: str) -> dict:
        path = Path(file_path)
        if path.suffix.lower() in {".txt", ".csv"}:
            text = self._read_text(path)
            if text:
                return {
                    "provider": "text-reader",
                    "text": text,
                    "average_confidence": 0.98,
                    "blocks": [
                        {"text": line, "position": "text", "confidence": 0.98}
                        for line in text.splitlines()
                        if line.strip()
                    ],
                    "tables": [],
                }
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
            result = self._analyze_image(path)
            if result:
                return result
        return {
            "provider": "unavailable",
            "text": "",
            "average_confidence": 0,
            "blocks": [],
            "tables": [],
            "warning": "未安装可用 OCR 引擎，图片文字需由视觉模型识别；无视觉模型时必须人工复核。",
        }

    def _analyze_image(self, path: Path) -> Optional[dict]:
        settings = get_settings()
        provider = settings.ocr_provider.lower()
        candidates: list[dict[str, Any]] = []
        temp_paths: list[Path] = []

        try:
            variants, temp_paths = self._image_variants(path)
            original = variants[0][1] if variants else path
            variant_map = dict(variants)
            enhanced = variant_map.get("enhanced", original)
            if platform.system() == "Windows" and provider in {"auto", "cascade", "multi"}:
                # Windows desktop builds should favor lightweight local OCR first.
                self._append_candidate(candidates, self._try_rapidocr(original))
                self._append_candidate(candidates, self._try_rapidocr(enhanced))
                self._append_candidate(candidates, self._try_paddleocr(original))
                self._append_candidate(candidates, self._try_tesseract(original))
                self._append_candidate(candidates, self._try_tesseract(enhanced))
            else:
                if provider in {"auto", "cascade", "multi", "paddleocr", "paddle"}:
                    self._append_candidate(candidates, self._try_paddleocr(original))
                if provider in {"auto", "cascade", "multi", "rapidocr", "rapid"}:
                    self._append_candidate(candidates, self._try_rapidocr(original))
                    if provider in {"auto", "cascade", "multi"}:
                        self._append_candidate(candidates, self._try_rapidocr(enhanced))
                if provider in {"auto", "cascade", "multi", "tesseract"}:
                    self._append_candidate(candidates, self._try_tesseract(original))
                    if provider in {"auto", "cascade", "multi"}:
                        self._append_candidate(candidates, self._try_tesseract(enhanced))
            if provider in {"auto", "cascade", "multi", "macos", "macos-vision", "vision"} or platform.system() == "Darwin":
                for variant_name, variant_path in variants:
                    self._append_candidate(candidates, self._try_macos_vision(variant_path, variant_name))
            if provider in {"auto", "cascade", "multi"} and self._needs_region_ocr(candidates):
                for region_name, region_path in self._region_variants(path, temp_paths):
                    self._append_candidate(candidates, self._with_region_name(self._try_rapidocr(region_path), region_name))
                    self._append_candidate(candidates, self._with_region_name(self._try_macos_vision(region_path, region_name), region_name))
        finally:
            for temp_path in temp_paths:
                try:
                    temp_path.unlink()
                except Exception:
                    pass

        return self._best_result(candidates)

    def _append_candidate(self, candidates: list[dict[str, Any]], result: Optional[dict]) -> None:
        if not result or not str(result.get("text", "")).strip():
            return
        result["quality_score"] = self._ocr_quality_score(result)
        candidates.append(result)

    def _with_region_name(self, result: Optional[dict], region_name: str) -> Optional[dict]:
        if result:
            result["provider"] = f"{result.get('provider', 'ocr')}:{region_name}"
        return result

    def _needs_region_ocr(self, candidates: list[dict[str, Any]]) -> bool:
        if not candidates:
            return True
        best = max(candidates, key=lambda item: float(item.get("quality_score", 0)))
        text = str(best.get("text", ""))
        important_keywords = ["产品名称", "配料", "净含量", "生产日期", "保质期", "贮存", "许可证", "执行标准"]
        hits = sum(1 for keyword in important_keywords if keyword in text)
        return hits < 7 or len(text) < 900

    def _best_result(self, candidates: list[dict[str, Any]]) -> Optional[dict]:
        if not candidates:
            return None
        ranked = sorted(candidates, key=lambda item: float(item.get("quality_score", 0)), reverse=True)
        best = ranked[0]
        merged = self._merge_candidates(ranked[:6])
        candidate_summary = [
            {
                "provider": item.get("provider", ""),
                "confidence": item.get("average_confidence", 0),
                "text_length": len(str(item.get("text", ""))),
                "quality_score": round(float(item.get("quality_score", 0)), 3),
            }
            for item in ranked
        ]
        best_keyword_hits = self._important_keyword_hits(str(best.get("text", "")))
        merged_keyword_hits = self._important_keyword_hits(str(merged.get("text", ""))) if merged else 0
        if merged and (
            len(merged["text"]) > len(str(best.get("text", ""))) * 1.08
            or merged_keyword_hits > best_keyword_hits
        ):
            merged["provider"] = f"ocr-cascade:{'+'.join(str(item.get('provider', 'ocr')) for item in ranked[:3])}"
            merged["average_confidence"] = max(float(item.get("average_confidence", 0)) for item in ranked[:6])
            merged["quality_score"] = self._ocr_quality_score(merged)
            merged["ocr_candidates"] = candidate_summary
            return merged
        best = dict(best)
        best["ocr_candidates"] = candidate_summary
        return best

    def _ocr_quality_score(self, result: dict[str, Any]) -> float:
        text = str(result.get("text", ""))
        confidence = float(result.get("average_confidence", 0) or 0)
        useful_chars = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))
        line_count = len([line for line in text.splitlines() if line.strip()])
        keywords = [
            "产品名称",
            "配料",
            "营养成分",
            "净含量",
            "生产日期",
            "保质期",
            "贮存",
            "生产商",
            "地址",
            "许可证",
            "执行标准",
            "SC",
            "能量",
            "蛋白质",
            "脂肪",
            "钠",
        ]
        keyword_hits = self._important_keyword_hits(text)
        return min(useful_chars / 1500, 1) * 0.45 + confidence * 0.35 + min(keyword_hits / 12, 1) * 0.16 + min(line_count / 40, 1) * 0.04

    def _important_keyword_hits(self, text: str) -> int:
        keywords = [
            "产品名称",
            "配料",
            "营养成分",
            "净含量",
            "生产日期",
            "保质期",
            "贮存",
            "生产商",
            "地址",
            "许可证",
            "执行标准",
            "SC",
            "能量",
            "蛋白质",
            "脂肪",
            "钠",
        ]
        return sum(1 for keyword in keywords if keyword in text)

    def _merge_candidates(self, candidates: list[dict[str, Any]]) -> Optional[dict]:
        if not candidates:
            return None
        lines: list[str] = []
        seen: set[str] = set()
        blocks: list[dict[str, Any]] = []
        for candidate in candidates:
            for block in candidate.get("blocks", []):
                text = str(block.get("text", "")).strip()
                if not text:
                    continue
                normalized = self._normalize_line_for_merge(text)
                if not normalized or normalized in seen:
                    continue
                if any(normalized in existing or existing in normalized for existing in seen if len(normalized) > 5 and len(existing) > 5):
                    continue
                seen.add(normalized)
                lines.append(text)
                blocks.append({**block, "provider": candidate.get("provider", "")})
        if not lines:
            return None
        return {
            "provider": "ocr-cascade",
            "text": "\n".join(lines),
            "average_confidence": candidates[0].get("average_confidence", 0.75),
            "blocks": blocks,
            "tables": [],
        }

    def _normalize_line_for_merge(self, line: str) -> str:
        return re.sub(r"\W+", "", line.lower())

    def _image_variants(self, path: Path) -> tuple[list[tuple[str, Path]], list[Path]]:
        variants: list[tuple[str, Path]] = [("original", path)]
        temp_paths: list[Path] = []
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        except Exception:
            return variants, temp_paths

        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                width, height = image.size
                longest = max(width, height)
                scale = 1.0
                if longest < 1800:
                    scale = min(2.0, 1800 / max(longest, 1))
                elif longest > 2600:
                    scale = 2600 / longest
                resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale)))) if scale != 1.0 else image.copy()
                grayscale = ImageOps.grayscale(resized)
                enhanced = ImageOps.autocontrast(grayscale)
                enhanced = ImageEnhance.Contrast(enhanced).enhance(1.35)
                enhanced = enhanced.filter(ImageFilter.SHARPEN)
                threshold = enhanced.point(lambda pixel: 255 if pixel > 175 else 0)
                for name, variant in [("enhanced", enhanced), ("threshold", threshold)]:
                    temp = Path(tempfile.NamedTemporaryFile(suffix=f"-{name}.png", delete=False).name)
                    variant.save(temp)
                    temp_paths.append(temp)
                    variants.append((name, temp))
        except Exception:
            return variants, temp_paths
        return variants, temp_paths

    def _region_variants(self, path: Path, temp_paths: list[Path]) -> list[tuple[str, Path]]:
        regions: list[tuple[str, Path]] = []
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        except Exception:
            return regions

        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                width, height = image.size
                boxes = {
                    "label-bottom": (0, int(height * 0.46), width, height),
                    "label-left": (0, int(height * 0.36), int(width * 0.58), int(height * 0.86)),
                    "label-right": (int(width * 0.42), int(height * 0.36), width, int(height * 0.86)),
                }
                for name, box in boxes.items():
                    cropped = image.crop(box)
                    longest = max(cropped.size)
                    scale = min(2.2, max(1.0, 1700 / max(longest, 1)))
                    if scale > 1:
                        cropped = cropped.resize((int(cropped.width * scale), int(cropped.height * scale)))
                    grayscale = ImageOps.grayscale(cropped)
                    enhanced = ImageOps.autocontrast(grayscale)
                    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.45)
                    enhanced = enhanced.filter(ImageFilter.SHARPEN)
                    temp = Path(tempfile.NamedTemporaryFile(suffix=f"-{name}.png", delete=False).name)
                    enhanced.save(temp)
                    temp_paths.append(temp)
                    regions.append((name, temp))
        except Exception:
            return regions
        return regions

    def _try_paddleocr(self, path: Path) -> Optional[dict]:
        provider = get_settings().ocr_provider.lower()
        if provider not in {"auto", "cascade", "multi", "paddleocr", "paddle"}:
            return None
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except Exception:
            return None

        try:
            engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            raw_result = engine.ocr(str(path), cls=True)
        except Exception:
            return None

        blocks = self._normalize_paddle_result(raw_result)
        text = "\n".join(block["text"] for block in blocks if block.get("text"))
        if not text.strip():
            return None
        confidence_values = [float(block["confidence"]) for block in blocks if block.get("confidence") is not None]
        average_confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else 0.86
        return {
            "provider": "paddleocr",
            "text": text,
            "average_confidence": average_confidence,
            "blocks": blocks,
            "tables": [],
        }

    def _try_rapidocr(self, path: Path) -> Optional[dict]:
        try:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore
            except Exception:
                from rapidocr import RapidOCR  # type: ignore
        except Exception:
            return None

        try:
            engine = RapidOCR()
            raw_result, _ = engine(str(path))
        except Exception:
            return None

        blocks = []
        for item in raw_result or []:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            position = item[0]
            text = str(item[1]).strip()
            confidence = float(item[2]) if len(item) > 2 and item[2] is not None else 0.82
            if text:
                blocks.append({"text": text, "position": position, "confidence": confidence})
        text = "\n".join(block["text"] for block in blocks)
        if not text.strip():
            return None
        confidence_values = [float(block["confidence"]) for block in blocks]
        average_confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else 0.82
        return {
            "provider": "rapidocr",
            "text": text,
            "average_confidence": average_confidence,
            "blocks": blocks,
            "tables": [],
        }

    def _try_tesseract(self, path: Path) -> Optional[dict]:
        if not shutil.which("tesseract"):
            return None
        command = ["tesseract", str(path), "stdout", "-l", "chi_sim+eng", "--psm", "6", "tsv"]
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=45)
        except Exception:
            return None
        if completed.returncode != 0:
            return None
        blocks = []
        for line in completed.stdout.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 12:
                continue
            text = parts[11].strip()
            if not text:
                continue
            try:
                confidence = max(0, float(parts[10]) / 100)
            except ValueError:
                confidence = 0.65
            blocks.append({"text": text, "position": "tesseract", "confidence": confidence})
        if not blocks:
            return None
        text = "\n".join(block["text"] for block in blocks)
        confidence_values = [float(block["confidence"]) for block in blocks]
        average_confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else 0.65
        return {
            "provider": "tesseract",
            "text": text,
            "average_confidence": average_confidence,
            "blocks": blocks,
            "tables": [],
        }

    def _normalize_paddle_result(self, raw_result: Any) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        pages = raw_result if isinstance(raw_result, list) else [raw_result]
        for page in pages:
            lines = page if isinstance(page, list) else []
            for line in lines:
                if not isinstance(line, (list, tuple)) or len(line) < 2:
                    continue
                position = line[0]
                payload = line[1]
                if isinstance(payload, (list, tuple)) and payload:
                    text = str(payload[0])
                    confidence = float(payload[1]) if len(payload) > 1 and payload[1] is not None else 0.86
                else:
                    text = str(payload)
                    confidence = 0.86
                if text.strip():
                    blocks.append({"text": text.strip(), "position": position, "confidence": confidence})
        return blocks

    def _try_macos_vision(self, path: Path, variant_name: str = "original") -> Optional[dict]:
        if platform.system() != "Darwin":
            return None
        swift = self._swift_ocr_source()
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".swift", encoding="utf-8", delete=False) as script:
                script.write(swift)
                script_path = Path(script.name)
            completed = subprocess.run(
                ["/usr/bin/swift", str(script_path), str(path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception:
            return None
        finally:
            try:
                script_path.unlink()
            except Exception:
                pass

        if completed.returncode != 0:
            return None
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return None
        blocks = []
        confidences = []
        for line in lines:
            if "\t" in line:
                confidence_text, text = line.split("\t", 1)
                try:
                    confidence = float(confidence_text)
                except ValueError:
                    confidence = 0.82
            else:
                text = line
                confidence = 0.82
            if text.strip():
                blocks.append({"text": text.strip(), "position": "vision", "confidence": confidence})
                confidences.append(confidence)
        if not blocks:
            return None
        average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.82
        return {
            "provider": f"macos-vision:{variant_name}",
            "text": "\n".join(block["text"] for block in blocks),
            "average_confidence": average_confidence,
            "blocks": blocks,
            "tables": [],
        }

    def _swift_ocr_source(self) -> str:
        return r'''
import Foundation
import Vision
import AppKit

let path = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
guard let image = NSImage(contentsOfFile: path),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    exit(2)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
if #available(macOS 11.0, *) {
    request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
}

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
    let observations = request.results ?? []
    for observation in observations {
        if let candidate = observation.topCandidates(1).first {
            print("\(candidate.confidence)\t\(candidate.string)")
        }
    }
} catch {
    exit(3)
}
'''

    def _read_text(self, path: Path) -> str:
        content = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return ""


def get_ocr_adapter() -> OCRAdapter:
    return OCRAdapter()
