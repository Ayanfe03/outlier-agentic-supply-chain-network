import { useEffect, useRef, useState } from "react";
import StatusBar from "@/components/StatusBar";
import IntentInput from "@/components/IntentInput";
import CoordinationFlow from "@/components/CoordinationFlow";
import SupplyGraph from "@/components/SupplyGraph";
import AgentInteraction from "@/components/AgentInteraction";
import LiveMessageStream from "@/components/LiveMessageStream";
import { apiService, getBuyerWsUrl } from "@/services/api";
import type { CoordinationReport, AgentFact } from "@/types/protocol";

const Index = () => {
  const [agents, setAgents] = useState<AgentFact[]>([]);
  const [report, setReport] = useState<CoordinationReport | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const liveRef = useRef(false);
  const [eventLog, setEventLog] = useState<
    { id: string; type: string; actor: string; action: string; message: string; ts: string }[]
  >([]);

  useEffect(() => {
    apiService.getAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  const handleSubmitIntent = async (intent: string) => {
    setIsProcessing(true);
    liveRef.current = false;
    setEventLog([]);
    setReport({ id: "", intent, status: "running", steps: [], createdAt: new Date().toISOString() });

    try {
      if (wsRef.current) {
        wsRef.current.close();
      }
      const ws = new WebSocket(getBuyerWsUrl());
      wsRef.current = ws;
      const wsReady = new Promise<void>((resolve) => {
        ws.onopen = () => {
          ws.send("subscribe");
          resolve();
        };
      });
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "step" && data.step) {
            liveRef.current = true;
            setEventLog((prev) => [
              ...prev,
              {
                id: `log-${Date.now()}-${prev.length}`,
                type: "step",
                actor: data.step.agentName || data.step.agentId || "agent",
                action: data.step.action || "action",
                message: data.step.result || "",
                ts: data.step.timestamp || new Date().toISOString(),
              },
            ]);
            setReport((prev) => {
              const next = prev || {
                id: `live-${Date.now()}`,
                intent,
                status: "running",
                steps: [],
                createdAt: new Date().toISOString(),
              };
              const stepId = data.step.id || `live-step-${next.steps.length + 1}`;
              return {
                ...next,
                steps: [
                  ...next.steps,
                  {
                    id: stepId,
                    agentId: data.step.agentId,
                    agentName: data.step.agentName,
                    agentRole: data.step.agentRole,
                    action: data.step.action,
                    result: data.step.result,
                    status: "completed",
                    timestamp: data.step.timestamp || new Date().toISOString(),
                  },
                ],
              };
            });
          }
          if (data.type === "status") {
            setEventLog((prev) => [
              ...prev,
              {
                id: `log-${Date.now()}-${prev.length}`,
                type: "status",
                actor: "system",
                action: data.status || "status",
                message: data.intent || "",
                ts: new Date().toISOString(),
              },
            ]);
            setReport((prev) => (prev ? { ...prev, status: data.status } : prev));
          }
        } catch {
          return;
        }
      };

      await Promise.race([
        wsReady,
        new Promise((resolve) => setTimeout(resolve, 800)),
      ]);

      const fullReport = await apiService.submitIntent(intent);
      const steps = fullReport.steps;

      if (!liveRef.current) {
        for (let i = 0; i < steps.length; i++) {
          await new Promise((r) => setTimeout(r, 600));
          setReport((prev) =>
            prev
              ? {
                  ...prev,
                  steps: steps.slice(0, i + 1).map((s) => ({
                    ...s,
                    status: "completed",
                  })),
                }
              : null
          );
        }
      }

      if (!liveRef.current) {
        setEventLog(
          steps.map((s, idx) => ({
            id: `log-final-${idx + 1}`,
            type: "step",
            actor: s.agentName || s.agentId || "agent",
            action: s.action || "action",
            message: s.result || "",
            ts: s.timestamp || new Date().toISOString(),
          }))
        );
      }

      setReport({ ...fullReport, intent });
    } catch (e: any) {
      setReport({
        id: `error-${Date.now()}`,
        intent,
        status: "failed",
        steps: [],
        summary: e?.message || "Unable to process intent",
        createdAt: new Date().toISOString(),
      });
    } finally {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <StatusBar onlineCount={agents.length} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Hero / Intent Input */}
        <section className="pt-16 pb-12">
          <IntentInput onSubmit={handleSubmitIntent} isProcessing={isProcessing} />
        </section>

        {/* Live Interaction + Coordination + Graph */}
        <section className="pb-4">
          <AgentInteraction isRunning={isProcessing || report?.status === "running"} />
        </section>
        <section className="pb-16 grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <CoordinationFlow report={report} />
          </div>
          <div className="space-y-6">
            <div className="mt-12">
              <LiveMessageStream events={eventLog} />
            </div>
            <SupplyGraph report={report} />
          </div>
        </section>
      </main>
    </div>
  );
};

export default Index;
