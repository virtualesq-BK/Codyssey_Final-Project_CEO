export type BusinessStage = "idea" | "validation" | "early" | "growth";
export type AgentStatus = "pending" | "running" | "success" | "partial" | "failed" | "skipped";
export type Decision = "GO" | "PIVOT" | "VALIDATE_MORE" | "STOP";

export interface AnalyzeRequest {
  title: string;
  problem: string;
  customer: string;
  solution: string;
  industry: string;
  location: string;
  business_stage: BusinessStage;
}

export interface Evidence {
  title: string;
  source: string;
  url?: string;
  content: string;
  confidence: number;
}

export interface AgentResult {
  agent_name: string;
  status: AgentStatus;
  summary: string;
  findings: Record<string, unknown>[];
  evidence: Evidence[];
  recommendations: string[];
  confidence: number;
  error_message?: string;
  execution_time_ms?: number;
}

export interface DecisionResult {
  summary: string;
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  risks: string[];
  financial_summary: string;
  validation_items: string[];
  action_plan: string[];
  decision: Decision;
  confidence: number;
  disclaimer: string;
}

export interface WorkflowResult {
  idea_id: string;
  status: AgentStatus;
  agent_results: Record<string, AgentResult>;
  decision_result?: DecisionResult;
  total_execution_time_ms?: number;
  created_at: string;
}

export interface AnalyzeResponse {
  idea_id: string;
  workflow_result: WorkflowResult;
}

export async function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch("/api/v1/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "알 수 없는 오류" }));
    throw new Error(err.detail ?? "분석 요청 실패");
  }
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch("/api/v1/health");
    return res.ok;
  } catch {
    return false;
  }
}
