import { motion } from "framer-motion";
import { useMemo, useRef } from "react";
import type { CoordinationReport } from "@/types/protocol";

interface GraphNode {
  id: string;
  label: string;
  type: "agent" | "facility" | "material" | "route";
  x: number;
  y: number;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
  type: "material" | "information" | "routing";
}

interface SupplyGraphProps {
  report: CoordinationReport | null;
}

const typeColors: Record<string, string> = {
  agent: "hsl(190, 95%, 50%)",
  facility: "hsl(145, 80%, 45%)",
  material: "hsl(38, 92%, 50%)",
  route: "hsl(215, 15%, 55%)",
};

const edgeColors: Record<string, string> = {
  material: "hsl(145, 80%, 45%)",
  information: "hsl(190, 95%, 50%)",
  routing: "hsl(38, 92%, 50%)",
};

const SupplyGraph = ({ report }: SupplyGraphProps) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const { nodes, edges } = useMemo(() => {
    if (!report || !report.steps.length) {
      return { nodes: [] as GraphNode[], edges: [] as GraphEdge[] };
    }
    const stepNodes: GraphNode[] = report.steps.map((s, i) => ({
      id: s.agentId,
      label: s.agentName,
      type: "agent",
      x: 80 + (i % 2) * 240,
      y: 60 + i * 90,
    }));
    const stepEdges: GraphEdge[] = report.steps.slice(1).map((s, i) => ({
      source: report.steps[i].agentId,
      target: s.agentId,
      label: report.steps[i + 1].action,
      type: "information",
    }));
    const facilityNodes: GraphNode[] = [];
    if (report.origin) {
      facilityNodes.push({ id: "origin", label: report.origin, type: "facility", x: 40, y: 320 });
    }
    if (report.destination) {
      facilityNodes.push({ id: "destination", label: report.destination, type: "facility", x: 360, y: 320 });
    }
    const facilityEdges: GraphEdge[] = [];
    if (report.origin && report.destination) {
      facilityEdges.push({
        source: "origin",
        target: "destination",
        label: report.route || "route",
        type: "routing",
      });
    }
    // Material flow: buyer -> supplier -> logistics -> destination (if present)
    const buyer = report.steps.find((s) => s.agentRole === "buyer")?.agentId;
    const supplier = report.steps.find((s) => s.agentRole === "supplier")?.agentId;
    const logistics = report.steps.find((s) => s.agentRole === "logistics")?.agentId;
    const part = report.part || "goods";
    if (buyer && supplier) {
      facilityEdges.push({ source: buyer, target: supplier, label: `order:${part}`, type: "material" });
    }
    if (supplier && logistics) {
      facilityEdges.push({ source: supplier, target: logistics, label: `ship:${part}`, type: "material" });
    }
    if (logistics && report.destination) {
      facilityEdges.push({ source: logistics, target: "destination", label: `deliver:${part}`, type: "material" });
    }
    return { nodes: [...stepNodes, ...facilityNodes], edges: [...stepEdges, ...facilityEdges] };
  }, [report]);

  const formatLabel = (label: string) => {
    const clean = label.replace(/\s+/g, " ").trim();
    return clean.length > 26 ? `${clean.slice(0, 23)}...` : clean;
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3 }}
    >
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-lg font-semibold text-foreground">Supply Graph</h2>
        <div className="flex items-center gap-3">
          {Object.entries(edgeColors).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <div className="w-3 h-0.5 rounded" style={{ backgroundColor: color }} />
              <span className="text-[10px] font-mono text-muted-foreground capitalize">{type}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-4 overflow-hidden relative">
        <div className="absolute inset-0 bg-grid opacity-30" />
        <svg ref={svgRef} viewBox="0 0 420 380" className="w-full h-auto relative z-10">
          <defs>
            {Object.entries(edgeColors).map(([type, color]) => (
              <marker
                key={type}
                id={`arrow-${type}`}
                viewBox="0 0 10 10"
                refX="10"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill={color} opacity="0.6" />
              </marker>
            ))}
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Edges */}
          {edges.map((edge, i) => {
            const src = nodes.find((n) => n.id === edge.source)!;
            const tgt = nodes.find((n) => n.id === edge.target)!;
            const showLabel = edge.type !== "information";
            return (
              <g key={i}>
                <line
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={edgeColors[edge.type]}
                  strokeWidth="1.5"
                  strokeOpacity="0.4"
                  markerEnd={`url(#arrow-${edge.type})`}
                  strokeDasharray="4 3"
                />
                {showLabel && (
                  <text
                    x={(src.x + tgt.x) / 2}
                    y={(src.y + tgt.y) / 2 - 8}
                    textAnchor="middle"
                    fontSize="8"
                    fill="hsl(215, 15%, 55%)"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {formatLabel(edge.label)}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => (
            <g key={node.id} filter="url(#glow)">
              <circle
                cx={node.x}
                cy={node.y}
                r="20"
                fill="hsl(220, 18%, 10%)"
                stroke={typeColors[node.type]}
                strokeWidth="1.5"
                strokeOpacity="0.6"
              />
              <circle
                cx={node.x}
                cy={node.y}
                r="4"
                fill={typeColors[node.type]}
                opacity="0.8"
              />
              <text
                x={node.x}
                y={node.y + 32}
                textAnchor="middle"
                fontSize="9"
                fill="hsl(210, 20%, 85%)"
                fontFamily="Inter, sans-serif"
                fontWeight="500"
              >
                {node.label}
              </text>
            </g>
          ))}
        </svg>
        {!nodes.length && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
            Submit an intent to render the graph.
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default SupplyGraph;
