"use client";

import {
  Line,
  LineChart,
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
}

export function TrendChart({ data, height = 200 }: TrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12 }}
          tickFormatter={(value: string) => formatDateShort(value)}
        />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
        <Tooltip
          labelFormatter={(value: string) => formatDateShort(value)}
          contentStyle={{ fontSize: 12 }}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#2563eb"
          strokeWidth={2}
          dot={{ fill: "#2563eb", r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
