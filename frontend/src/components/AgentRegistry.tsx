import { motion } from "framer-motion";
import { Bot, Truck, Shield, ShoppingCart, Wifi, WifiOff } from "lucide-react";
import type { AgentFact } from "@/types/protocol";

const roleConfig: Record<AgentFact["role"], { icon: typeof Bot; gradient: string; label: string }> = {
  buyer: { icon: ShoppingCart, gradient: "from-primary/20 to-primary/5", label: "Buyer" },
  supplier: { icon: Bot, gradient: "from-accent/20 to-accent/5", label: "Supplier" },
  logistics: { icon: Truck, gradient: "from-warning/20 to-warning/5", label: "Logistics" },
  compliance: { icon: Shield, gradient: "from-destructive/20 to-destructive/5", label: "Compliance" },
};

const roleColor: Record<AgentFact["role"], string> = {
  buyer: "text-primary border-primary/30",
  supplier: "text-accent border-accent/30",
  logistics: "text-warning border-warning/30",
  compliance: "text-destructive border-destructive/30",
};

interface AgentCardProps {
  agent: AgentFact;
  index: number;
}

const AgentCard = ({ agent, index }: AgentCardProps) => {
  const config = roleConfig[agent.role];
  const color = roleColor[agent.role];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      className="group relative"
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${config.gradient} rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
      <div className="relative bg-card border border-border rounded-xl p-5 hover:border-primary/20 transition-all duration-300 glow-border">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-2.5 rounded-lg bg-gradient-to-br ${config.gradient} border ${color}`}>
            <Icon className={`w-4 h-4 ${color.split(" ")[0]}`} />
          </div>
          <div className="flex items-center gap-1.5">
            {agent.status === "online" ? (
              <Wifi className="w-3 h-3 text-accent" />
            ) : (
              <WifiOff className="w-3 h-3 text-muted-foreground" />
            )}
            <span
              className={`text-[10px] font-mono uppercase tracking-wider ${
                agent.status === "online" ? "text-accent" : "text-muted-foreground"
              }`}
            >
              {agent.status}
            </span>
          </div>
        </div>

        <h3 className="font-semibold text-foreground mb-1">{agent.name}</h3>
        <span className={`inline-block text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border ${color} mb-3`}>
          {config.label}
        </span>

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            <span className="text-foreground/60">Jurisdiction:</span> {agent.jurisdiction}
          </p>
          <div className="flex flex-wrap gap-1">
            {agent.capabilities.slice(0, 3).map((cap) => (
              <span
                key={cap}
                className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground font-mono"
              >
                {cap}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

interface AgentRegistryProps {
  agents: AgentFact[];
}

const AgentRegistry = ({ agents }: AgentRegistryProps) => {
  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-lg font-semibold text-foreground">Agent Registry</h2>
        <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
          {agents.length} agents
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map((agent, i) => (
          <AgentCard key={agent.id} agent={agent} index={i} />
        ))}
      </div>
    </div>
  );
};

export default AgentRegistry;
