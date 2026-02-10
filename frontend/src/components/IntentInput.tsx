import { motion } from "framer-motion";
import { Send, Zap } from "lucide-react";
import { useState } from "react";

interface IntentInputProps {
  onSubmit: (intent: string) => void;
  isProcessing: boolean;
}

const IntentInput = ({ onSubmit, isProcessing }: IntentInputProps) => {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !isProcessing) {
      onSubmit(value.trim());
    }
  };

  const suggestions = [
    "Find compliant engine suppliers in Nigeria",
    "Route 500 units of tires from Abuja to Port Harcourt",
    "Find compliant lithium battery suppliers in EU",
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="w-full max-w-3xl mx-auto"
    >
      <div className="text-center mb-8">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 mb-6"
        >
          <Zap className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-mono text-primary tracking-wider uppercase">
            Outlier Agentic Protocol (OAP) v1.0
          </span>
        </motion.div>
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-3">
          <span className="text-gradient-primary">Outlier</span>{" "}
          <span className="text-foreground">Agentic Protocol</span>
        </h1>
        <p className="text-muted-foreground text-lg max-w-xl mx-auto">
          Describe a procurement intent and watch agents discover, route, and verify compliance in real time.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/30 to-accent/30 rounded-xl blur-sm opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
        <div className="relative flex items-center bg-card border border-border rounded-xl overflow-hidden glow-border">
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Describe a supply intent (part, quantity, origin, destination)..."
            disabled={isProcessing}
            className="flex-1 bg-transparent px-6 py-5 text-foreground placeholder:text-muted-foreground focus:outline-none text-base"
          />
          <button
            type="submit"
            disabled={!value.trim() || isProcessing}
            className="mr-3 p-3 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>

      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {suggestions.map((s, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 + i * 0.1 }}
            onClick={() => setValue(s)}
            className="text-xs px-3 py-1.5 rounded-full border border-border bg-secondary/50 text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all duration-200"
          >
            {s}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
};

export default IntentInput;
