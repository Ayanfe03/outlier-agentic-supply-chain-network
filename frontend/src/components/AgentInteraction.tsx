import { motion } from "framer-motion";

interface AgentInteractionProps {
  isRunning: boolean;
}

const roleColor: Record<string, string> = {
  buyer: "hsl(248, 80%, 60%)",
  supplier: "hsl(160, 80%, 55%)",
  logistics: "hsl(38, 92%, 55%)",
  compliance: "hsl(0, 75%, 60%)",
};

const AgentInteraction = ({ isRunning }: AgentInteractionProps) => {
  const width = 840;
  const height = 380;
  const center = { x: width / 2, y: height / 2 + 10 };
  const radius = 150;

  const nodes = [
    { id: "supplier-1", label: "supplier-1", role: "supplier", action: "request_parts" },
    { id: "logistics-1", label: "logistics-1", role: "logistics", action: "request_routing" },
    { id: "compliance-1", label: "compliance-1", role: "compliance", action: "verify_compliance" },
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-10 mb-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20" />
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-foreground">Agent Interaction</h3>
          <span className="text-xs font-mono px-2 py-0.5 rounded-full border text-primary border-primary/30 bg-primary/10">
            active
          </span>
        </div>

        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-80">
          <defs>
            <filter id="agent-glow">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Connections (buyer -> all) */}
          {nodes.map((node, i) => {
            const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const x = center.x + radius * Math.cos(angle);
            const y = center.y + radius * Math.sin(angle);
            return (
              <motion.line
                key={`line-${node.id}`}
                x1={center.x}
                y1={center.y}
                x2={x}
                y2={y}
                stroke="hsl(210, 20%, 60%)"
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray="10 10"
                animate={
                  isRunning
                    ? { strokeDashoffset: [0, -24], opacity: [0.5, 1, 0.5] }
                    : { strokeDashoffset: 0, opacity: 0.35 }
                }
                transition={
                  isRunning
                    ? { repeat: Infinity, duration: 2.2, ease: "easeInOut" }
                    : { duration: 0.2 }
                }
              />
            );
          })}

          {/* Buyer center node */}
          <g filter="url(#agent-glow)">
            <motion.circle
              cx={center.x}
              cy={center.y}
              r={42}
              fill="hsl(220, 18%, 10%)"
              stroke={roleColor.buyer}
              strokeWidth="3"
              animate={isRunning ? { r: [42, 48, 42] } : { r: 42 }}
              transition={
                isRunning
                  ? { repeat: Infinity, duration: 2.0, ease: "easeInOut" }
                  : { duration: 0.2 }
              }
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

          {/* Outer nodes */}
          {nodes.map((node, i) => {
            const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
            const x = center.x + radius * Math.cos(angle);
            const y = center.y + radius * Math.sin(angle);
            const color = roleColor[node.role] || roleColor.buyer;
            return (
              <g key={node.id} filter="url(#agent-glow)">
                <motion.circle
                  cx={x}
                  cy={y}
                  r={30}
                  fill="hsl(220, 18%, 10%)"
                  stroke={color}
                  strokeWidth="3"
                  animate={isRunning ? { r: [30, 34, 30], opacity: [0.85, 1, 0.85] } : { r: 30, opacity: 0.85 }}
                  transition={
                    isRunning
                      ? { repeat: Infinity, duration: 2.4, ease: "easeInOut" }
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
                  {node.label}
                </text>
                <text
                  x={x}
                  y={y - 40}
                  textAnchor="middle"
                  fontSize="10"
                  fill="hsl(210, 20%, 65%)"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {node.action}
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
