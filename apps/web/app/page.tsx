"use client";

import {
  AlertTriangle,
  Bot,
  Check,
  ChevronDown,
  Clipboard,
  Download,
  Eye,
  EyeOff,
  FileText,
  FolderOpen,
  Loader2,
  MessageSquareText,
  Paperclip,
  Pencil,
  RefreshCw,
  Save,
  Search,
  SendHorizontal,
  Settings,
  ShieldCheck,
  Upload,
  Wrench,
  X,
} from "lucide-react";
import { ChangeEvent, DragEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  API_BASE,
  api,
  type AuditFinding,
  type AuditTask,
  type DetectionItem,
  type HealthStatus,
  type Industry,
  type KnowledgeCoverage,
  type ModelProvider,
  type Standard,
  type ToolStatus,
  type ToolTestResult,
  type ToolsStatusResponse,
  type UploadedFile,
} from "@/lib/api";

type AgentStepStatus = "waiting" | "active" | "done" | "error";

type AgentStep = {
  id: string;
  label: string;
  description: string;
  status: AgentStepStatus;
};

type SettingsLevel = "basic" | "providers" | "tools" | "review" | "knowledge" | "quote" | "ocr" | "report" | "advanced";

type RiskOverride = {
  level?: string;
  suggestion?: string;
  status?: "pending" | "confirmed" | "dismissed";
};

type AuditConversation = {
  id: string;
  title: string;
  group: string;
  latestTask: AuditTask;
  tasks: AuditTask[];
};

type SaveFilter = {
  name: string;
  extensions: string[];
};

type ModelForm = {
  provider: string;
  model: string;
  base_url: string;
  api_key_secret: string;
  api_key_hint: string;
  api_key_saved: boolean;
  supports_vision: boolean;
  supports_json: boolean;
  supports_tools: boolean;
};

type QuoteItemForm = {
  industry_id: string;
  code: string;
  name: string;
  method_standard: string;
  judgment_standard: string;
  price: string;
  cycle_days: string;
  sample_amount: string;
  package_name: string;
};

const initialSteps: AgentStep[] = [
  { id: "upload", label: "上传并读取文件", description: "保存原始图片、PDF 或文本资料。", status: "waiting" },
  { id: "ocr", label: "视觉/OCR 识别", description: "有视觉模型时优先看图，OCR 作为辅助和兜底。", status: "waiting" },
  { id: "route", label: "品类路由", description: "自动选择食品、保健食品、电子产品等法规包。", status: "waiting" },
  { id: "rules", label: "法规检索与规则校验", description: "调用本地法规库和确定性审核规则。", status: "waiting" },
  { id: "review", label: "模型合规分析", description: "输出风险等级、法规依据和修改建议。", status: "waiting" },
];

const MAX_AUDIT_IMAGES = 12;
const MERGED_IMAGE_MAX_WIDTH = 1600;
const MERGED_IMAGE_MAX_HEIGHT = 30000;
const MERGED_IMAGE_MARGIN = 48;
const MERGED_IMAGE_LABEL_HEIGHT = 48;

const providerPresets = [
  {
    provider: "OpenAI",
    model: "gpt-4.1",
    base_url: "https://api.openai.com/v1",
    supports_vision: true,
    supports_json: true,
    supports_tools: true,
  },
  {
    provider: "DeepSeek",
    model: "deepseek-chat",
    base_url: "https://api.deepseek.com/v1",
    supports_vision: false,
    supports_json: true,
    supports_tools: true,
  },
  {
    provider: "Doubao",
    model: "doubao-seed-1-6",
    base_url: "https://ark.cn-beijing.volces.com/api/v3",
    supports_vision: true,
    supports_json: true,
    supports_tools: true,
  },
  {
    provider: "Claude",
    model: "claude-sonnet-4-5",
    base_url: "https://api.anthropic.com/v1",
    supports_vision: true,
    supports_json: true,
    supports_tools: true,
  },
];

const settingsItems: Array<{ id: SettingsLevel; title: string; description: string }> = [
  { id: "basic", title: "基础设置", description: "模型、API Key、报告格式" },
  { id: "providers", title: "模型供应商", description: "豆包 / DeepSeek / GPT / Claude" },
  { id: "tools", title: "工具管理", description: "OCR / 法规检索 / 报告 / 桌面打包" },
  { id: "review", title: "审核设置", description: "路由、联网核查、风险偏好" },
  { id: "knowledge", title: "知识库设置", description: "本地法规库与索引" },
  { id: "quote", title: "项目报价库", description: "单项添加 / 文档导入" },
  { id: "ocr", title: "OCR 设置", description: "识别语言与图片增强" },
  { id: "report", title: "报告设置", description: "抬头、Logo、免责声明" },
  { id: "advanced", title: "高级设置", description: "默认折叠，谨慎修改" },
];

function formatDate(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function riskLabel(level?: string) {
  if (level === "high") return "高风险";
  if (level === "medium") return "中风险";
  if (level === "low") return "低风险";
  return "待确认";
}

function riskTone(level?: string) {
  if (level === "high") return "red";
  if (level === "medium") return "orange";
  if (level === "low") return "blue";
  return "gray";
}

function toolStatusLabel(status?: string) {
  if (status === "ready") return "可用";
  if (status === "partial") return "部分可用";
  if (status === "missing") return "未就绪";
  return "未知";
}

function toolStatusTone(status?: string) {
  if (status === "ready") return "teal";
  if (status === "partial") return "orange";
  return "gray";
}

function statusLabel(task?: AuditTask | null) {
  if (!task) return "待上传";
  if (task.status === "completed") return "已完成";
  if (task.status === "needs_review") return "有风险";
  if (task.status === "pending") return "审核中";
  return task.status || "已生成";
}

function taskTitle(task?: AuditTask | null) {
  if (!task) return "新标签审核";
  if (task.session_title) return task.session_title;
  const name = task.extracted_fields?.product_name || task.extracted_fields?.name;
  if (name) return String(name);
  const route = task.final_report?.industry || task.document_type || "标签审核";
  return `${route} ${task.id.slice(0, 8)}`;
}

function formatFileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function isImageFile(file: File) {
  return file.type.startsWith("image/");
}

function readImage(file: File) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`无法读取图片：${file.name}`));
    };
    image.src = url;
  });
}

function canvasToPngFile(canvas: HTMLCanvasElement, filename: string) {
  return new Promise<File>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("多图合成失败，请减少图片数量后重试。"));
        return;
      }
      resolve(new File([blob], filename, { type: "image/png" }));
    }, "image/png");
  });
}

async function composeAuditImages(files: File[]) {
  const images = await Promise.all(files.map((file) => readImage(file)));
  let prepared = images.map((image) => {
    const originalWidth = image.naturalWidth || image.width;
    const originalHeight = image.naturalHeight || image.height;
    const width = Math.min(MERGED_IMAGE_MAX_WIDTH, originalWidth);
    const scale = width / originalWidth;
    const height = Math.max(1, Math.round(originalHeight * scale));
    return { image, width: Math.round(width), height };
  });
  const fixedHeight = MERGED_IMAGE_MARGIN + prepared.length * (MERGED_IMAGE_LABEL_HEIGHT + MERGED_IMAGE_MARGIN);
  const imageHeight = prepared.reduce((sum, item) => sum + item.height, 0);
  const maxImageHeight = MERGED_IMAGE_MAX_HEIGHT - fixedHeight;
  if (imageHeight > maxImageHeight) {
    const scale = Math.max(0.25, maxImageHeight / imageHeight);
    prepared = prepared.map((item) => ({
      ...item,
      width: Math.max(1, Math.round(item.width * scale)),
      height: Math.max(1, Math.round(item.height * scale)),
    }));
  }
  const contentWidth = Math.max(...prepared.map((item) => item.width));
  const canvasWidth = contentWidth + MERGED_IMAGE_MARGIN * 2;
  const canvasHeight =
    MERGED_IMAGE_MARGIN +
    prepared.reduce((sum, item) => sum + MERGED_IMAGE_LABEL_HEIGHT + item.height + MERGED_IMAGE_MARGIN, 0);
  const canvas = document.createElement("canvas");
  canvas.width = canvasWidth;
  canvas.height = canvasHeight;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("当前环境无法合成多张图片。");

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvasWidth, canvasHeight);
  context.textBaseline = "middle";

  let y = MERGED_IMAGE_MARGIN;
  prepared.forEach((item, index) => {
    context.fillStyle = "#f3f4f6";
    context.fillRect(MERGED_IMAGE_MARGIN, y, contentWidth, MERGED_IMAGE_LABEL_HEIGHT);
    context.fillStyle = "#111827";
    context.font = "600 22px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    context.fillText(`图片 ${index + 1} / ${files.length}`, MERGED_IMAGE_MARGIN + 18, y + MERGED_IMAGE_LABEL_HEIGHT / 2);
    context.fillStyle = "#6b7280";
    context.font = "18px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    const fileName = files[index]?.name || "";
    const maxNameWidth = contentWidth - 210;
    const displayName =
      context.measureText(fileName).width > maxNameWidth && fileName.length > 28
        ? `${fileName.slice(0, 16)}...${fileName.slice(-10)}`
        : fileName;
    context.fillText(displayName, MERGED_IMAGE_MARGIN + 170, y + MERGED_IMAGE_LABEL_HEIGHT / 2);
    y += MERGED_IMAGE_LABEL_HEIGHT;
    context.drawImage(item.image, MERGED_IMAGE_MARGIN, y, item.width, item.height);
    y += item.height + MERGED_IMAGE_MARGIN;
  });

  return canvasToPngFile(canvas, `huian-audit-images-${Date.now()}.png`);
}

async function prepareAuditUploadFile(files: File[]) {
  if (files.length === 1) return files[0];
  return composeAuditImages(files);
}

function conversationIdOf(task?: AuditTask | null) {
  return task?.conversation_id || task?.id || "";
}

function compareTaskTimeAsc(a: AuditTask, b: AuditTask) {
  return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
}

function compareTaskTimeDesc(a: AuditTask, b: AuditTask) {
  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
}

function maskApiKey(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (trimmed.length <= 8) return "已保存密钥";
  return `${trimmed.slice(0, 3)}****${trimmed.slice(-4)}`;
}

function getFindings(task?: AuditTask | null): AuditFinding[] {
  if (!task) return [];
  const findings = task.final_report?.findings;
  return Array.isArray(findings) ? findings : [];
}

function getRiskSummary(findings: AuditFinding[], overrides: Record<string, RiskOverride>) {
  return findings.reduce(
    (acc, finding) => {
      const level = overrides[finding.finding_id]?.level || finding.risk_level;
      if (level === "high") acc.high += 1;
      else if (level === "medium") acc.medium += 1;
      else if (level === "low") acc.low += 1;
      else acc.confirm += 1;
      return acc;
    },
    { high: 0, medium: 0, low: 0, confirm: 0 },
  );
}

function getConclusion(findings: AuditFinding[], overrides: Record<string, RiskOverride>) {
  const summary = getRiskSummary(findings, overrides);
  if (summary.high > 0) return "存在高风险";
  if (summary.medium > 0 || summary.confirm > 0) return "存在合规风险";
  if (findings.length > 0) return "存在低风险提示";
  return "未发现明显风险";
}

function buildReportText(task: AuditTask, overrides: Record<string, RiskOverride>) {
  const findings = getFindings(task);
  const lines = [
    "汇安检测合规审核报告",
    "",
    `商品/任务：${taskTitle(task)}`,
    `品类：${task.final_report?.industry || "自动识别"}`,
    `审核结论：${getConclusion(findings, overrides)}`,
    `模型：${task.model_used || "本地规则 + 当前模型"}`,
    `生成时间：${formatDate(task.completed_at || task.created_at)}`,
    "",
    "风险明细：",
  ];
  if (!findings.length) {
    lines.push("未发现明显风险。");
  }
  findings.forEach((finding, index) => {
    const override = overrides[finding.finding_id] || {};
    lines.push(
      `${index + 1}. ${finding.title}`,
      `风险等级：${riskLabel(override.level || finding.risk_level)}`,
      `标签原文：${finding.evidence_text || "-"}`,
      `法规依据：${finding.standard_code || "-"} ${finding.standard_clause || ""}`,
      `问题说明：${finding.reason || "-"}`,
      `修改建议：${override.suggestion || finding.suggestion || "-"}`,
      "",
    );
  });
  lines.push(task.final_report?.disclaimer || "AI 结果仅供参考，不构成法律意见或官方检测结论。");
  return lines.join("\n");
}

function isTauriDesktop() {
  return typeof window !== "undefined" && Boolean((window as Window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__);
}

function makeBlob(content: BlobPart | Blob, type: string) {
  return content instanceof Blob ? content : new Blob([content], { type });
}

function downloadBlob(filename: string, content: BlobPart | Blob, type: string) {
  const blob = makeBlob(content, type);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function saveReportFile(filename: string, content: BlobPart | Blob, type: string, filters: SaveFilter[]) {
  const blob = makeBlob(content, type);

  if (isTauriDesktop()) {
    try {
      const [{ save }, { writeFile }] = await Promise.all([
        import("@tauri-apps/plugin-dialog"),
        import("@tauri-apps/plugin-fs"),
      ]);
      const path = await save({ defaultPath: filename, filters });
      if (!path) {
        return false;
      }
      await writeFile(path, new Uint8Array(await blob.arrayBuffer()));
      return true;
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "请确认应用有文件保存权限。";
      throw new Error(`打开保存窗口失败：${message}`);
    }
  }

  downloadBlob(filename, blob, type);
  return true;
}

function makeDocHtml(task: AuditTask, overrides: Record<string, RiskOverride>) {
  const findings = getFindings(task);
  const summary = getRiskSummary(findings, overrides);
  const rows = findings
    .map((finding, index) => {
      const override = overrides[finding.finding_id] || {};
      return `
        <tr>
          <td>${index + 1}</td>
          <td>${riskLabel(override.level || finding.risk_level)}</td>
          <td>${finding.title}</td>
          <td>${finding.evidence_text || ""}</td>
          <td>${finding.standard_code || ""} ${finding.standard_clause || ""}</td>
          <td>${override.suggestion || finding.suggestion || ""}</td>
        </tr>`;
    })
    .join("");
  return `
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; color: #202123; line-height: 1.65; }
          h1 { font-size: 26px; }
          table { width: 100%; border-collapse: collapse; margin-top: 16px; }
          th, td { border: 1px solid #d1d5db; padding: 8px; vertical-align: top; }
          th { background: #f3f4f6; }
          .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 18px 0; }
          .box { border: 1px solid #d1d5db; padding: 12px; }
          .note { color: #6b7280; font-size: 12px; margin-top: 24px; }
        </style>
      </head>
      <body>
        <h1>汇安检测合规审核报告</h1>
        <p>商品/任务：<b>${taskTitle(task)}</b></p>
        <p>品类：${task.final_report?.industry || "自动识别"}　审核结论：<b>${getConclusion(findings, overrides)}</b></p>
        <div class="summary">
          <div class="box">高风险：${summary.high}</div>
          <div class="box">中风险：${summary.medium}</div>
          <div class="box">低风险：${summary.low}</div>
          <div class="box">待确认：${summary.confirm}</div>
        </div>
        <h2>风险明细</h2>
        <table>
          <thead><tr><th>#</th><th>等级</th><th>问题</th><th>标签原文</th><th>法规依据</th><th>修改建议</th></tr></thead>
          <tbody>${rows || "<tr><td colspan='6'>未发现明显风险。</td></tr>"}</tbody>
        </table>
        <p class="note">${task.final_report?.disclaimer || "AI 结果仅供参考，不构成法律意见或官方检测结论。"}</p>
      </body>
    </html>`;
}

export default function Home() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const quoteImportInputRef = useRef<HTMLInputElement | null>(null);
  const [tasks, setTasks] = useState<AuditTask[]>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [models, setModels] = useState<ModelProvider[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [detectionItems, setDetectionItems] = useState<DetectionItem[]>([]);
  const [knowledgeCoverage, setKnowledgeCoverage] = useState<KnowledgeCoverage | null>(null);
  const [toolsStatus, setToolsStatus] = useState<ToolsStatusResponse | null>(null);
  const [toolTests, setToolTests] = useState<Record<string, ToolTestResult>>({});
  const [testingToolId, setTestingToolId] = useState("");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [apiKeyVisible, setApiKeyVisible] = useState(false);
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [revealedSavedApiKey, setRevealedSavedApiKey] = useState("");
  const [currentTask, setCurrentTask] = useState<AuditTask | null>(null);
  const [activeConversationId, setActiveConversationId] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [requestSubmitted, setRequestSubmitted] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedIndustryId, setSelectedIndustryId] = useState("auto");
  const [selectedModelId, setSelectedModelId] = useState("");
  const [steps, setSteps] = useState<AgentStep[]>(initialSteps);
  const [isRunning, setIsRunning] = useState(false);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsLevel, setSettingsLevel] = useState<SettingsLevel>("basic");
  const [confirmSettingsClose, setConfirmSettingsClose] = useState(false);
  const [sessionEditorOpen, setSessionEditorOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<AuditTask | null>(null);
  const [sessionForm, setSessionForm] = useState({ title: "", group: "默认分组" });
  const [exportOpen, setExportOpen] = useState(false);
  const [resultCollapsed, setResultCollapsed] = useState(false);
  const [compactResultOpen, setCompactResultOpen] = useState(false);
  const [expandedFindingId, setExpandedFindingId] = useState<string>("");
  const [riskOverrides, setRiskOverrides] = useState<Record<string, RiskOverride>>({});
  const [draftSuggestion, setDraftSuggestion] = useState("");
  const [filter, setFilter] = useState("");
  const [knowledgeUrl, setKnowledgeUrl] = useState("");
  const [selectedQuoteItemId, setSelectedQuoteItemId] = useState("");
  const [quoteItemForm, setQuoteItemForm] = useState<QuoteItemForm>({
    industry_id: "",
    code: "",
    name: "",
    method_standard: "",
    judgment_standard: "",
    price: "",
    cycle_days: "5",
    sample_amount: "",
    package_name: "基础报价库",
  });
  const [modelForm, setModelForm] = useState<ModelForm>({
    provider: "OpenAI",
    model: "gpt-4.1",
    base_url: "https://api.openai.com/v1",
    api_key_secret: "",
    api_key_hint: "",
    api_key_saved: false,
    supports_vision: true,
    supports_json: true,
    supports_tools: true,
  });
  const [savedModelForm, setSavedModelForm] = useState<ModelForm | null>(null);

  const findings = useMemo(() => getFindings(currentTask), [currentTask]);
  const summary = useMemo(() => getRiskSummary(findings, riskOverrides), [findings, riskOverrides]);
  const activeModel = useMemo(
    () => models.find((model) => model.id === selectedModelId) || null,
    [models, selectedModelId],
  );
  const settingsDirty = useMemo(() => {
    if (!savedModelForm) return false;
    const normalize = (form: ModelForm) => ({
      ...form,
      api_key_secret: form.api_key_secret && form.api_key_secret === revealedSavedApiKey ? "" : form.api_key_secret,
    });
    return JSON.stringify(normalize(modelForm)) !== JSON.stringify(savedModelForm);
  }, [modelForm, revealedSavedApiKey, savedModelForm]);
  const selectedQuoteItem = useMemo(
    () => detectionItems.find((item) => item.id === selectedQuoteItemId) || null,
    [detectionItems, selectedQuoteItemId],
  );
  const conversations = useMemo<AuditConversation[]>(() => {
    const map = new Map<string, AuditTask[]>();
    for (const task of tasks) {
      const id = conversationIdOf(task);
      if (!id) continue;
      map.set(id, [...(map.get(id) || []), task]);
    }
    return Array.from(map.entries())
      .map(([id, items]) => {
        const sortedDesc = [...items].sort(compareTaskTimeDesc);
        const latestTask = sortedDesc[0];
        return {
          id,
          latestTask,
          tasks: [...items].sort(compareTaskTimeAsc),
          title: taskTitle(latestTask),
          group: latestTask.session_group || latestTask.final_report?.industry || latestTask.document_type || "默认分组",
        };
      })
      .sort((a, b) => compareTaskTimeDesc(a.latestTask, b.latestTask));
  }, [tasks]);
  const filteredConversations = useMemo(() => {
    const keyword = filter.trim().toLowerCase();
    if (!keyword) return conversations;
    return conversations.filter((conversation) => {
      const text = [
        conversation.title,
        conversation.group,
        conversation.latestTask.final_report?.industry || "",
        statusLabel(conversation.latestTask),
        `${conversation.tasks.length} 次审核`,
      ].join(" ").toLowerCase();
      return text.includes(keyword);
    });
  }, [conversations, filter]);
  const groupedConversations = useMemo(() => {
    const groups = new Map<string, AuditConversation[]>();
    for (const conversation of filteredConversations) {
      groups.set(conversation.group, [...(groups.get(conversation.group) || []), conversation]);
    }
    return Array.from(groups.entries());
  }, [filteredConversations]);
  const sessionGroups = useMemo(() => {
    const groups = new Set<string>();
    for (const conversation of conversations) {
      const group = conversation.group.trim();
      if (group) groups.add(group);
    }
    groups.add("默认分组");
    return Array.from(groups).sort((a, b) => a.localeCompare(b, "zh-CN"));
  }, [conversations]);
  const selectedGroupExists = useMemo(
    () => sessionGroups.includes(sessionForm.group.trim()),
    [sessionForm.group, sessionGroups],
  );
  const currentConversationTasks = useMemo(() => {
    const id = activeConversationId || conversationIdOf(currentTask);
    if (!id) return currentTask ? [currentTask] : [];
    const byId = new Map<string, AuditTask>();
    for (const task of tasks) {
      if (conversationIdOf(task) === id) byId.set(task.id, task);
    }
    if (currentTask && conversationIdOf(currentTask) === id) byId.set(currentTask.id, currentTask);
    return Array.from(byId.values()).sort(compareTaskTimeAsc);
  }, [activeConversationId, currentTask, tasks]);
  const currentConversationTitle = useMemo(() => {
    const latestTask = currentConversationTasks[currentConversationTasks.length - 1] || currentTask;
    return latestTask ? taskTitle(latestTask) : "新标签审核";
  }, [currentConversationTasks, currentTask]);
  const currentResultIndex = useMemo(
    () => currentConversationTasks.findIndex((task) => task.id === currentTask?.id) + 1,
    [currentConversationTasks, currentTask],
  );
  const matchingModelProvider = useMemo(
    () =>
      models.find(
        (item) =>
          item.provider === modelForm.provider &&
          item.model === modelForm.model &&
          item.base_url.replace(/\/$/, "") === modelForm.base_url.replace(/\/$/, ""),
      ) || null,
    [modelForm.base_url, modelForm.model, modelForm.provider, models],
  );

  useEffect(() => {
    void loadInitialData();
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (currentTask && !isRunning) {
      setSteps(initialSteps.map((step) => ({ ...step, status: "done" })));
    }
  }, [currentTask, isRunning]);

  async function loadInitialData() {
    setError("");
    try {
      await waitForLocalService();
      const [healthStatus, industryList, modelList, standardList, coverage, taskList, detectionItemList, toolList] = await Promise.all([
        api.health(),
        api.industries(),
        api.modelProviders(),
        api.standards(),
        api.knowledgeCoverage(),
        api.auditTasks(),
        api.detectionItems(),
        api.toolsStatus(),
      ]);
      setHealth(healthStatus);
      setIndustries(industryList);
      setModels(modelList);
      setStandards(standardList);
      setKnowledgeCoverage(coverage);
      setTasks(taskList);
      setDetectionItems(detectionItemList);
      setToolsStatus(toolList);
      if (industryList[0]) {
        setQuoteItemForm((current) => ({ ...current, industry_id: current.industry_id || industryList[0].id }));
      }
      const defaultModel = modelList.find((model) => model.default_for_text || model.default_for_vision) || modelList[0];
      setSelectedModelId("local");
      if (defaultModel) {
        const nextModelForm = {
          provider: defaultModel.provider,
          model: defaultModel.model,
          base_url: defaultModel.base_url,
          api_key_secret: "",
          api_key_hint: defaultModel.api_key_hint || (defaultModel.api_key_saved ? "已保存密钥" : ""),
          api_key_saved: defaultModel.api_key_saved,
          supports_vision: defaultModel.supports_vision,
          supports_json: defaultModel.supports_json,
          supports_tools: defaultModel.supports_tools,
        };
        setModelForm(nextModelForm);
        setSavedModelForm(nextModelForm);
        setApiKeyVisible(false);
        setRevealedSavedApiKey("");
      }
      if (taskList[0]) {
        setCurrentTask(taskList[0]);
        setActiveConversationId(conversationIdOf(taskList[0]));
      }
    } catch (caught) {
      setError(humanizeRequestError(caught, "初始化失败，请确认本地服务已启动。"));
    }
  }

  function resetForNewAudit() {
    setCurrentTask(null);
    setActiveConversationId("");
    setSelectedFiles([]);
    setUploadedFile(null);
    setRequestSubmitted(false);
    setMessage("");
    setRiskOverrides({});
    setExpandedFindingId("");
    setSteps(initialSteps);
    setResultCollapsed(false);
    setCompactResultOpen(false);
    setToast("已创建新的审核会话");
  }

  function setStepStatus(id: string, status: AgentStepStatus) {
    setSteps((current) =>
      current.map((step) => {
        if (step.id === id) return { ...step, status };
        return step;
      }),
    );
  }

  function resetSteps() {
    setSteps(initialSteps.map((step) => ({ ...step, status: "waiting" })));
  }

  function selectFiles(fileList: FileList | File[]) {
    const incoming = Array.from(fileList).filter(Boolean);
    if (!incoming.length) return;
    setError("");
    setSelectedFiles((current) => {
      const next = current.length && current.every(isImageFile) && incoming.every(isImageFile) ? [...current, ...incoming] : incoming;
      if (next.length > 1 && !next.every(isImageFile)) {
        setError("一次审核多文件目前仅支持图片；PDF、Word、TXT 请单独上传。");
        return current;
      }
      if (next.length > MAX_AUDIT_IMAGES) {
        setError(`一次最多上传 ${MAX_AUDIT_IMAGES} 张图片。`);
        return current;
      }
      setToast(next.length > 1 ? `已选择 ${next.length} 张图片` : `已选择 ${next[0].name}`);
      return next;
    });
    setUploadedFile(null);
    setRequestSubmitted(false);
    setSteps(initialSteps);
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) selectFiles(event.target.files);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    selectFiles(event.dataTransfer.files);
  }

  function removeSelectedFile(index: number) {
    setSelectedFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
    setUploadedFile(null);
  }

  function clearSelectedFiles() {
    setSelectedFiles([]);
    setUploadedFile(null);
  }

  function makeTextFile() {
    const text = message.trim();
    if (!text) return null;
    return new File([text], `label-text-${Date.now()}.txt`, { type: "text/plain" });
  }

  async function runAudit(options?: { reuseTask?: AuditTask }) {
    const reusable = options?.reuseTask;
    const conversationId = conversationIdOf(reusable) || activeConversationId || conversationIdOf(currentTask);
    if (!selectedFiles.length && !message.trim() && !reusable) {
      setError("请先上传标签图片、PDF、Word，或粘贴标签文本。");
      return;
    }
    setIsRunning(true);
    setRequestSubmitted(true);
    setError("");
    setToast("");
    resetSteps();
    setResultCollapsed(false);
    setCompactResultOpen(false);
    try {
      const inputFile = selectedFiles.length ? await prepareAuditUploadFile(selectedFiles) : makeTextFile();
      let fileId = reusable?.file_id || uploadedFile?.id || "";
      if (!fileId) {
        if (!inputFile) throw new Error("缺少可审核文件。");
        setStepStatus("upload", "active");
        const uploaded = await api.uploadFile(inputFile);
        setUploadedFile(uploaded);
        fileId = uploaded.id;
        setStepStatus("upload", "done");
      } else {
        setStepStatus("upload", "done");
      }
      setStepStatus("ocr", "active");
      await new Promise((resolve) => window.setTimeout(resolve, 260));
      setStepStatus("route", "active");
      const created = await api.createAuditTask({
        file_id: fileId,
        industry_id: reusable?.industry_id || selectedIndustryId,
        customer_name: reusable?.customer_name || "内部审核",
        document_type: reusable?.document_type || "产品标签",
        model_provider_id: selectedModelId || "local",
        conversation_id: conversationId || undefined,
      });
      setStepStatus("ocr", "done");
      setStepStatus("route", "done");
      setStepStatus("rules", "done");
      setStepStatus("review", "done");
      setCurrentTask(created);
      setActiveConversationId(conversationIdOf(created));
      setRiskOverrides({});
      const nextTasks = await api.auditTasks();
      setTasks(nextTasks);
      setSelectedFiles([]);
      setUploadedFile(null);
      setMessage("");
      setExpandedFindingId(getFindings(created)[0]?.finding_id || "");
      setToast("审核完成，已生成结构化结果");
    } catch (caught) {
      if (!reusable) setRequestSubmitted(false);
      setSteps((current) =>
        current.map((step) => (step.status === "active" ? { ...step, status: "error" } : step)),
      );
      setError(caught instanceof Error ? caught.message : "审核失败，请稍后重试。");
    } finally {
      setIsRunning(false);
    }
  }

  async function rerunCurrentTask() {
    if (!currentTask) {
      setError("当前没有可重新审核的任务。");
      return;
    }
    await runAudit({ reuseTask: currentTask });
  }

  function selectTask(task: AuditTask) {
    setCurrentTask(task);
    setActiveConversationId(conversationIdOf(task));
    setSelectedFiles([]);
    setUploadedFile(null);
    setRequestSubmitted(true);
    setRiskOverrides({});
    setExpandedFindingId(getFindings(task)[0]?.finding_id || "");
    setResultCollapsed(false);
    setCompactResultOpen(false);
  }

  function openSessionEditor(task: AuditTask) {
    setEditingSession(task);
    setSessionForm({
      title: task.session_title || taskTitle(task),
      group: task.session_group || task.final_report?.industry || task.document_type || "默认分组",
    });
    setSessionEditorOpen(true);
  }

  async function saveSessionEdit() {
    if (!editingSession) return;
    setError("");
    try {
      const conversationId = conversationIdOf(editingSession);
      const relatedTasks = tasks.filter((task) => conversationIdOf(task) === conversationId);
      const updatedTasks = await Promise.all(
        relatedTasks.map((task) =>
          api.updateAuditTask(task.id, {
            session_title: sessionForm.title.trim(),
            session_group: sessionForm.group.trim() || "默认分组",
          }),
        ),
      );
      const updatedById = new Map(updatedTasks.map((task) => [task.id, task]));
      setTasks((current) => current.map((task) => updatedById.get(task.id) || task));
      if (currentTask && updatedById.has(currentTask.id)) setCurrentTask(updatedById.get(currentTask.id) || currentTask);
      setSessionEditorOpen(false);
      setEditingSession(null);
      setToast("会话信息已更新");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "会话保存失败。");
    }
  }

  async function deleteSession(task: AuditTask) {
    setError("");
    const conversationId = conversationIdOf(task);
    const relatedTasks = tasks.filter((item) => conversationIdOf(item) === conversationId);
    const relatedIds = new Set(relatedTasks.map((item) => item.id));
    setTasks((current) => current.filter((item) => !relatedIds.has(item.id)));
    if (currentTask && relatedIds.has(currentTask.id)) {
      setCurrentTask(null);
      setActiveConversationId("");
      setRiskOverrides({});
      setExpandedFindingId("");
    }
    if (editingSession?.id === task.id) {
      setSessionEditorOpen(false);
      setEditingSession(null);
    }
    try {
      await Promise.all(relatedTasks.map((item) => api.deleteAuditTask(item.id)));
      setToast("会话已删除");
    } catch (caught) {
      const refreshed = await api.auditTasks();
      setTasks(refreshed);
      setError(caught instanceof Error ? caught.message : "会话删除失败。");
    }
  }

  async function copyResult() {
    if (!currentTask) return;
    await navigator.clipboard.writeText(buildReportText(currentTask, riskOverrides));
    setToast("审核结果已复制");
  }

  async function downloadPdf() {
    if (!currentTask) return;
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/reports/audit/${currentTask.id}/download`);
      if (!response.ok) {
        throw new Error("PDF 报告生成失败，请稍后重试。");
      }
      const blob = await response.blob();
      const saved = await saveReportFile(
        `汇安检测-审核报告-${currentTask.id}.pdf`,
        blob,
        "application/pdf",
        [{ name: "PDF 报告", extensions: ["pdf"] }],
      );
      if (!saved) return;
      setExportOpen(false);
      setToast("PDF 报告已生成");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "PDF 报告生成失败。");
    }
  }

  async function downloadWord() {
    if (!currentTask) return;
    setError("");
    try {
      const html = makeDocHtml(currentTask, riskOverrides);
      const saved = await saveReportFile(
        `汇安检测-审核报告-${currentTask.id}.doc`,
        html,
        "application/msword;charset=utf-8",
        [{ name: "Word 文档", extensions: ["doc"] }],
      );
      if (!saved) return;
      setExportOpen(false);
      setToast("Word 报告已生成");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Word 报告生成失败。");
    }
  }

  function updateRisk(findingId: string, patch: RiskOverride) {
    setRiskOverrides((current) => ({
      ...current,
      [findingId]: { ...(current[findingId] || {}), ...patch },
    }));
  }

  function startEditSuggestion(finding: AuditFinding) {
    setExpandedFindingId(finding.finding_id);
    setDraftSuggestion(riskOverrides[finding.finding_id]?.suggestion || finding.suggestion || "");
  }

  function saveSuggestion(findingId: string) {
    updateRisk(findingId, { suggestion: draftSuggestion });
    setDraftSuggestion("");
    setToast("修改建议已更新到当前报告");
  }

  function applyProviderPreset(providerName: string) {
    const preset = providerPresets.find((item) => item.provider === providerName);
    if (!preset) return;
    const existing = models.find(
      (item) =>
        item.provider === preset.provider &&
        item.model === preset.model &&
        item.base_url.replace(/\/$/, "") === preset.base_url.replace(/\/$/, ""),
    );
    setModelForm((current) => ({
      ...current,
      ...preset,
      api_key_secret: "",
      api_key_hint: existing?.api_key_hint || (existing?.api_key_saved ? "已保存密钥" : ""),
      api_key_saved: Boolean(existing?.api_key_saved),
    }));
    setApiKeyVisible(false);
    setRevealedSavedApiKey("");
  }

  function closeSettings() {
    if (settingsDirty) {
      setConfirmSettingsClose(true);
      return;
    }
    setSettingsOpen(false);
  }

  function discardSettingsChanges() {
    if (savedModelForm) setModelForm(savedModelForm);
    setApiKeyVisible(false);
    setRevealedSavedApiKey("");
    setConfirmSettingsClose(false);
    setSettingsOpen(false);
  }

  async function toggleApiKeyVisibility() {
    if (apiKeyVisible) {
      setApiKeyVisible(false);
      return;
    }
    if (modelForm.api_key_secret) {
      setApiKeyVisible(true);
      return;
    }
    if (!matchingModelProvider?.api_key_saved) {
      setApiKeyVisible(true);
      return;
    }
    setApiKeyLoading(true);
    setError("");
    try {
      const result = await api.modelProviderSecret(matchingModelProvider.id);
      const secret = result.api_key_secret || "";
      setModelForm((current) => ({ ...current, api_key_secret: secret }));
      setRevealedSavedApiKey(secret);
      setApiKeyVisible(true);
    } catch (caught) {
      setError(humanizeRequestError(caught, "读取已保存密钥失败。"));
    } finally {
      setApiKeyLoading(false);
    }
  }

  async function saveModelProvider(options?: { closeAfterSave?: boolean }) {
    setError("");
    try {
      await waitForLocalService();
      const apiKeyHint = modelForm.api_key_secret
        ? maskApiKey(modelForm.api_key_secret)
        : modelForm.api_key_hint || (modelForm.api_key_saved ? "已保存密钥" : "");
      const saved = await api.createModelProvider({
        provider: modelForm.provider,
        model: modelForm.model,
        base_url: modelForm.base_url,
        api_key_secret: modelForm.api_key_secret,
        api_key_hint: apiKeyHint,
        supports_vision: modelForm.supports_vision,
        supports_json: modelForm.supports_json,
        supports_tools: modelForm.supports_tools,
        status: "active",
        default_for_text: true,
        default_for_vision: modelForm.supports_vision,
      });
      const refreshed = await api.modelProviders();
      setModels(refreshed);
      setSelectedModelId(saved.id);
      const nextModelForm = {
        ...modelForm,
        api_key_secret: "",
        api_key_hint: saved.api_key_hint || (saved.api_key_saved ? "已保存密钥" : ""),
        api_key_saved: saved.api_key_saved,
      };
      setModelForm(nextModelForm);
      setSavedModelForm(nextModelForm);
      setApiKeyVisible(false);
      setRevealedSavedApiKey("");
      setConfirmSettingsClose(false);
      if (options?.closeAfterSave) setSettingsOpen(false);
      setToast("模型配置已保存");
    } catch (caught) {
      setError(humanizeRequestError(caught, "模型配置保存失败。"));
    }
  }

  async function testConnection() {
    setError("");
    try {
      const result = await api.health();
      setHealth(result);
      setToast(`服务连接正常：${result.status}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "连接测试失败。");
    }
  }

  async function waitForLocalService() {
    for (let index = 0; index < 30; index += 1) {
      try {
        await api.health();
        return;
      } catch {
        if (index === 0) setToast("本地服务启动中，稍等一下再自动保存");
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
      }
    }
    throw new Error("本地服务还没有启动完成，请稍等几秒后再保存。");
  }

  function humanizeRequestError(caught: unknown, fallback: string) {
    const message = caught instanceof Error ? caught.message : fallback;
    if (message === "Load failed" || message === "Failed to fetch" || message.includes("NetworkError")) {
      return "本地服务暂时不可用，请稍等几秒后再试。";
    }
    return message || fallback;
  }

  async function refreshToolStatuses() {
    setError("");
    try {
      const result = await api.toolsStatus();
      setToolsStatus(result);
      setToast(`工具状态已刷新：${result.summary.ready} 项可用，${result.summary.partial} 项部分可用`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "工具状态刷新失败。");
    }
  }

  async function testTool(tool: ToolStatus) {
    setError("");
    setTestingToolId(tool.id);
    try {
      const result = await api.testTool(tool.id);
      setToolTests((current) => ({ ...current, [tool.id]: result }));
      const refreshed = await api.toolsStatus();
      setToolsStatus(refreshed);
      setToast(result.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `${tool.name} 检测失败。`);
    } finally {
      setTestingToolId("");
    }
  }

  async function importKnowledgeFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const industryId = selectedIndustryId === "auto" ? industries[0]?.id : selectedIndustryId;
    if (!industryId) {
      setError("请先选择法规所属品类。");
      return;
    }
    setError("");
    try {
      const result = await api.importStandards(industryId, file);
      const [refreshed, coverage] = await Promise.all([api.standards(), api.knowledgeCoverage()]);
      setStandards(refreshed);
      setKnowledgeCoverage(coverage);
      setToast(result.message || "法规库文件已导入");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "法规库导入失败。");
    }
  }

  async function dedupeKnowledgeStandards() {
    setError("");
    try {
      const result = await api.dedupeStandards();
      const [refreshed, coverage] = await Promise.all([api.standards(), api.knowledgeCoverage()]);
      setStandards(refreshed);
      setKnowledgeCoverage(coverage);
      setToast(`${result.message} 处理 ${result.duplicate_groups} 组重复，停用 ${result.inactive} 条，迁移 ${result.relinked_rules} 条规则。`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "标准库去重失败。");
    }
  }

  async function importKnowledgeUrl() {
    const url = knowledgeUrl.trim();
    const industryId = selectedIndustryId === "auto" ? industries[0]?.id : selectedIndustryId;
    if (!url) {
      setError("请先粘贴标准全文 PDF/Word/TXT/HTML 链接。");
      return;
    }
    if (!industryId) {
      setError("请先选择法规所属品类。");
      return;
    }
    setError("");
    try {
      const result = await api.importStandardsFromUrl(industryId, url);
      const [refreshed, coverage] = await Promise.all([api.standards(), api.knowledgeCoverage()]);
      setStandards(refreshed);
      setKnowledgeCoverage(coverage);
      setKnowledgeUrl("");
      setToast(result.message || "已从 URL 导入法规全文");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "URL 导入失败。");
    }
  }

  async function saveQuoteItem() {
    const industryId = quoteItemForm.industry_id || industries[0]?.id || "";
    if (!industryId) {
      setError("请先选择项目所属品类。");
      return;
    }
    if (!quoteItemForm.name.trim()) {
      setError("请填写项目名称。");
      return;
    }
    setError("");
    try {
      await api.createDetectionItem({
        industry_id: industryId,
        code: quoteItemForm.code.trim() || `ITEM-${Date.now().toString().slice(-6)}`,
        name: quoteItemForm.name.trim(),
        method_standard: quoteItemForm.method_standard.trim(),
        judgment_standard: quoteItemForm.judgment_standard.trim(),
        price: Number(quoteItemForm.price || 0),
        cycle_days: Number(quoteItemForm.cycle_days || 5),
        sample_amount: quoteItemForm.sample_amount.trim(),
        package_name: quoteItemForm.package_name.trim() || "基础报价库",
      });
      const refreshed = await api.detectionItems();
      setDetectionItems(refreshed);
      setQuoteItemForm((current) => ({
        ...current,
        code: "",
        name: "",
        method_standard: "",
        judgment_standard: "",
        price: "",
        cycle_days: "5",
        sample_amount: "",
      }));
      setToast("项目报价已添加");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "项目报价保存失败。");
    }
  }

  function editQuoteItem(item: DetectionItem) {
    setSelectedQuoteItemId(item.id);
    setQuoteItemForm({
      industry_id: item.industry_id,
      code: item.code,
      name: item.name,
      method_standard: item.method_standard,
      judgment_standard: item.judgment_standard,
      price: String(item.price || ""),
      cycle_days: String(item.cycle_days || 5),
      sample_amount: item.sample_amount,
      package_name: item.package_name || "基础报价库",
    });
  }

  function newQuoteItem() {
    setSelectedQuoteItemId("");
    setQuoteItemForm({
      industry_id: quoteItemForm.industry_id || industries[0]?.id || "",
      code: "",
      name: "",
      method_standard: "",
      judgment_standard: "",
      price: "",
      cycle_days: "5",
      sample_amount: "",
      package_name: "基础报价库",
    });
  }

  async function updateQuoteItem() {
    if (!selectedQuoteItem) return;
    if (!quoteItemForm.name.trim()) {
      setError("请填写项目名称。");
      return;
    }
    setError("");
    try {
      await api.updateDetectionItem(selectedQuoteItem.id, {
        industry_id: quoteItemForm.industry_id || selectedQuoteItem.industry_id,
        code: quoteItemForm.code.trim() || selectedQuoteItem.code,
        name: quoteItemForm.name.trim(),
        method_standard: quoteItemForm.method_standard.trim(),
        judgment_standard: quoteItemForm.judgment_standard.trim(),
        price: Number(quoteItemForm.price || 0),
        cycle_days: Number(quoteItemForm.cycle_days || 5),
        sample_amount: quoteItemForm.sample_amount.trim(),
        package_name: quoteItemForm.package_name.trim() || "基础报价库",
      });
      const refreshed = await api.detectionItems();
      setDetectionItems(refreshed);
      setToast("项目报价已更新");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "项目报价更新失败。");
    }
  }

  async function deleteQuoteItem() {
    if (!selectedQuoteItem) return;
    await deleteQuoteItemById(selectedQuoteItem.id);
  }

  async function deleteQuoteItemById(itemId: string) {
    setError("");
    setDetectionItems((current) => current.filter((item) => item.id !== itemId));
    try {
      await api.deactivate("detection-items", itemId);
      const refreshed = await api.detectionItems();
      setDetectionItems(refreshed);
      if (selectedQuoteItemId === itemId) newQuoteItem();
      setToast("项目报价已删除");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "项目报价删除失败。");
    }
  }

  async function dedupeQuoteItems() {
    setError("");
    try {
      const result = await api.dedupeDetectionItems();
      const refreshed = await api.detectionItems();
      setDetectionItems(refreshed);
      setSelectedQuoteItemId("");
      setToast(`${result.message} 处理 ${result.duplicate_groups} 组重复。`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "项目报价去重失败。");
    }
  }

  async function importQuoteFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const industryId = quoteItemForm.industry_id || (selectedIndustryId === "auto" ? industries[0]?.id : selectedIndustryId);
    if (!industryId) {
      setError("请先选择报价项目所属品类。");
      return;
    }
    setError("");
    try {
      const result = await api.importQuoteLibrary(industryId, file);
      const refreshed = await api.detectionItems();
      setDetectionItems(refreshed);
      setToast(result.message || `已导入 ${result.items_created} 个报价项目`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "项目报价库导入失败。");
    }
  }

  const selectedIndustryName =
    selectedIndustryId === "auto"
      ? "自动路由"
      : industries.find((industry) => industry.id === selectedIndustryId)?.name || "自动路由";
  const selectedIndustryStandardCount =
    selectedIndustryId === "auto"
      ? standards.length
      : standards.filter((standard) => standard.industry_id === selectedIndustryId).length;

  return (
    <main className="agent-shell">
      <input
        ref={fileInputRef}
        className="hidden-input"
        type="file"
        accept="image/*,.pdf,.doc,.docx,.txt"
        multiple
        onChange={handleFileInput}
      />
      <input ref={importInputRef} className="hidden-input" type="file" onChange={importKnowledgeFile} />
      <input ref={quoteImportInputRef} className="hidden-input" type="file" onChange={importQuoteFile} />

      <aside className="agent-sidebar">
        <div className="brand">
          <img className="brand-mark" src="/huian-icon.svg" alt="汇安检测" />
          <div>
            <div className="brand-title">汇安检测</div>
            <div className="brand-subtitle">本地法规库 · AI 审核</div>
          </div>
        </div>

        <button className="primary-button full" onClick={resetForNewAudit}>
          <MessageSquareText size={16} />
          新建审核
        </button>

        <label className="search-box">
          <Search size={15} />
          <input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="搜索历史会话" />
        </label>

        <div className="sidebar-section-title">历史会话</div>
        <div className="session-list">
          {groupedConversations.length ? (
            groupedConversations.map(([group, groupConversations]) => (
              <div className="session-group" key={group}>
                <div className="session-group-title">{group}</div>
                {groupConversations.map((conversation) => (
                  <div key={conversation.id} className={`session-row ${activeConversationId === conversation.id ? "active" : ""}`}>
                    <button className="session-main" onClick={() => selectTask(conversation.latestTask)}>
                      <span className="session-title-line">
                        <strong>{conversation.title}</strong>
                        <span className={`pill ${conversation.latestTask.status === "needs_review" ? "orange" : "green"}`}>
                          {statusLabel(conversation.latestTask)}
                        </span>
                      </span>
                      <span className="session-meta">
                        {conversation.latestTask.final_report?.industry || conversation.latestTask.document_type} · {conversation.tasks.length} 次审核 ·{" "}
                        {formatDate(conversation.latestTask.created_at)}
                      </span>
                    </button>
                    <div className="session-actions">
                      <button className="icon-button" onClick={() => openSessionEditor(conversation.latestTask)} aria-label="编辑会话">
                        <Pencil size={13} />
                      </button>
                      <button className="icon-button" onClick={() => void deleteSession(conversation.latestTask)} aria-label="删除会话">
                        <X size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ))
          ) : (
            <div className="empty-sidebar">还没有历史会话</div>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="status-line">
            <span>当前模型</span>
            <strong>
              {selectedModelId === "local"
                ? "本地规则引擎"
                : activeModel
                  ? `${activeModel.provider}/${activeModel.model}`
                  : "未配置"}
            </strong>
          </div>
          <div className="status-line">
            <span>法规库</span>
            <strong>{standards.length} 条标准</strong>
          </div>
          <button className="ghost-button full" onClick={() => setSettingsOpen(true)}>
            <Settings size={16} />
            设置
          </button>
        </div>
      </aside>

      <section className={`agent-main ${resultCollapsed ? "result-hidden" : ""} ${compactResultOpen ? "compact-result-open" : ""}`}>
        <div className="workspace">
          <header className="workspace-topbar">
            <div>
              <div className="workspace-title">{currentTask ? currentConversationTitle : "新标签审核"}</div>
              <div className="workspace-subtitle">
                {selectedIndustryName} · 本地法规 {selectedIndustryStandardCount} 条 · {health?.model_gateway || "等待连接"} ·{" "}
                {selectedModelId === "local" ? "本地规则引擎" : activeModel?.provider || "未选择模型"}
              </div>
            </div>
            <div className="top-actions">
              <button className="ghost-button" onClick={rerunCurrentTask} disabled={!currentTask || isRunning}>
                <RefreshCw size={15} />
                重新审核
              </button>
              {resultCollapsed ? (
                <button className="ghost-button" onClick={() => setResultCollapsed(false)} disabled={!currentTask}>
                  <Eye size={15} />
                  显示结果
                </button>
              ) : null}
              <button
                className="ghost-button compact-result-trigger"
                onClick={() => {
                  setResultCollapsed(false);
                  setCompactResultOpen(true);
                }}
                disabled={!currentTask}
              >
                <Eye size={15} />
                审核结果
              </button>
              <button className="primary-button" onClick={() => setExportOpen(true)} disabled={!currentTask}>
                <Download size={15} />
                导出报告
              </button>
            </div>
          </header>

          <div className="chat-area">
            {!currentTask && !isRunning ? (
              <div className="empty-state" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
                <div className="empty-icon">
                  <Upload size={26} />
                </div>
                <h1>上传标签图片或文档，开始合规审核</h1>
                <p>支持多张图片、PDF、Word 和纯文本。有视觉模型时优先看图识别，OCR 作为辅助，并输出可追溯的风险建议。</p>
                <div className="empty-actions">
                  <button className="primary-button" onClick={() => fileInputRef.current?.click()}>
                    <Paperclip size={16} />
                    选择文件
                  </button>
                  <button className="ghost-button" onClick={() => setSettingsOpen(true)}>
                    <Settings size={16} />
                    配置模型
                  </button>
                </div>
              </div>
            ) : null}

            {(requestSubmitted || isRunning || currentTask) && (
              <div className="message-stack">
                {requestSubmitted && (selectedFiles.length > 0 || uploadedFile || message) && (
                  <div className="message user-message">
                    <div className="message-title">审核请求</div>
                    <div className="message-text">{message || "请审核这个标签，重点检查强制字段、宣称语、警示语和营养标示。"}</div>
                    {selectedFiles.length > 0 ? (
                      <div className="file-chip-list">
                        {selectedFiles.map((file, index) => (
                          <div className="file-chip" key={`${file.name}-${file.size}-${index}`}>
                            <FileText size={22} />
                            <div>
                              <strong>{file.name}</strong>
                              <span>{formatFileSize(file.size)} · {selectedFiles.length > 1 ? `第 ${index + 1} 张` : "待上传"}</span>
                            </div>
                            {!isRunning ? (
                              <button className="icon-button" onClick={() => removeSelectedFile(index)} aria-label="移除文件">
                                <X size={14} />
                              </button>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : uploadedFile ? (
                      <div className="file-chip">
                        <FileText size={22} />
                        <div>
                          <strong>{uploadedFile.original_name}</strong>
                          <span>已上传</span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}

                <div className="message agent-message">
                  <div className="message-title">智能体执行过程</div>
                  <div className="message-text">每一步都由真实后端能力承接：文件上传、视觉/OCR 识别、品类路由、规则校验和模型审核。</div>
                  <div className="agent-steps">
                    {steps.map((step, index) => (
                      <div key={step.id} className={`agent-step ${step.status}`}>
                        <span className="step-dot">
                          {step.status === "done" ? <Check size={12} /> : step.status === "active" ? <Loader2 size={12} /> : index + 1}
                        </span>
                        <span>
                          <strong>{step.label}</strong>
                          <small>{step.description}</small>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {currentConversationTasks.map((task, index) => {
                  const taskFindings = getFindings(task);
                  const isSelected = currentTask?.id === task.id;
                  return (
                    <button
                      key={task.id}
                      className={`message agent-message result-message ${isSelected ? "active" : ""}`}
                      onClick={() => selectTask(task)}
                    >
                      <span className="message-title">
                        第 {index + 1} 次审核：{getConclusion(taskFindings, isSelected ? riskOverrides : {})}
                      </span>
                      <span className="message-text">
                        {formatDate(task.completed_at || task.created_at)} · 已识别 {taskFindings.length} 项风险或提示。点击查看这一版的完整结果、法规依据和导出报告。
                      </span>
                      <span className="result-message-foot">
                        <span>{task.final_report?.industry || task.document_type || "自动识别品类"}</span>
                        {task.final_report?.vision_primary ? <em className="pill teal">视觉优先识别</em> : null}
                        <em className={`pill ${task.status === "needs_review" ? "orange" : "green"}`}>{statusLabel(task)}</em>
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <footer className="composer-wrap">
            <div className="run-options">
              <select value={selectedIndustryId} onChange={(event) => setSelectedIndustryId(event.target.value)}>
                <option value="auto">自动识别品类</option>
                {industries.map((industry) => (
                  <option key={industry.id} value={industry.id}>
                    {industry.name}
                  </option>
                ))}
              </select>
              <select value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)}>
                <option value="local">本地规则引擎</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.provider} / {model.model}
                  </option>
                ))}
              </select>
            </div>
            {selectedFiles.length > 0 && !isRunning ? (
              <div className="pending-attachments">
                <div className="pending-attachments-head">
                  <span>{selectedFiles.length > 1 ? `${selectedFiles.length} 张图片待发送` : "1 个文件待发送"}</span>
                  <button className="text-button" onClick={clearSelectedFiles} disabled={isRunning}>
                    全部移除
                  </button>
                </div>
                {selectedFiles.map((file, index) => (
                  <div className="pending-attachment" key={`${file.name}-${file.size}-${index}`}>
                    <FileText size={20} />
                    <div>
                      <strong>{file.name}</strong>
                      <span>{formatFileSize(file.size)} · {selectedFiles.length > 1 ? `图片 ${index + 1}` : "待发送"}</span>
                    </div>
                    <button className="icon-button" onClick={() => removeSelectedFile(index)} disabled={isRunning} aria-label="移除待发送文件">
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="composer">
              <button className="icon-button" onClick={() => fileInputRef.current?.click()} disabled={isRunning} aria-label="上传文件">
                <Paperclip size={18} />
              </button>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="粘贴标签文本，或补充审核要求..."
                disabled={isRunning}
              />
              <button className="primary-button send" onClick={() => void runAudit()} disabled={isRunning}>
                {isRunning ? <Loader2 size={17} /> : <SendHorizontal size={17} />}
                {isRunning ? "审核中" : "发送"}
              </button>
            </div>
          </footer>
        </div>

        {!resultCollapsed && (
          <aside className="result-panel">
            <div className="result-head">
              <div>
                <div className="panel-title">审核结果</div>
                <div className="panel-subtitle">
                  {currentTask
                    ? `第 ${currentResultIndex || 1} 次审核 · ${formatDate(currentTask.completed_at || currentTask.created_at)}`
                    : "等待审核"}
                </div>
              </div>
              <button
                className="icon-button"
                onClick={() => {
                  if (compactResultOpen) {
                    setCompactResultOpen(false);
                    return;
                  }
                  setResultCollapsed(true);
                }}
                aria-label="收起结果"
              >
                <X size={15} />
              </button>
            </div>

            <div className="result-body">
              {currentTask ? (
                <>
                  <div className="conclusion-box">
                    <strong>{getConclusion(findings, riskOverrides)}</strong>
                    {currentTask.final_report?.vision_primary ? <em className="pill teal">视觉优先识别</em> : null}
                    <span>{currentTask.final_report?.summary || "系统已生成结构化审核结果。"}</span>
                  </div>
                  <div className="risk-grid">
                    <div>
                      <span>高风险</span>
                      <strong className="red-text">{summary.high}</strong>
                    </div>
                    <div>
                      <span>中风险</span>
                      <strong className="orange-text">{summary.medium}</strong>
                    </div>
                    <div>
                      <span>低风险</span>
                      <strong className="blue-text">{summary.low}</strong>
                    </div>
                  </div>

                  <div className="finding-list">
                    {findings.length ? (
                      findings.map((finding) => {
                        const override = riskOverrides[finding.finding_id] || {};
                        const isOpen = expandedFindingId === finding.finding_id;
                        const level = override.level || finding.risk_level;
                        return (
                          <article key={finding.finding_id} className={`finding-card ${isOpen ? "open" : ""}`}>
                            <button
                              className="finding-summary"
                              onClick={() => {
                                setExpandedFindingId(isOpen ? "" : finding.finding_id);
                                setDraftSuggestion("");
                              }}
                            >
                              <span>
                                <strong>{finding.title}</strong>
                                <small>{finding.field_key || "标签字段"} · 置信度 {Math.round((finding.confidence || 0) * 100)}%</small>
                                <small className="finding-meta-line">
                                  依据：{finding.standard_code || "标准规则库"} {finding.standard_clause || ""}
                                </small>
                              </span>
                              <span className={`pill ${riskTone(level)}`}>{riskLabel(level)}</span>
                            </button>
                            {isOpen ? (
                              <div className="finding-detail">
                                <p>
                                  <b>标签原文：</b>
                                  {finding.evidence_text || "未提供"}
                                </p>
                                <p>
                                  <b>问题说明：</b>
                                  {finding.reason}
                                </p>
                                <div className="citation">
                                  <div className="citation-title">
                                    <Eye size={14} />
                                    <b>查看法规依据</b>
                                  </div>
                                  <div>
                                    {finding.standard_code || "标准规则库"} {finding.standard_clause || ""}
                                  </div>
                                  <small>{finding.source_excerpt || "依据本地法规包和规则库匹配结果生成，正式出具前建议人工复核原文条款。"}</small>
                                </div>
                                <div className="risk-editor">
                                  <label>
                                    风险等级
                                    <select value={level} onChange={(event) => updateRisk(finding.finding_id, { level: event.target.value })}>
                                      <option value="high">高风险</option>
                                      <option value="medium">中风险</option>
                                      <option value="low">低风险</option>
                                      <option value="confirm">待确认</option>
                                    </select>
                                  </label>
                                  <label className="suggestion-field">
                                    修改建议
                                    <textarea
                                      value={draftSuggestion || override.suggestion || finding.suggestion || ""}
                                      onFocus={() => startEditSuggestion(finding)}
                                      onChange={(event) => setDraftSuggestion(event.target.value)}
                                    />
                                  </label>
                                  <div className="finding-actions">
                                    <button className="ghost-button" onClick={() => saveSuggestion(finding.finding_id)}>
                                      <Save size={14} />
                                      保存建议
                                    </button>
                                    <button className="ghost-button" onClick={() => updateRisk(finding.finding_id, { status: "dismissed" })}>
                                      驳回
                                    </button>
                                    <button className="primary-button" onClick={() => updateRisk(finding.finding_id, { status: "confirmed" })}>
                                      确认风险
                                    </button>
                                  </div>
                                  {override.status ? <span className="local-status">当前状态：{override.status === "confirmed" ? "已确认" : "已驳回"}</span> : null}
                                </div>
                              </div>
                            ) : null}
                          </article>
                        );
                      })
                    ) : (
                      <div className="empty-result">
                        <ShieldCheck size={26} />
                        <strong>未发现明显风险</strong>
                        <span>仍建议人工抽查关键字段。</span>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="empty-result">
                  <Bot size={30} />
                  <strong>等待审核结果</strong>
                  <span>上传标签后，结果会在这里结构化展示。</span>
                </div>
              )}
            </div>

            <div className="result-foot">
              <button className="ghost-button" onClick={copyResult} disabled={!currentTask}>
                <Clipboard size={15} />
                复制结果
              </button>
              <button className="primary-button" onClick={() => setExportOpen(true)} disabled={!currentTask}>
                <Download size={15} />
                导出报告
              </button>
            </div>
          </aside>
        )}
      </section>

      {sessionEditorOpen && editingSession ? (
        <div className="modal-layer confirm-layer" role="dialog" aria-modal="true">
          <div className="confirm-modal">
            <div className="modal-head">
              <div>
                <h2>编辑会话</h2>
                <p>修改历史会话名称，并把它归类到合适的分组。</p>
              </div>
              <button className="icon-button" onClick={() => setSessionEditorOpen(false)} aria-label="关闭会话编辑">
                <X size={16} />
              </button>
            </div>
            <div className="settings-form single compact-form">
              <label>
                会话名称
                <input
                  value={sessionForm.title}
                  onChange={(event) => setSessionForm((current) => ({ ...current, title: event.target.value }))}
                  placeholder="例如：凉粉标签复核"
                />
              </label>
              <label>
                选择分组
                <select
                  value={selectedGroupExists ? sessionForm.group.trim() : "__new__"}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSessionForm((current) => ({ ...current, group: value === "__new__" ? "" : value }));
                  }}
                >
                  {sessionGroups.map((group) => (
                    <option key={group} value={group}>
                      {group}
                    </option>
                  ))}
                  <option value="__new__">新建分组...</option>
                </select>
              </label>
              {!selectedGroupExists ? (
                <label>
                  新建分组名称
                  <input
                    value={sessionForm.group}
                    onChange={(event) => setSessionForm((current) => ({ ...current, group: event.target.value }))}
                    placeholder="例如：食品标签 / 客户A / 6月批次"
                    autoFocus
                  />
                </label>
              ) : null}
              <div className="session-group-preview">
                保存后会话将归入：<strong>{sessionForm.group.trim() || "默认分组"}</strong>
              </div>
            </div>
            <div className="confirm-actions">
              <button className="danger-button" onClick={() => void deleteSession(editingSession)}>
                删除会话
              </button>
              <button className="primary-button" onClick={saveSessionEdit}>
                <Save size={15} />
                保存
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {settingsOpen ? (
        <div className="modal-layer" role="dialog" aria-modal="true">
          <div className="settings-modal">
            <nav className="settings-nav">
              <div className="settings-title-row">
                <h2>设置</h2>
                <button className="icon-button" onClick={closeSettings} aria-label="关闭设置">
                  <X size={16} />
                </button>
              </div>
              {settingsItems.map((item) => (
                <button
                  key={item.id}
                  className={`settings-item ${settingsLevel === item.id ? "active" : ""}`}
                  onClick={() => setSettingsLevel(item.id)}
                >
                  <strong>{item.title}</strong>
                  <span>{item.description}</span>
                </button>
              ))}
            </nav>
            <section className="settings-content">
              <div className="settings-toolbar">
                <div>
                  <h2>{settingsItems.find((item) => item.id === settingsLevel)?.title}</h2>
                  <p>复杂能力放在设置中分级管理，主工作台保持轻量。</p>
                </div>
                <button className="primary-button" onClick={() => void saveModelProvider({ closeAfterSave: true })}>
                  <Save size={15} />
                  保存并关闭
                </button>
              </div>

              {settingsLevel === "basic" || settingsLevel === "providers" ? (
                <>
                  <div className="provider-grid">
                    {providerPresets.map((preset) => (
                      <button
                        key={preset.provider}
                        className={`provider-card ${modelForm.provider === preset.provider ? "active" : ""}`}
                        onClick={() => applyProviderPreset(preset.provider)}
                      >
                        <span>
                          <strong>{preset.provider === "OpenAI" ? "GPT" : preset.provider}</strong>
                          <small>{preset.base_url}</small>
                        </span>
                        <span className={`pill ${modelForm.provider === preset.provider ? "teal" : ""}`}>
                          {modelForm.provider === preset.provider ? "选中" : "可选"}
                        </span>
                      </button>
                    ))}
                  </div>
                  <div className="settings-form">
                    <label>
                      Base URL
                      <input value={modelForm.base_url} onChange={(event) => setModelForm((current) => ({ ...current, base_url: event.target.value }))} />
                    </label>
                    <label>
                      模型 ID
                      <input value={modelForm.model} onChange={(event) => setModelForm((current) => ({ ...current, model: event.target.value }))} />
                    </label>
                    <label>
                      API Key
                      <span className="secret-input">
                        <input
                          type={apiKeyVisible ? "text" : "password"}
                          value={modelForm.api_key_secret}
                          onChange={(event) => {
                            const value = event.target.value;
                            setModelForm((current) => ({ ...current, api_key_secret: value }));
                            if (value !== revealedSavedApiKey) setRevealedSavedApiKey("");
                          }}
                          placeholder={modelForm.api_key_saved ? "留空则继续使用已保存密钥" : "输入后保存到本地后端"}
                        />
                        <button
                          type="button"
                          className="secret-toggle"
                          onClick={() => void toggleApiKeyVisibility()}
                          disabled={apiKeyLoading}
                          aria-label={apiKeyVisible ? "隐藏 API Key" : "显示 API Key"}
                        >
                          {apiKeyLoading ? <Loader2 size={15} className="spin" /> : apiKeyVisible ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </span>
                      <span className={`key-status ${modelForm.api_key_secret || modelForm.api_key_saved ? "saved" : ""}`}>
                        {modelForm.api_key_secret
                          ? `将保存：${maskApiKey(modelForm.api_key_secret)}`
                          : modelForm.api_key_saved
                            ? `已保存：${modelForm.api_key_hint || "已保存密钥"}`
                            : "未保存密钥"}
                      </span>
                    </label>
                    <label>
                      当前供应商
                      <input value={modelForm.provider} onChange={(event) => setModelForm((current) => ({ ...current, provider: event.target.value }))} />
                    </label>
                  </div>
                  <div className="switch-row">
                    <span>
                      <strong>支持视觉输入</strong>
                      <small>图片会和 OCR 文本一起交给模型。</small>
                    </span>
                    <button
                      className={`toggle ${modelForm.supports_vision ? "on" : ""}`}
                      onClick={() => setModelForm((current) => ({ ...current, supports_vision: !current.supports_vision }))}
                      aria-label="切换视觉能力"
                    />
                  </div>
                  <div className="switch-row">
                    <span>
                      <strong>支持工具调用</strong>
                      <small>声明该模型支持 tool calling；实际可用工具在“工具管理”里检测。</small>
                    </span>
                    <button
                      className={`toggle ${modelForm.supports_tools ? "on" : ""}`}
                      onClick={() => setModelForm((current) => ({ ...current, supports_tools: !current.supports_tools }))}
                      aria-label="切换工具调用能力"
                    />
                  </div>
                  <button className="ghost-button" onClick={testConnection}>
                    <Search size={15} />
                    测试后端连接
                  </button>
                </>
              ) : null}

              {settingsLevel === "tools" ? (
                <div className="settings-panel-list">
                  <div className="tool-summary">
                    <div>
                      <Wrench size={22} />
                      <span>
                        <strong>工具运行状态</strong>
                        <small>
                          {toolsStatus
                            ? `${toolsStatus.summary.total} 项工具 · ${toolsStatus.summary.ready} 项可用 · ${toolsStatus.summary.partial} 项部分可用`
                            : "正在读取本地工具状态"}
                        </small>
                      </span>
                    </div>
                    <button className="ghost-button" onClick={refreshToolStatuses}>
                      <RefreshCw size={15} />
                      刷新状态
                    </button>
                  </div>
                  <div className="tool-grid">
                    {(toolsStatus?.tools ?? []).map((tool) => {
                      const result = toolTests[tool.id];
                      return (
                        <div key={tool.id} className="tool-card">
                          <div className="tool-card-head">
                            <span>
                              <strong>{tool.name}</strong>
                              <small>{tool.category}</small>
                            </span>
                            <span className={`pill ${toolStatusTone(tool.status)}`}>{toolStatusLabel(tool.status)}</span>
                          </div>
                          <p>{tool.summary}</p>
                          <div className="tool-detail-list">
                            {tool.details.map((detail) => (
                              <span key={`${tool.id}-${detail.label}`} className={detail.ok ? "ready" : ""}>
                                <Check size={13} />
                                {detail.label}
                                <small>{detail.note}</small>
                              </span>
                            ))}
                          </div>
                          {tool.github.length ? (
                            <div className="tool-projects">
                              <b>参考项目</b>
                              <span>{tool.github.join(" · ")}</span>
                            </div>
                          ) : null}
                          <div className="tool-card-actions">
                            <button className="ghost-button compact" onClick={() => void testTool(tool)} disabled={testingToolId === tool.id}>
                              {testingToolId === tool.id ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
                              检测
                            </button>
                            <small>{tool.install_hint}</small>
                          </div>
                          {result ? (
                            <div className={`tool-test-result ${toolStatusTone(result.status)}`}>
                              {result.message}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {settingsLevel === "review" ? (
                <div className="settings-panel-list">
                  <div className="switch-row">
                    <span>
                      <strong>自动品类路由</strong>
                      <small>上传后自动选择法规包，低置信度时提醒用户确认。</small>
                    </span>
                    <button className="toggle on" aria-label="自动品类路由已开启" />
                  </div>
                  <div className="switch-row">
                    <span>
                      <strong>联网核查新规</strong>
                      <small>只提示可能有新规，不直接进入正式依据。</small>
                    </span>
                    <button className="toggle on" aria-label="联网核查已开启" />
                  </div>
                </div>
              ) : null}

              {settingsLevel === "knowledge" ? (
                <div className="settings-panel-list">
                  <div className="knowledge-summary">
                    <FolderOpen size={22} />
                    <div>
                      <strong>本地法规库</strong>
                      <span>
                        {knowledgeCoverage?.total_standards ?? standards.length} 条标准/法规摘要，
                        {knowledgeCoverage?.total_rules ?? 0} 条审核规则，
                        {knowledgeCoverage?.total_clauses ?? 0} 个全文切片。
                      </span>
                    </div>
                  </div>
                  <button className="primary-button" onClick={() => importInputRef.current?.click()}>
                    <Upload size={15} />
                    导入法规文件
                  </button>
                  <div className="url-import-row">
                    <input
                      value={knowledgeUrl}
                      onChange={(event) => setKnowledgeUrl(event.target.value)}
                      placeholder="粘贴标准全文 PDF/Word/TXT/HTML 链接"
                    />
                    <button className="ghost-button" onClick={importKnowledgeUrl}>
                      <Download size={15} />
                      URL 导入
                    </button>
                  </div>
                  <button className="ghost-button" onClick={dedupeKnowledgeStandards}>
                    <RefreshCw size={15} />
                    整理重复标准
                  </button>
                  <div className="knowledge-coverage">
                    {(knowledgeCoverage?.industries ?? []).map((industry) => {
                      return (
                        <div key={industry.industry_id}>
                          <strong>{industry.name}</strong>
                          <span>
                            {industry.standard_count} 标准 · {industry.rule_count} 规则
                            {industry.clause_count ? ` · ${industry.clause_count} 切片` : ""}
                            {industry.pending_effective_count ? ` · ${industry.pending_effective_count} 待实施` : ""}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  {knowledgeCoverage?.note ? <p className="knowledge-note">{knowledgeCoverage.note}</p> : null}
                  <div className="standard-list">
                    {standards.slice(0, 8).map((standard) => (
                      <div key={standard.id}>
                        <strong>{standard.code}</strong>
                        <span>{standard.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {settingsLevel === "quote" ? (
                <div className="settings-panel-list">
                  <div className="knowledge-summary">
                    <FileText size={22} />
                    <div>
                      <strong>{selectedQuoteItem ? "项目详情" : "项目报价库"}</strong>
                      <span>
                        {selectedQuoteItem
                          ? "查看并编辑当前项目的报价、周期、标准和样品要求。"
                          : `已内置 ${detectionItems.length} 个检测/审核项目。审核结果可基于风险项推荐检测项目并生成报价单。`}
                      </span>
                    </div>
                  </div>
                  <div className="settings-form">
                    <label>
                      所属品类
                      <select
                        value={quoteItemForm.industry_id || industries[0]?.id || ""}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, industry_id: event.target.value }))}
                      >
                        {industries.map((industry) => (
                          <option key={industry.id} value={industry.id}>
                            {industry.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      项目编号
                      <input
                        value={quoteItemForm.code}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, code: event.target.value }))}
                        placeholder="例如：FOOD-LABEL-001"
                      />
                    </label>
                    <label>
                      项目名称
                      <input
                        value={quoteItemForm.name}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, name: event.target.value }))}
                        placeholder="例如：预包装食品标签合规审核"
                      />
                    </label>
                    <label>
                      报价金额
                      <input
                        type="number"
                        min="0"
                        value={quoteItemForm.price}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, price: event.target.value }))}
                        placeholder="例如：500"
                      />
                    </label>
                    <label>
                      方法/依据标准
                      <input
                        value={quoteItemForm.method_standard}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, method_standard: event.target.value }))}
                        placeholder="例如：GB 7718-2011"
                      />
                    </label>
                    <label>
                      判定标准
                      <input
                        value={quoteItemForm.judgment_standard}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, judgment_standard: event.target.value }))}
                        placeholder="例如：GB 28050-2011"
                      />
                    </label>
                    <label>
                      周期/天
                      <input
                        type="number"
                        min="1"
                        value={quoteItemForm.cycle_days}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, cycle_days: event.target.value }))}
                      />
                    </label>
                    <label>
                      样品/资料要求
                      <input
                        value={quoteItemForm.sample_amount}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, sample_amount: event.target.value }))}
                        placeholder="例如：标签照片或包装样 1 份"
                      />
                    </label>
                    <label>
                      套餐/分组
                      <input
                        value={quoteItemForm.package_name}
                        onChange={(event) => setQuoteItemForm((current) => ({ ...current, package_name: event.target.value }))}
                        placeholder="例如：基础报价库"
                      />
                    </label>
                  </div>
                  <div className="quote-actions">
                    <button className="primary-button" onClick={selectedQuoteItem ? updateQuoteItem : saveQuoteItem}>
                      <Save size={15} />
                      {selectedQuoteItem ? "保存修改" : "添加项目"}
                    </button>
                    {selectedQuoteItem ? (
                      <>
                        <button className="ghost-button" onClick={newQuoteItem}>
                          <FileText size={15} />
                          新建项目
                        </button>
                        <button className="danger-button" onClick={deleteQuoteItem}>
                          <X size={15} />
                          删除项目
                        </button>
                      </>
                    ) : null}
                    <button className="ghost-button" onClick={() => quoteImportInputRef.current?.click()}>
                      <Upload size={15} />
                      批量导入报价文档
                    </button>
                    <button className="ghost-button" onClick={dedupeQuoteItems}>
                      <RefreshCw size={15} />
                      整理重复项目
                    </button>
                  </div>
                  <div className="quote-import-hint">
                    支持 Excel/CSV 表格，也支持 Word/PDF/TXT 报价文档。表格列建议包含：项目名称、价格、周期、方法标准、判定标准、样品量、套餐。
                  </div>
                  <div className="quote-item-list">
                    {detectionItems.slice(0, 10).map((item) => (
                      <div key={item.id} className={selectedQuoteItemId === item.id ? "active" : ""}>
                        <span>
                          <strong>{item.name}</strong>
                          <small>{item.code} · {item.method_standard || "未填标准"}</small>
                        </span>
                        <b>¥{Number(item.price || 0).toFixed(0)}</b>
                        <em>{item.cycle_days} 天</em>
                        <button className="ghost-button compact" onClick={() => editQuoteItem(item)}>
                          查看
                        </button>
                        <button className="icon-button" onClick={() => void deleteQuoteItemById(item.id)} aria-label="删除报价项目">
                          <X size={13} />
                        </button>
                      </div>
                    ))}
                    {!detectionItems.length ? <p>暂无报价项目，可以先添加单个项目或导入报价文档。</p> : null}
                  </div>
                </div>
              ) : null}

              {settingsLevel === "ocr" ? (
                <div className="settings-panel-list">
                  <div className="settings-form single">
                    <label>
                      OCR 引擎
                      <select defaultValue="cascade">
                        <option value="cascade">多引擎级联：Windows 优先 RapidOCR，Mac 可用 Vision</option>
                        <option value="rapidocr">RapidOCR 优先（Windows 推荐）</option>
                        <option value="paddleocr">PaddleOCR 优先（中文复杂版面增强）</option>
                        <option value="macos">macOS Vision 本机识别（仅 Mac）</option>
                        <option value="cloud">云 OCR 备用</option>
                      </select>
                    </label>
                    <label>
                      识别语言
                      <select defaultValue="zh">
                        <option value="zh">中文优先</option>
                        <option value="mixed">中英混合</option>
                      </select>
                    </label>
                  </div>
                  <div className="switch-row">
                    <span>
                      <strong>低置信度提醒</strong>
                      <small>系统会保留候选 OCR 结果，低置信度时在结果区提示人工复核。</small>
                    </span>
                    <button className="toggle on" aria-label="低置信度提醒已开启" />
                  </div>
                </div>
              ) : null}

              {settingsLevel === "report" ? (
                <div className="settings-panel-list">
                  <div className="settings-form">
                    <label>
                      报告抬头
                      <input defaultValue="汇安检测合规审核报告" />
                    </label>
                    <label>
                      默认格式
                      <select defaultValue="both">
                        <option value="both">Word + PDF</option>
                        <option value="doc">Word</option>
                        <option value="pdf">PDF</option>
                      </select>
                    </label>
                  </div>
                  <div className="switch-row">
                    <span>
                      <strong>包含法规摘录</strong>
                      <small>导出时附带条款摘要和来源。</small>
                    </span>
                    <button className="toggle on" aria-label="包含法规摘录" />
                  </div>
                </div>
              ) : null}

              {settingsLevel === "advanced" ? (
                <div className="advanced-box">
                  <AlertTriangle size={22} />
                  <div>
                    <strong>高级设置默认折叠</strong>
                    <p>Token 上限、并发数、超时、日志级别、本地服务端口等在正式版中放在这里，避免普通用户误操作。</p>
                  </div>
                </div>
              ) : null}
            </section>
          </div>
        </div>
      ) : null}

      {confirmSettingsClose ? (
        <div className="modal-layer confirm-layer" role="dialog" aria-modal="true">
          <div className="confirm-modal">
            <div className="modal-head">
              <div>
                <h2>保存这次设置吗？</h2>
                <p>模型供应商配置已有改动，直接关闭会丢失这些修改。</p>
              </div>
              <button className="icon-button" onClick={() => setConfirmSettingsClose(false)} aria-label="取消关闭确认">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-actions">
              <button className="ghost-button" onClick={discardSettingsChanges}>
                放弃修改
              </button>
              <button className="primary-button" onClick={() => void saveModelProvider({ closeAfterSave: true })}>
                <Save size={15} />
                保存并关闭
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {exportOpen && currentTask ? (
        <div className="modal-layer" role="dialog" aria-modal="true">
          <div className="export-modal">
            <div className="modal-head">
              <div>
                <h2>导出报告</h2>
                <p>桌面端可选择保存位置；浏览器中会保存到默认下载目录。Word 可继续编辑，PDF 适合归档发送。</p>
              </div>
              <button className="icon-button" onClick={() => setExportOpen(false)} aria-label="关闭导出弹窗">
                <X size={16} />
              </button>
            </div>
            <div className="export-choice">
              <button onClick={downloadWord}>
                <FileText size={20} />
                <strong>Word 文档</strong>
                <span>可继续编辑依据和建议</span>
              </button>
              <button onClick={downloadPdf}>
                <Download size={20} />
                <strong>PDF 文件</strong>
                <span>含法规依据，适合归档</span>
              </button>
            </div>
            <div className="report-includes">
              <span>
                <Check size={13} />
                风险汇总
              </span>
              <span>
                <Check size={13} />
                标签原文
              </span>
              <span>
                <Check size={13} />
                法规依据
              </span>
              <span>
                <Check size={13} />
                条款摘录
              </span>
              <span>
                <Check size={13} />
                修改建议
              </span>
            </div>
            <div className="report-preview">
              <strong>{taskTitle(currentTask)}</strong>
              <span>
                {getConclusion(findings, riskOverrides)} · 高 {summary.high} / 中 {summary.medium} / 低 {summary.low}
              </span>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? <div className="toast success">{toast}</div> : null}
      {error ? (
        <div className="toast error">
          <span>{error}</span>
          <button onClick={() => setError("")}>关闭</button>
        </div>
      ) : null}
    </main>
  );
}
