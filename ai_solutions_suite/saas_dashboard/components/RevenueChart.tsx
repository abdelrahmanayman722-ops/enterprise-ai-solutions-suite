import React from "react";

export interface MonthlyRevenueData {
  month: string;
  actualMrr: number;
  projectedMrr?: number;
}

interface RevenueChartProps {
  data?: MonthlyRevenueData[];
}

export const RevenueChart: React.FC<RevenueChartProps> = ({ data }) => {
  return (
    <div className="bg-zinc-900/80 border border-zinc-800/80 rounded-xl p-6 mb-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
        <div>
          <h3 className="text-base font-bold text-zinc-100 tracking-tight">
            Executive MRR & ARR Financial Trajectory
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            12-Month Invoiced Revenue Performance vs Predictive Run-Rate
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
            <span>Invoiced MRR</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
            <span>Projected Run-Rate</span>
          </div>
        </div>
      </div>

      <div className="w-full h-52">
        <svg viewBox="0 0 1000 220" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="mrrGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1="50" y1="30" x2="950" y2="30" stroke="#1f1f23" strokeWidth="1" />
          <line x1="50" y1="80" x2="950" y2="80" stroke="#1f1f23" strokeWidth="1" />
          <line x1="50" y1="130" x2="950" y2="130" stroke="#1f1f23" strokeWidth="1" />
          <line x1="50" y1="180" x2="950" y2="180" stroke="#1f1f23" strokeWidth="1" />

          {/* Y Axis ticks */}
          <text x="15" y="35" fill="#52525b" fontSize="10" fontFamily="monospace">$50k</text>
          <text x="15" y="85" fill="#52525b" fontSize="10" fontFamily="monospace">$35k</text>
          <text x="15" y="135" fill="#52525b" fontSize="10" fontFamily="monospace">$20k</text>
          <text x="15" y="185" fill="#52525b" fontSize="10" fontFamily="monospace">$5k</text>

          {/* X Axis month labels */}
          <text x="75" y="205" fill="#71717a" fontSize="11">Nov</text>
          <text x="155" y="205" fill="#71717a" fontSize="11">Dec</text>
          <text x="235" y="205" fill="#71717a" fontSize="11">Jan</text>
          <text x="315" y="205" fill="#71717a" fontSize="11">Feb</text>
          <text x="395" y="205" fill="#71717a" fontSize="11">Mar</text>
          <text x="475" y="205" fill="#71717a" fontSize="11">Apr</text>
          <text x="555" y="205" fill="#71717a" fontSize="11">May</text>
          <text x="635" y="205" fill="#71717a" fontSize="11">Jun</text>
          <text x="715" y="205" fill="#71717a" fontSize="11">Jul</text>
          <text x="795" y="205" fill="#71717a" fontSize="11">Aug</text>
          <text x="875" y="205" fill="#71717a" fontSize="11">Sep</text>
          <text x="945" y="205" fill="#71717a" fontSize="11">Oct</text>

          {/* Area under curve */}
          <path d="M 80,170 Q 240,150 400,120 T 720,80 L 950,45 L 950,180 L 80,180 Z" fill="url(#mrrGradient)" />

          {/* Actual invoiced path */}
          <path d="M 80,170 Q 240,150 400,120 T 720,80" fill="none" stroke="#3b82f6" strokeWidth="3" strokeLinecap="round" />

          {/* Projected trajectory */}
          <path d="M 720,80 Q 830,60 950,45" fill="none" stroke="#10b981" strokeWidth="2.5" strokeDasharray="6,4" strokeLinecap="round" />

          {/* Key milestone circles */}
          <circle cx="80" cy="170" r="4" fill="#3b82f6" />
          <circle cx="240" cy="150" r="4" fill="#3b82f6" />
          <circle cx="400" cy="120" r="4" fill="#3b82f6" />
          <circle cx="560" cy="100" r="4" fill="#3b82f6" />
          <circle cx="720" cy="80" r="5" fill="#3b82f6" stroke="#ffffff" strokeWidth="2" />
          <circle cx="950" cy="45" r="5" fill="#10b981" stroke="#ffffff" strokeWidth="2" />
        </svg>
      </div>
    </div>
  );
};
