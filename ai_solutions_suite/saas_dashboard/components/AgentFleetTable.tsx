import React from "react";

export interface AgentNode {
  id: string;
  name: string;
  model: string;
  role: string;
  throughputRps: number;
  latencyMs: number;
  status: "active" | "ingesting" | "idle" | "error";
}

interface AgentFleetTableProps {
  agents?: AgentNode[];
}

export const AgentFleetTable: React.FC<AgentFleetTableProps> = ({ agents }) => {
  const defaultAgents: AgentNode[] = [
    {
      id: "agent_rag_01",
      name: "RAG-Worker-Alpha",
      model: "Claude 3.5 Sonnet",
      role: "Knowledge Synthesis",
      throughputRps: 48,
      latencyMs: 24,
      status: "active",
    },
    {
      id: "agent_sql_02",
      name: "SafeSQL-Barrier-01",
      model: "AST/Regex Guard",
      role: "Read-Only Security",
      throughputRps: 120,
      latencyMs: 4,
      status: "active",
    },
    {
      id: "agent_scraper_03",
      name: "Scraper-Crawler-09",
      model: "Client Hints / Jitter",
      role: "Multi-Domain Mining",
      throughputRps: 85,
      latencyMs: 18,
      status: "ingesting",
    },
    {
      id: "agent_hunter_04",
      name: "Contract-Hunter-Bot",
      model: "HN / WWR Ingest",
      role: "High-Ticket Pipeline",
      throughputRps: 14,
      latencyMs: 42,
      status: "active",
    },
    {
      id: "agent_sentinel_05",
      name: "Anomaly-Sentinel",
      model: "Real-Time Watchdog",
      role: "Zero-Day Audit",
      throughputRps: 310,
      latencyMs: 2,
      status: "active",
    },
  ];

  const fleet = agents || defaultAgents;

  const getStatusBadge = (status: AgentNode["status"]) => {
    switch (status) {
      case "active":
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 uppercase tracking-wide">
            Active
          </span>
        );
      case "ingesting":
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 uppercase tracking-wide">
            Ingesting
          </span>
        );
      case "idle":
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-zinc-500/10 text-zinc-400 uppercase tracking-wide">
            Idle
          </span>
        );
      case "error":
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 uppercase tracking-wide">
            Fault
          </span>
        );
    }
  };

  return (
    <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-5 flex flex-col h-full">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-sm font-bold text-zinc-100">
            Active AI Agent Fleet Monitor
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Autonomous nodes operating in current cluster
          </p>
        </div>
        <span className="text-xs font-semibold px-2 py-1 rounded-md bg-emerald-500/10 text-emerald-400">
          {fleet.length} Nodes Online
        </span>
      </div>

      <div className="overflow-x-auto border border-zinc-800/80 rounded-lg flex-1">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-[11px]">
              <th className="py-2.5 px-3 font-semibold">Agent Node</th>
              <th className="py-2.5 px-3 font-semibold">Role</th>
              <th className="py-2.5 px-3 font-semibold">RPS</th>
              <th className="py-2.5 px-3 font-semibold">Latency</th>
              <th className="py-2.5 px-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {fleet.map((agent) => (
              <tr key={agent.id} className="hover:bg-zinc-800/30 transition-colors">
                <td className="py-2.5 px-3">
                  <div className="font-semibold text-zinc-200">{agent.name}</div>
                  <div className="text-[11px] text-zinc-500">{agent.model}</div>
                </td>
                <td className="py-2.5 px-3 text-zinc-300">{agent.role}</td>
                <td className="py-2.5 px-3 font-mono text-zinc-300">{agent.throughputRps} rps</td>
                <td className="py-2.5 px-3 font-mono text-zinc-300">{agent.latencyMs}ms</td>
                <td className="py-2.5 px-3">{getStatusBadge(agent.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
