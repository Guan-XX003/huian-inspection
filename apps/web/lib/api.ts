export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type Industry = {
  id: string;
  name: string;
  code: string;
  description: string;
  status: string;
};

export type DashboardSummary = {
  industry_count: number;
  standard_count: number;
  rule_count: number;
  detection_item_count: number;
  audit_task_count: number;
  quote_count: number;
  needs_review_count: number;
};

export type HealthStatus = {
  status: string;
  app: string;
  ocr_provider: string;
  document_parser_provider: string;
  model_provider: string;
  model_gateway: string;
};

export type ModelProvider = {
  id: string;
  provider: string;
  model: string;
  base_url: string;
  supports_vision: boolean;
  supports_json: boolean;
  supports_tools: boolean;
  default_for_text: boolean;
  default_for_vision: boolean;
  status: string;
  api_key_hint: string;
  api_key_saved: boolean;
};

export type DetectionItem = {
  id: string;
  industry_id: string;
  code: string;
  name: string;
  method_standard: string;
  judgment_standard: string;
  price: number;
  cycle_days: number;
  sample_amount: string;
  package_name: string;
  status: string;
};

export type Standard = {
  id: string;
  industry_id: string;
  code: string;
  name: string;
  version: string;
  effective_date: string;
  expiry_date: string;
  status: string;
  source_file: string;
  clauses: Array<Record<string, unknown>>;
};

export type KnowledgeCoverageIndustry = {
  industry_id: string;
  code: string;
  name: string;
  standard_count: number;
  rule_count: number;
  clause_count: number;
  pending_effective_count: number;
  source_ready_count: number;
  sample_standards: Array<{
    code: string;
    name: string;
    version: string;
    effective_date: string;
  }>;
};

export type KnowledgeCoverage = {
  total_standards: number;
  total_rules: number;
  total_clauses: number;
  source_ready_count: number;
  industries: KnowledgeCoverageIndustry[];
  note: string;
};

export type AuditRule = {
  id: string;
  industry_id: string;
  standard_id: string | null;
  name: string;
  rule_type: string;
  field_key: string;
  trigger: string;
  risk_level: string;
  suggestion: string;
  status: string;
};

export type UploadedFile = {
  id: string;
  original_name: string;
  path: string;
  content_type: string;
  size: number;
};

export type AuditFinding = {
  finding_id: string;
  title: string;
  risk_level: string;
  field_key: string;
  evidence_text: string;
  reason: string;
  suggestion: string;
  standard_code: string;
  standard_clause: string;
  source_excerpt: string;
  confidence: number;
  needs_human_review: boolean;
  recommended_item_codes: string[];
};

export type LabelPrecheck = {
  summary?: string;
  recognition_score?: number;
  completeness_score?: number;
  required_fields?: string[];
  missing_fields?: string[];
  low_confidence_fields?: string[];
  sections?: Array<{
    field_key: string;
    label: string;
    text: string;
    present: boolean;
    confidence: number;
    source: string;
  }>;
};

export type AuditTask = {
  id: string;
  industry_id: string;
  file_id: string;
  customer_name: string;
  document_type: string;
  conversation_id: string;
  session_title: string;
  session_group: string;
  session_archived: boolean;
  status: string;
  ocr_result: { text?: string; average_confidence?: number; label_precheck?: LabelPrecheck };
  extracted_fields: Record<string, string>;
  rule_results: Array<Record<string, string | boolean>>;
  model_result: Record<string, string | boolean | AuditFinding[]>;
  final_report: {
    summary?: string;
    risk_level?: string;
    route?: string;
    vision_primary?: boolean;
    industry?: string;
    label_precheck?: LabelPrecheck;
    standards?: string[];
    compliant_items?: Array<Record<string, unknown>>;
    findings?: AuditFinding[];
    disclaimer?: string;
    recommended_item_codes?: string[];
  };
  model_used: string;
  needs_human_review: boolean;
  created_at: string;
  completed_at?: string | null;
};

export type Quote = {
  id: string;
  quote_no: string;
  audit_task_id: string | null;
  customer_name: string;
  items_json: Array<{
    code: string;
    name: string;
    method_standard: string;
    price: number;
    cycle_days: number;
    sample_amount: string;
    package_name: string;
    lab_name?: string;
    lab_qualification?: string;
    lab_strengths?: string;
    service_note?: string;
  }>;
  subtotal: number;
  tax_rate: number;
  discount_rate: number;
  total: number;
  valid_until: string;
  status: string;
};

export type ImportTask = {
  id: string;
  filename: string;
  file_path: string;
  file_type: string;
  target_library: string;
  status: string;
  model: string;
  parsed_result: Record<string, unknown>;
  error_message: string;
  created_at: string;
};

export type ToolDetail = {
  label: string;
  ok: boolean;
  note: string;
};

export type ToolStatus = {
  id: string;
  name: string;
  category: string;
  status: "ready" | "partial" | "missing";
  enabled: boolean;
  summary: string;
  metrics?: Record<string, number>;
  details: ToolDetail[];
  install_hint: string;
  github: string[];
};

export type ToolsStatusResponse = {
  tools: ToolStatus[];
  summary: {
    ready: number;
    partial: number;
    missing: number;
    total: number;
  };
};

export type ToolTestResult = {
  tool_id: string;
  status: "ready" | "partial" | "missing";
  message: string;
  details?: unknown;
};

export const api = {
  health: () => request<HealthStatus>("/api/health"),
  dashboard: () => request<DashboardSummary>("/api/admin/dashboard"),
  toolsStatus: () => request<ToolsStatusResponse>("/api/admin/tools/status"),
  testTool: (toolId: string) =>
    request<ToolTestResult>(`/api/admin/tools/${encodeURIComponent(toolId)}/test`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  industries: () => request<Industry[]>("/api/admin/industries"),
  standards: () => request<Standard[]>("/api/admin/standards"),
  knowledgeCoverage: () => request<KnowledgeCoverage>("/api/admin/knowledge/coverage"),
  auditRules: () => request<AuditRule[]>("/api/admin/audit-rules"),
  detectionItems: () => request<DetectionItem[]>("/api/admin/detection-items"),
  modelProviders: () => request<ModelProvider[]>("/api/admin/model-providers"),
  auditTasks: () => request<AuditTask[]>("/api/audit/tasks"),
  updateAuditTask: (id: string, payload: { session_title: string; session_group: string }) =>
    request<AuditTask>(`/api/audit/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteAuditTask: (id: string) =>
    request<AuditTask>(`/api/audit/tasks/${id}`, {
      method: "DELETE",
    }),
  quotes: () => request<Quote[]>("/api/quotes"),
  uploadFile: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_BASE}/api/files/upload`, { method: "POST", body: form });
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<UploadedFile>;
  },
  createAuditTask: (payload: {
    industry_id: string;
    file_id: string;
    customer_name: string;
    document_type: string;
    model_provider_id?: string;
    conversation_id?: string;
  }) =>
    request<AuditTask>("/api/audit/tasks", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  quoteFromAudit: (auditId: string) =>
    request<Quote>(`/api/quotes/from-audit/${auditId}`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  createQuote: (payload: {
    customer_name: string;
    detection_item_ids: string[];
    discount_rate?: number;
    tax_rate?: number;
  }) =>
    request<Quote>("/api/quotes", {
      method: "POST",
      body: JSON.stringify({ discount_rate: 1, tax_rate: 0.06, ...payload }),
    }),
  createStandard: (payload: {
    industry_id: string;
    code: string;
    name: string;
    version: string;
    effective_date: string;
    expiry_date?: string;
    status?: string;
    source_file?: string;
    clauses?: Array<Record<string, unknown>>;
  }) =>
    request<Standard>("/api/admin/standards", {
      method: "POST",
      body: JSON.stringify({ status: "active", source_file: "", clauses: [], ...payload }),
    }),
  updateStandard: (id: string, payload: {
    industry_id: string;
    code: string;
    name: string;
    version: string;
    effective_date: string;
    expiry_date?: string;
    status?: string;
    source_file?: string;
    clauses?: Array<Record<string, unknown>>;
  }) =>
    request<Standard>(`/api/admin/standards/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ expiry_date: "", source_file: "", clauses: [], ...payload }),
    }),
  createAuditRule: (payload: {
    industry_id: string;
    standard_id?: string | null;
    name: string;
    rule_type: string;
    field_key: string;
    trigger: string;
    risk_level: string;
    suggestion: string;
    status?: string;
  }) =>
    request<AuditRule>("/api/admin/audit-rules", {
      method: "POST",
      body: JSON.stringify({ status: "active", ...payload }),
    }),
  updateAuditRule: (id: string, payload: {
    industry_id: string;
    standard_id?: string | null;
    name: string;
    rule_type: string;
    field_key: string;
    trigger: string;
    risk_level: string;
    suggestion: string;
    status?: string;
  }) =>
    request<AuditRule>(`/api/admin/audit-rules/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "active", ...payload }),
    }),
  createDetectionItem: (payload: {
    industry_id: string;
    code: string;
    name: string;
    method_standard: string;
    judgment_standard?: string;
    price: number;
    cycle_days: number;
    sample_amount: string;
    package_name: string;
    status?: string;
  }) =>
    request<DetectionItem>("/api/admin/detection-items", {
      method: "POST",
      body: JSON.stringify({ status: "active", judgment_standard: "", ...payload }),
    }),
  updateDetectionItem: (id: string, payload: {
    industry_id: string;
    code: string;
    name: string;
    method_standard: string;
    judgment_standard?: string;
    price: number;
    cycle_days: number;
    sample_amount: string;
    package_name: string;
    status?: string;
  }) =>
    request<DetectionItem>(`/api/admin/detection-items/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ judgment_standard: "", status: "active", ...payload }),
    }),
  createModelProvider: (payload: {
    provider: string;
    model: string;
    base_url?: string;
    api_key_hint?: string;
    api_key_secret?: string;
    supports_vision?: boolean;
    supports_json?: boolean;
    supports_tools?: boolean;
    default_for_text?: boolean;
    default_for_vision?: boolean;
    status?: string;
  }) =>
    request<ModelProvider>("/api/admin/model-providers", {
      method: "POST",
      body: JSON.stringify({ status: "active", supports_json: true, ...payload }),
    }),
  modelProviderSecret: (id: string) => request<{ api_key_secret: string }>(`/api/admin/model-providers/${id}/secret`),
  deactivate: (kind: "standards" | "audit-rules" | "detection-items" | "model-providers", id: string) =>
    request<unknown>(`/api/admin/${kind}/${id}`, { method: "DELETE" }),
  deleteConfig: (kind: "standards" | "audit-rules" | "detection-items" | "model-providers", id: string) =>
    request<unknown>(`/api/admin/${kind}/${id}?hard=true`, { method: "DELETE" }),
  dedupeDetectionItems: () =>
    request<{ duplicate_groups: number; inactive: number; message: string }>("/api/admin/detection-items/dedupe", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  dedupeModelProviders: () =>
    request<ModelProvider[]>("/api/admin/model-providers/dedupe", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  dedupeStandards: () =>
    request<{ duplicate_groups: number; inactive: number; removed: number; relinked_rules: number; message: string }>("/api/admin/knowledge/dedupe-standards", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  importStandards: async (industryId: string, file: File) => {
    const form = new FormData();
    form.append("industry_id", industryId);
    form.append("file", file);
    const response = await fetch(`${API_BASE}/api/admin/standard-rule-library/import`, { method: "POST", body: form });
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<{ standards_created: number; rules_created: number; clause_chunks_created?: number; import_task?: ImportTask; message: string }>;
  },
  importStandardsFromUrl: (industryId: string, url: string) =>
    request<{ standards_created: number; rules_created: number; clause_chunks_created?: number; import_task?: ImportTask; message: string }>(
      "/api/admin/standard-rule-library/import-url",
      {
        method: "POST",
        body: JSON.stringify({ industry_id: industryId, url }),
      },
    ),
  importQuoteLibrary: async (industryId: string, file: File) => {
    const form = new FormData();
    form.append("industry_id", industryId);
    form.append("file", file);
    const response = await fetch(`${API_BASE}/api/admin/quote-library/import`, { method: "POST", body: form });
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<{ items_created: number; import_task?: ImportTask; message: string }>;
  },
  importTask: (id: string) => request<ImportTask>(`/api/admin/import-tasks/${id}`),
  importTasks: (targetLibrary?: string) =>
    request<ImportTask[]>(`/api/admin/import-tasks${targetLibrary ? `?target_library=${encodeURIComponent(targetLibrary)}` : ""}`),
  deleteImportTask: (id: string) =>
    request<ImportTask>(`/api/admin/import-tasks/${id}`, { method: "DELETE" }),
};
