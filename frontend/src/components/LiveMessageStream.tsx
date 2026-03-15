import { motion } from "framer-motion";
import { Activity, CheckCircle2, AlertTriangle } from "lucide-react";

interface LiveMessageStreamProps {
  events: { id: string; type: string; actor: string; action: string; message: string; ts: string }[];
}

const typeIcon = (type: string) => {
  if (type === "status") return Activity;
  if (type === "error") return AlertTriangle;
  return CheckCircle2;
};

const LiveMessageStream = ({ events }: LiveMessageStreamProps) => {
  return (
    <div className="bg-card border border-border rounded-xl p-5 overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Live Message Stream</h3>
        <span className="text-[10px] font-mono text-muted-foreground">{events.length} events</span>
      </div>

      <div className="max-h-64 overflow-auto space-y-3 pr-2">
        {events.length === 0 && (
          <div className="text-xs text-muted-foreground">Events will appear here during orchestration.</div>
        )}
        {events.map((e) => {
          const Icon = typeIcon(e.type);
          return (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 rounded-lg border border-border bg-secondary/40"
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-3.5 h-3.5 text-accent" />
                <span className="text-xs font-mono text-muted-foreground">{e.actor}</span>
                <span className="text-[10px] text-muted-foreground/70">{e.action}</span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-3">{e.message || "—"}</p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default LiveMessageStream;
