import { motion } from "framer-motion";
import { Check, Loader2, AlertCircle, Clock, ArrowRight } from "lucide-react";
import type { CoordinationStep, CoordinationReport } from "@/types/protocol";

const statusConfig = {
  pending: { icon: Clock, color: "text-muted-foreground", bg: "bg-muted", ring: "ring-muted" },
  running: { icon: Loader2, color: "text-primary", bg: "bg-primary/10", ring: "ring-primary/30" },
  completed: { icon: Check, color: "text-accent", bg: "bg-accent/10", ring: "ring-accent/30" },
  failed: { icon: AlertCircle, color: "text-destructive", bg: "bg-destructive/10", ring: "ring-destructive/30" },
};

const roleAccent: Record<string, string> = {
  buyer: "border-l-primary",
  supplier: "border-l-accent",
  logistics: "border-l-warning",
  compliance: "border-l-destructive",
};

const cleanResult = (raw: string) => {
  let text = raw?.trim() || "";
  if (text.startsWith("```")) {
    text = text.replace(/^```(json)?/i, "").replace(/```$/i, "").trim();
  }
  let pretty = "";
  try {
    const parsed = JSON.parse(text);
    pretty = JSON.stringify(parsed, null, 2);
  } catch {
    pretty = text;
  }
  const summary =
    pretty.length > 140 ? `${pretty.slice(0, 140).replace(/\s+/g, " ")}…` : pretty;
  return { summary, pretty };
};

const StepItem = ({ step, index }: { step: CoordinationStep; index: number }) => {
  const config = statusConfig[step.status];
  const Icon = config.icon;
  const { summary, pretty } = cleanResult(step.result || "");

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.15, duration: 0.4 }}
      className={`relative bg-card border border-border rounded-xl p-4 border-l-2 ${roleAccent[step.agentRole] || "border-l-primary"}`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-1.5 rounded-full ${config.bg} ring-1 ${config.ring} mt-0.5`}>
          <Icon className={`w-3.5 h-3.5 ${config.color} ${step.status === "running" ? "animate-spin" : ""}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted-foreground">{step.agentName}</span>
            {step.duration && (
              <span className="text-[10px] font-mono text-muted-foreground/60">{step.duration}s</span>
            )}
          </div>
          <p className="text-sm font-medium text-foreground mb-1">{step.action}</p>
          <details className="group text-xs text-muted-foreground">
            <summary className="cursor-pointer list-none">
              <span className="inline-block">{summary || "Details available"}</span>
              <span className="ml-2 text-[10px] text-primary/80 group-open:hidden">View</span>
            </summary>
            <pre className="mt-2 whitespace-pre-wrap text-[11px] text-muted-foreground/90 bg-secondary/40 rounded-md p-2 border border-border">
              {pretty || "No details"}
            </pre>
          </details>
        </div>
      </div>
    </motion.div>
  );
};

interface CoordinationFlowProps {
  report: CoordinationReport | null;
}

const CoordinationFlow = ({ report }: CoordinationFlowProps) => {
  if (!report || report.status === "idle") {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center gap-2 text-muted-foreground">
          <ArrowRight className="w-4 h-4" />
          <span className="text-sm">Submit an intent to start coordination</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-lg font-semibold text-foreground">Coordination Cascade</h2>
        <div className="inline-flex items-center gap-2 text-xs font-mono text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent/60 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
          </span>
          Live feed
        </div>
        <span
          className={`text-xs font-mono px-2 py-0.5 rounded-full border ${
            report.status === "completed"
              ? "text-accent border-accent/30 bg-accent/10"
              : report.status === "running"
              ? "text-primary border-primary/30 bg-primary/10"
              : "text-destructive border-destructive/30 bg-destructive/10"
          }`}
        >
          {report.status}
        </span>
      </div>

      {/* Intent */}
      <div className="mb-5 p-3 rounded-lg bg-secondary/50 border border-border">
        <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">Intent</span>
        <p className="text-sm text-foreground mt-1 font-medium">{report.intent}</p>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {report.steps.map((step, i) => (
          <StepItem key={step.id} step={step} index={i} />
        ))}
      </div>

      {/* Summary */}
      {report.summary && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: report.steps.length * 0.15 + 0.2 }}
          className="mt-6 p-5 rounded-xl bg-gradient-to-br from-primary/5 to-accent/5 border border-primary/20 glow-primary"
        >
          <h3 className="text-sm font-semibold text-foreground mb-2">Coordination Summary</h3>
          <p className="text-sm text-muted-foreground mb-4">{report.summary}</p>
          <div className="flex gap-6">
            {report.totalCost && (
              <div>
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                  Total Cost
                </span>
                <p className="text-xl font-bold text-gradient-primary">
                  ${report.totalCost.toLocaleString()}
                </p>
              </div>
            )}
            {report.leadTime && (
              <div>
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                  Lead Time
                </span>
                <p className="text-xl font-bold text-foreground">{report.leadTime}</p>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Full Report */}
      {report.raw && (
        <div className="mt-6">
          <details className="group rounded-xl border border-border bg-card/70 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-foreground">
              Full Coordination Report (raw)
            </summary>
            <pre className="mt-3 max-h-80 overflow-auto text-xs text-muted-foreground whitespace-pre-wrap">
              {JSON.stringify(report.raw, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};

export default CoordinationFlow;
