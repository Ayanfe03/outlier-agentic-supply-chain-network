import { useEffect, useState } from "react";
import StatusBar from "@/components/StatusBar";
import AgentRegistry from "@/components/AgentRegistry";
import { apiService } from "@/services/api";
import type { AgentFact } from "@/types/protocol";
import { Search } from "lucide-react";

const RegistryPage = () => {
  const [agents, setAgents] = useState<AgentFact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    apiService
      .getAgents()
      .then(setAgents)
      .catch((e) => setError(e.message || "Failed to load agents"));
  }, []);

  const filteredAgents = agents.filter((agent) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const cap = JSON.stringify(agent.capabilities || {}).toLowerCase();
    const pol = JSON.stringify(agent.policies || {}).toLowerCase();
    const jur = JSON.stringify(agent.jurisdiction || {}).toLowerCase();
    return (
      agent.agent_id.toLowerCase().includes(q) ||
      agent.role.toLowerCase().includes(q) ||
      cap.includes(q) ||
      pol.includes(q) ||
      jur.includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-background">
      <StatusBar onlineCount={agents.length} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <section className="mb-8">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-3xl font-semibold text-foreground">Agent Registry</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Discover registered agents, capabilities, policies, and jurisdictions.
              </p>
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search agents..."
                className="w-full bg-card border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
          </div>
        </section>

        {error ? (
          <div className="text-sm text-destructive">Failed to load agents: {error}</div>
        ) : (
          <AgentRegistry agents={filteredAgents} />
        )}
      </main>
    </div>
  );
};

export default RegistryPage;
