import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { CoordinationReport } from "@/types/protocol";

interface AgentInteractionProps {
  report: CoordinationReport | null;
  isRunning: boolean;
  currentPhase?: {
    agentName?: string;
    agentRole?: string;
    action?: string;
  } | null;
}

const roleColor: Record<string, string> = {
  buyer: "hsl(248, 80%, 60%)",
  supplier: "hsl(160, 80%, 55%)",
  logistics: "hsl(38, 92%, 55%)",
  compliance: "hsl(0, 75%, 60%)",
};

const AgentInteraction = ({ report, isRunning, currentPhase }: AgentInteractionProps) => {
  if (!report) return null;
  const rawSteps = report.steps || [];
  const hasBuyer = rawSteps.some((s) => s.agentRole === "buyer");
  const steps =
    isRunning && rawSteps.length === 0
      ? [
          { id: "supplier-live", agentName: "supplier-1", agentRole: "supplier", action: "request_parts" },
          { id: "logistics-live", agentName: "logistics-1", agentRole: "logistics", action: "request_routing" },
          { id: "compliance-live", agentName: "compliance-1", agentRole: "compliance", action: "verify_compliance" },
        ]
      : rawSteps.filter((s) => s.agentRole !== "buyer");
  if (!steps.length) return null;
  const phaseIndex = currentPhase
    ? steps.findIndex(
        (s) =>
          (currentPhase.agentName && s.agentName === currentPhase.agentName) ||
          (currentPhase.agentRole && s.agentRole === currentPhase.agentRole)
      )
    : -1;
  const [fallbackIndex, setFallbackIndex] = useState(0);

  useEffect(() => {
    if (!isRunning || phaseIndex >= 0 || steps.length === 0) {
      setFallbackIndex(0);
      return;
    }
    const id = setInterval(() => {
      setFallbackIndex((i) => (i + 1) % steps.length);
    }, 900);
    return () => clearInterval(id);
  }, [isRunning, phaseIndex, steps.length]);

  const currentIndex =
    isRunning && phaseIndex >= 0 ? phaseIndex : isRunning ? fallbackIndex : -1;

  const width = 840;
  const height = 240;
  const center = { x: width / 2, y: height / 2 + 10 };
  const radius = 150;

  return (
    <div className="bg-card border border-border rounded-xl p-4 mb-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20" />
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-foreground">Live Agent Interaction</h3>
          <span
            className={`text-xs font-mono px-2 py-0.5 rounded-full border ${
              isRunning
                ? "text-primary border-primary/30 bg-primary/10"
                : "text-muted-foreground border-border bg-secondary/40"
            }`}
          >
            {isRunning ? "running" : "idle"}
          </span>
        </div>

        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-56">
          <defs>
            <filter id="agent-glow">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Connections (buyer -> current) */}
          {steps.map((step, i) => {
            const angle = (i / steps.length) * Math.PI * 2 - Math.PI / 2;
            const x = center.x + radius * Math.cos(angle);
            const y = center.y + radius * Math.sin(angle);
            const active = i === currentIndex;
            return (
              <motion.line
                key={`line-${step.id}`}
                x1={center.x}
                y1={center.y}
                x2={x}
                y2={y}
                stroke="hsl(210, 20%, 60%)"
                strokeWidth={active ? "5" : "3"}
                strokeLinecap="round"
                strokeDasharray="10 10"
                animate={
                  isRunning && active
                    ? { strokeDashoffset: [0, -24], opacity: [0.6, 1, 0.6] }
                    : { strokeDashoffset: 0, opacity: 0.4 }
                }
                transition={isRunning && active ? { repeat: Infinity, duration: 0.9 } : { duration: 0.2 }}
              />
            );
          })}

          {/* Buyer center node */}
          <g filter="url(#agent-glow)">
            <motion.circle
              cx={center.x}
              cy={center.y}
              r={40}
              fill="hsl(220, 18%, 10%)"
              stroke={roleColor.buyer}
              strokeWidth="3"
              animate={isRunning ? { r: [40, 46, 40] } : { r: 40 }}
              transition={isRunning ? { repeat: Infinity, duration: 1.2 } : { duration: 0.2 }}
            />
            <circle cx={center.x} cy={center.y} r={12} fill={roleColor.buyer} />
            <text
              x={center.x}
              y={center.y + 60}
              textAnchor="middle"
              fontSize="12"
              fill="hsl(210, 20%, 85%)"
              fontFamily="Inter, sans-serif"
              fontWeight="600"
            >
              buyer-1
            </text>
          </g>

          {/* Outer agent nodes */}
          {steps.map((step, i) => {
            const angle = (i / steps.length) * Math.PI * 2 - Math.PI / 2;
            const x = center.x + radius * Math.cos(angle);
            const y = center.y + radius * Math.sin(angle);
            const color = roleColor[step.agentRole] || roleColor.buyer;
            const active = i === currentIndex;
            return (
              <g key={step.id} filter="url(#agent-glow)">
                <motion.circle
                  cx={x}
                  cy={y}
                  r={30}
                  fill="hsl(220, 18%, 10%)"
                  stroke={color}
                  strokeWidth="3"
                  animate={
                    isRunning && active
                      ? { r: [30, 36, 30], opacity: [0.9, 1, 0.9] }
                      : { r: 30, opacity: 0.85 }
                  }
                  transition={
                    isRunning && active
                      ? { repeat: Infinity, duration: 1.0 }
                      : { duration: 0.2 }
                  }
                />
                <circle cx={x} cy={y} r={9} fill={color} />
                <text
                  x={x}
                  y={y + 50}
                  textAnchor="middle"
                  fontSize="11"
                  fill="hsl(210, 20%, 85%)"
                  fontFamily="Inter, sans-serif"
                  fontWeight="600"
                >
                  {step.agentName}
                </text>
                <text
                  x={x}
                  y={y - 40}
                  textAnchor="middle"
                  fontSize="10"
                  fill="hsl(210, 20%, 65%)"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {step.action}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

export default AgentInteraction;
