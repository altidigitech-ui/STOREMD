"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatDateShort } from "@/lib/utils";

interface TrendPoint {
  date: string;
  score: number;
}

interface TrendChartProps {
  data: TrendPoint[];
  height?: number;
  trend?: "up" | "down" | "stable";
}

function trendColor(trend: "up" | "down" | "stable" | undefined) {
  if (trend === "up") return "#16a34a";
  if (trend === "down") return "#dc2626";
  return "#2563eb";
}

interface TooltipPayload {
  payload: TrendPoint;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
}) {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  if (!entry) return null;
  const { date, score } = entry.payload;
  return (
    <div className="rounded-md border border-gray-200 bg-white px-3 py-2 shadow-md">
      <p className="text-xs text-gray-500">{formatDateShort(date)}</p>
      <p className="text-sm font-semibold text-gray-900">{score} / 100</p>
    </div>
  );
}

export function TrendChart({ data, height = 220, trend }: TrendChartProps) {
  const color = trendColor(trend);
  const gradientId = `trendGradient-${trend ?? "default"}`;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          vertical={false}
          stroke="#f3f4f6"
          strokeDasharray="3 3"
        />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickFormatter={(value: string) => formatDateShort(value)}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
          width={32}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="score"
          stroke={color}
          strokeWidth={2.5}
          fill={`url(#${gradientId})`}
          activeDot={{
            r: 5,
            fill: color,
            stroke: "#fff",
            strokeWidth: 2,
          }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
