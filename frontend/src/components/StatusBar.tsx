import { Activity, Server } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

interface StatusBarProps {
  onlineCount: number;
}

const StatusBar = ({ onlineCount }: StatusBarProps) => {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/50 backdrop-blur-md"
    >
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse-glow" />
          <span className="text-sm font-mono text-foreground tracking-tight font-semibold">
            OUTLIER
          </span>
        </div>
        <span className="text-xs text-muted-foreground font-mono hidden sm:inline">
          Agentic Protocol
        </span>
      </div>

      <div className="flex items-center gap-4">
        <Link
          to="/registry"
          className="inline-flex items-center gap-2 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <Server className="w-3.5 h-3.5 text-muted-foreground" />
          <span>Registry</span>
        </Link>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Activity className="w-3.5 h-3.5 text-accent" />
          <span className="text-xs font-mono">{onlineCount} Online</span>
        </div>
      </div>
    </motion.header>
  );
};

export default StatusBar;
