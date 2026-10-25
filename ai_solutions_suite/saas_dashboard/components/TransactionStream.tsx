"use client";

import React, { useState } from "react";

export interface TransactionEvent {
  id: string;
  client: string;
  endpoint: string;
  latencyMs: number;
  statusCode: number;
  statusText: string;
  timestamp: string;
}

interface TransactionStreamProps {
  initialTransactions?: TransactionEvent[];
  onExport?: (format: "csv" | "json") => void;
}

export const TransactionStream: React.FC<TransactionStreamProps> = ({
  initialTransactions,
  onExport,
}) => {
  const [filter, setFilter] = useState<"all" | "success" | "latency">("all");
  const [searchTerm, setSearchTerm] = useState("");

  const defaultEvents: TransactionEvent[] = [
    {
      id: "#TX-948101",
      client: "Acme FinTech Corp",
      endpoint: "POST /api/v1/auth/jwt",
      latencyMs: 24,
      statusCode: 200,
      statusText: "OK",
      timestamp: "2026-10-23T10:50:00Z",
    },
    {
      id: "#TX-948102",
      client: "Nexus Health Systems",
      endpoint: "GET /api/v1/rag/query",
      latencyMs: 38,
      statusCode: 200,
      statusText: "OK",
      timestamp: "2026-10-23T10:50:02Z",
    },
    {
      id: "#TX-948103",
      client: "Apex Logistics Global",
      endpoint: "POST /api/v1/sql/execute",
      latencyMs: 18,
      statusCode: 200,
      statusText: "OK",
      timestamp: "2026-10-23T10:50:05Z",
    },
    {
      id: "#TX-948104",
      client: "Solaria AI Labs",
      endpoint: "GET /api/v1/telemetry/stream",
      latencyMs: 46,
      statusCode: 200,
      statusText: "OK",
      timestamp: "2026-10-23T10:50:08Z",
    },
    {
      id: "#TX-948105",
      client: "Vanguard Security",
      endpoint: "POST /api/v1/scraper/sync",
      latencyMs: 22,
      statusCode: 200,
      statusText: "OK",
      timestamp: "2026-10-23T10:50:11Z",
    },
  ];

  const transactions = initialTransactions || defaultEvents;

  const filtered = transactions.filter((tx) => {
    const matchesSearch =
      !searchTerm ||
      tx.client.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.endpoint.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.id.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (filter === "latency") {
      return tx.latencyMs > 30;
    }
    if (filter === "success") {
      return tx.statusCode === 200;
    }
    return true;
  });

  return (
    <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-5 flex flex-col h-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-3">
        <div>
          <h3 className="text-sm font-bold text-zinc-100">
            Real-Time Enterprise Transaction Stream
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Live microservice RPC and API events
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search stream..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs px-2.5 py-1 rounded-md focus:outline-none focus:border-blue-500 w-32 sm:w-40"
          />
          <div className="flex bg-zinc-950 border border-zinc-800 rounded-md p-0.5 text-xs">
            <button
              onClick={() => setFilter("all")}
              className={`px-2 py-0.5 rounded font-medium ${
                filter === "all" ? "bg-zinc-800 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter("success")}
              className={`px-2 py-0.5 rounded font-medium ${
                filter === "success" ? "bg-zinc-800 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              200 OK
            </button>
            <button
              onClick={() => setFilter("latency")}
              className={`px-2 py-0.5 rounded font-medium ${
                filter === "latency" ? "bg-zinc-800 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              &gt;30ms
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto border border-zinc-800/80 rounded-lg flex-1">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-[11px]">
              <th className="py-2.5 px-3 font-semibold">TX ID</th>
              <th className="py-2.5 px-3 font-semibold">Client Org</th>
              <th className="py-2.5 px-3 font-semibold">Endpoint</th>
              <th className="py-2.5 px-3 font-semibold">Latency</th>
              <th className="py-2.5 px-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {filtered.map((tx) => (
              <tr key={tx.id} className="hover:bg-zinc-800/30 transition-colors">
                <td className="py-2.5 px-3 font-mono text-zinc-300">
                  <code>{tx.id}</code>
                </td>
                <td className="py-2.5 px-3 font-semibold text-zinc-200">{tx.client}</td>
                <td className="py-2.5 px-3 font-mono text-zinc-400">{tx.endpoint}</td>
                <td className="py-2.5 px-3 font-mono text-zinc-300">{tx.latencyMs}ms</td>
                <td className="py-2.5 px-3">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      tx.latencyMs > 30
                        ? "bg-amber-500/10 text-amber-400"
                        : "bg-emerald-500/10 text-emerald-400"
                    }`}
                  >
                    {tx.statusCode} {tx.statusText}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-zinc-500">
                  No matching transactions found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
