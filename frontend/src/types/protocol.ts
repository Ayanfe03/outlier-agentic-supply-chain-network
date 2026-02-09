// Types for the Outlier Agentic Protocol
export interface AgentFact {
  id: string;
  name: string;
  role: "buyer" | "supplier" | "logistics" | "compliance";
  capabilities: string[];
  jurisdiction: string;
  status: "online" | "offline" | "processing";
  policies: string[];
  lastSeen: string;
}

export interface CoordinationStep {
  id: string;
  agentId: string;
  agentName: string;
  agentRole: AgentFact["role"];
  action: string;
  result: string;
  status: "pending" | "running" | "completed" | "failed";
  timestamp: string;
  duration?: number;
}

export interface CoordinationReport {
  id: string;
  intent: string;
  status: "idle" | "running" | "completed" | "failed";
  steps: CoordinationStep[];
  summary?: string;
  totalCost?: number;
  leadTime?: string;
  createdAt: string;
  origin?: string;
  destination?: string;
  route?: string;
  part?: string;
  raw?: unknown;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "agent" | "facility" | "material" | "route";
  x: number;
  y: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  type: "material" | "information" | "routing";
}
