import React from "react";

export interface TelemetryMetrics {
  arr: number;
  mrr: number;
  arrGrowthYoY: string;
  throughputRps: number;
  p95LatencyMs: number;
  activeAgents: number;
  totalAgents: number;
  errorRate: number;
  cacheHitRatio: number;
  clusterNodes: number;
}

interface TelemetryGridProps {
  metrics?: Partial<TelemetryMetrics>;
}

export const TelemetryGrid: React.FC<TelemetryGridProps> = ({ metrics }) => {
  const data: TelemetryMetrics = {
    arr: 482500,
    mrr: 40208,
    arrGrowthYoY: "+24.8%",
    throughputRps: 4820,
    p95LatencyMs: 32,
    activeAgents: 18,
    totalAgents: 18,
    errorRate: 0.02,
    cacheHitRatio: 96.4,
    clusterNodes: 12,
    ...metrics,
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* ARR Card */}
      <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-5 hover:border-zinc-700 transition-colors">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Annual Recurring Revenue
          </span>
          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
            {data.arrGrowthYoY} YoY
          </span>
        </div>
        <div className="font-mono text-2xl font-bold text-zinc-100">
          ${data.arr.toLocaleString()}
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          MRR Run Rate: <span className="text-zinc-300 font-medium">${data.mrr.toLocaleString()}/mo</span>
        </div>
      </div>

      {/* Throughput Card */}
      <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-5 hover:border-zinc-700 transition-colors">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            API Throughput
          </span>
          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400">
            {data.p95LatencyMs}ms p95
          </span>
        </div>
        <div className="font-mono text-2xl font-bold text-zinc-100">
          {data.throughputRps.toLocaleString()} req/s
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          Global Peak Load: 7,400 req/s
        </div>
      </div>

      {/* Fleet Health Card */}
      <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-5 hover:border-zinc-700 transition-colors">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            AI Agent Fleet
          </span>
          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
            {data.activeAgents}/{data.totalAgents} Active
          </span>
        </div>
        <div className="font-mono text-2xl font-bold text-zinc-100">
          {((data.activeAgents / (data.totalAgents || 1)) * 100).toFixed(1)}%
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          Cluster Error Rate: {data.errorRate}%
        </div>
      </div>

      {/* Cache Ratio Card */}
      <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-5 hover:border-zinc-700 transition-colors">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Redis Cache Hit
          </span>
          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
            Optimized
          </span>
        </div>
        <div className="font-mono text-2xl font-bold text-zinc-100">
          {data.cacheHitRatio.toFixed(1)}%
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          {data.clusterNodes} Sharded Nodes (1.4 TB hot)
        </div>
      </div>
    </div>
  );
};
