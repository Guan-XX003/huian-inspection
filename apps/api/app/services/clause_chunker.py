import re
from dataclasses import dataclass


HEADING_PATTERN = re.compile(
    r"^\s*((?:第[一二三四五六七八九十百]+[章节条])|(?:附录\s*[A-ZＡ-Ｚ])|(?:\d+(?:\.\d+){0,4}))\s+(.{2,120})\s*$"
)


@dataclass
class ClauseChunk:
    clause_no: str
    title: str
    content: str
    page_no: str = ""


def chunk_standard_text(text: str, max_chars: int = 1800) -> list[ClauseChunk]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    heading_chunks = _chunk_by_headings(normalized, max_chars)
    if len(heading_chunks) >= 2:
        return heading_chunks
    return _chunk_by_length(normalized, max_chars)


def _normalize_text(text: str) -> str:
    lines = []
    for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"\d+\s*/\s*\d+", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _chunk_by_headings(text: str, max_chars: int) -> list[ClauseChunk]:
    chunks: list[ClauseChunk] = []
    current_no = "全文"
    current_title = "全文切片"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        content = "\n".join(current_lines).strip()
        if not content:
            return
        for index, part in enumerate(_split_long_content(content, max_chars)):
            suffix = f".{index + 1}" if index else ""
            chunks.append(ClauseChunk(current_no + suffix, current_title, part))
        current_lines = []

    for line in text.split("\n"):
        match = HEADING_PATTERN.match(line)
        if match and not _looks_like_table_row(line):
            flush()
            current_no = match.group(1).strip()
            current_title = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()
    return chunks


def _chunk_by_length(text: str, max_chars: int) -> list[ClauseChunk]:
    chunks = []
    for index, part in enumerate(_split_long_content(text, max_chars), 1):
        chunks.append(ClauseChunk(f"全文-{index}", "全文切片", part))
    return chunks


def _split_long_content(content: str, max_chars: int) -> list[str]:
    if len(content) <= max_chars:
        return [content]
    parts = []
    buffer = ""
    for paragraph in re.split(r"(?<=。|；|;|\.)\s*", content):
        if not paragraph:
            continue
        if len(buffer) + len(paragraph) > max_chars and buffer:
            parts.append(buffer.strip())
            buffer = paragraph
        else:
            buffer = f"{buffer}\n{paragraph}" if buffer else paragraph
    if buffer:
        parts.append(buffer.strip())
    return parts or [content[:max_chars]]


def _looks_like_table_row(line: str) -> bool:
    return "|" in line or "\t" in line or len(re.findall(r"\s{2,}", line)) >= 3
