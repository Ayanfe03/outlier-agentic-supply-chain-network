import type { AgentFact, CoordinationReport, CoordinationStep } from "@/types/protocol";

const REGISTRY_URL = import.meta.env.VITE_REGISTRY_URL || "http://localhost:8000";
const BUYER_URL = import.meta.env.VITE_BUYER_URL || "http://localhost:8002";

export const getBuyerWsUrl = () => {
  const url = new URL(BUYER_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  return url.toString();
};

const roleMap = (role: string): AgentFact["role"] => {
  const r = role.toLowerCase();
  if (r.includes("supplier")) return "supplier";
  if (r.includes("logistics")) return "logistics";
  if (r.includes("compliance")) return "compliance";
  return "buyer";
};

const toAgentFact = (a: any): AgentFact => {
  const caps = a.capabilities ? Object.values(a.capabilities).flat() : [];
  const policies = a.policies ? Object.values(a.policies).flat() : [];
  const jurisdiction = a.jurisdiction?.country
    ? `${a.jurisdiction.country}${a.jurisdiction.state ? ", " + a.jurisdiction.state : ""}`
    : "Unknown";
  return {
    id: a.agent_id,
    name: a.agent_id,
    role: roleMap(a.role || "buyer"),
    capabilities: (caps as string[]).slice(0, 6),
    jurisdiction,
    status: "online",
    policies: (policies as string[]).slice(0, 6),
    lastSeen: new Date().toISOString(),
  };
};

const toReport = (payload: any, intent: string): CoordinationReport => {
  const report = payload?.report || payload || {};
  const exchanges = report.message_exchanges || [];
  const steps: CoordinationStep[] = exchanges
    .filter((m: any) => m && m.to && m.intent)
    .map((m: any, i: number) => ({
      id: `step-${i + 1}`,
      agentId: m.to,
      agentName: m.to,
      agentRole: roleMap(m.to),
      action: m.intent || "action",
      result: typeof m.response === "string" ? m.response : JSON.stringify(m.response || {}),
      status: "completed",
      timestamp: new Date().toISOString(),
    }));
  if (!steps.some((s) => s.agentRole === "buyer")) {
    steps.unshift({
      id: "step-buyer",
      agentId: "buyer-1",
      agentName: "buyer-1",
      agentRole: "buyer",
      action: "orchestrate",
      result: "intent received",
      status: "completed",
      timestamp: new Date().toISOString(),
    });
  }

  const summary = report.final_plan
    ? `Status: ${report.final_plan.status}. Route: ${report.final_plan.route}. Supplier: ${report.final_plan.supplier_used}.`
    : undefined;

  return {
    id: report.timestamp || `report-${Date.now()}`,
    intent: report.intent || intent,
    status: "completed",
    steps,
    summary,
    totalCost: typeof report.final_plan?.total_cost_estimate === "number" ? report.final_plan.total_cost_estimate : undefined,
    leadTime: report.final_plan?.lead_time_days ? `${report.final_plan.lead_time_days} days` : undefined,
    createdAt: report.timestamp || new Date().toISOString(),
    origin: report.origin,
    destination: report.destination,
    route: report.final_plan?.route,
    part: report.part,
    raw: report,
  };
};

export const apiService = {
  async getAgents(): Promise<AgentFact[]> {
    const res = await fetch(`${REGISTRY_URL}/agents`);
    if (!res.ok) {
      throw new Error("Failed to fetch agents from registry");
    }
    const data = await res.json();
    return data.map(toAgentFact);
  },

  async submitIntent(intent: string): Promise<CoordinationReport> {
    const res = await fetch(`${BUYER_URL}/intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent }),
    });
    if (!res.ok) {
      throw new Error("Coordination failed");
    }
    const payload = await res.json();
    return toReport(payload, intent);
  },
};
