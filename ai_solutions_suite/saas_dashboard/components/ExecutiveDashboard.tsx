"use client";

import React, { useState } from "react";
import { TelemetryGrid, TelemetryMetrics } from "./TelemetryGrid";
import { RevenueChart } from "./RevenueChart";
import { AgentFleetTable } from "./AgentFleetTable";
import { TransactionStream } from "./TransactionStream";

export interface ExecutiveDashboardProps {
  initialMetrics?: Partial<TelemetryMetrics>;
}

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({
  initialMetrics,
}) => {
  const [isLive, setIsLive] = useState(true);

  const handleExport = (format: "csv" | "json") => {
    // Client-side export helper
    console.log(`[Export] Triggered ${format.toUpperCase()} export`);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 md:p-8 font-sans antialiased">
      {/* Header Bar */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-zinc-800/80 mb-6 gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold tracking-tight text-zinc-100">
            Apex Executive Operations Command
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Enterprise SaaS Intelligence • Multi-Agent Autonomous Fleet • Next.js 15 & Node.js Engine
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full border ${
              isLive
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-zinc-800 text-zinc-400 border-zinc-700"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isLive ? "bg-emerald-500 animate-pulse" : "bg-zinc-500"
              }`}
            />
            {isLive ? "Cluster Live (99.99%)" : "Telemetry Paused"}
          </span>

          <button
            onClick={() => setIsLive(!isLive)}
            className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-200 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          >
            {isLive ? "Pause Stream" : "Resume Stream"}
          </button>

          <button
            onClick={() => handleExport("csv")}
            className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-200 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-200 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          >
            Export JSON
          </button>
        </div>
      </header>

      {/* Main Command Center Layout */}
      <main>
        {/* Row 1: KPI Metrics Grid */}
        <TelemetryGrid metrics={initialMetrics} />

        {/* Row 2: Revenue Trend Visualizer */}
        <RevenueChart />

        {/* Row 3: Agent Fleet and Live Transactions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <AgentFleetTable />
          <TransactionStream onExport={handleExport} />
        </div>
      </main>

      {/* Footer */}
      <footer className="pt-6 border-t border-zinc-800/80 flex flex-col sm:flex-row justify-between items-center text-xs text-zinc-500 gap-2">
        <div>
          System Version: <strong className="text-zinc-400">Apex SaaS Suite v2.4.0 (Enterprise Production Build)</strong>
        </div>
        <div>
          Engine Architect: <strong className="text-zinc-400">Eng. Abdelrahman Rashad</strong> • Senior Full-Stack & Solutions Architect
        </div>
      </footer>
    </div>
  );
};

export default ExecutiveDashboard;
