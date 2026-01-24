import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

type FatigueTrendProps = {
  trials: Array<{
    id: number;
    name: string;
    medianFrequency?: number | null; // f_med in Hz (computed from PSD, not in base Trial type)
  }>;
  height?: number;
};

export default function FatigueTrend({ trials, height = 80 }: FatigueTrendProps) {
  // Get last 5 trials with median frequency data
  const validTrials = trials
    .filter((t) => t.medianFrequency != null)
    .slice(-5);

  if (validTrials.length === 0) {
    return (
      <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-clinical-text">Fatigue Trend</h3>
          <span className="text-xs text-clinical-text-dim">No data</span>
        </div>
        <div className="h-20 flex items-center justify-center text-clinical-text-dim text-xs">
          Capture trials with PSD analysis to view trend
        </div>
      </div>
    );
  }

  const chartData = validTrials.map((trial, idx) => ({
    trial: idx + 1,
    name: trial.name,
    fmed: trial.medianFrequency!,
  }));

  // Calculate trend direction
  const firstFmed = chartData[0]?.fmed;
  const lastFmed = chartData[chartData.length - 1]?.fmed;
  const trendDirection = firstFmed && lastFmed
    ? lastFmed < firstFmed ? 'down' : lastFmed > firstFmed ? 'up' : 'stable'
    : 'stable';

  const trendPercent = firstFmed && lastFmed
    ? ((lastFmed - firstFmed) / firstFmed) * 100
    : 0;

  const TrendIcon = trendDirection === 'down' ? TrendingDown 
    : trendDirection === 'up' ? TrendingUp 
    : Minus;

  const trendColor = trendDirection === 'down' 
    ? 'text-clinical-warning' 
    : trendDirection === 'up' 
    ? 'text-clinical-success' 
    : 'text-clinical-text-dim';

  return (
    <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-clinical-text">Fatigue Trend</h3>
        <div className="flex items-center gap-2">
          <TrendIcon className={`w-4 h-4 ${trendColor}`} />
          <span className={`text-xs font-medium ${trendColor}`}>
            {trendPercent !== 0 
              ? `${trendPercent > 0 ? '+' : ''}${trendPercent.toFixed(1)}%`
              : 'Stable'}
          </span>
        </div>
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <XAxis
              dataKey="trial"
              type="number"
              domain={['dataMin', 'dataMax']}
              tick={{ fontSize: 10 }}
              stroke="#475569"
            />
            <YAxis
              domain={['dataMin - 5', 'dataMax + 5']}
              tick={{ fontSize: 10 }}
              stroke="#475569"
              label={{ value: 'f_med (Hz)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: 10 } }}
            />
            <Tooltip
              formatter={(value: number) => [`${value.toFixed(1)} Hz`, 'Median Frequency']}
              labelFormatter={(label, payload) => {
                const data = payload?.[0]?.payload;
                return data?.name || `Trial ${label}`;
              }}
            />
            <Line
              type="monotone"
              dataKey="fmed"
              stroke={trendDirection === 'down' ? '#dc2626' : trendDirection === 'up' ? '#16a34a' : '#475569'}
              strokeWidth={2}
              dot={{ r: 3, fill: trendDirection === 'down' ? '#dc2626' : trendDirection === 'up' ? '#16a34a' : '#475569' }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between mt-2 text-xs text-clinical-text-dim">
        <div>
          Last {validTrials.length} trial{validTrials.length !== 1 ? 's' : ''}
        </div>
        {firstFmed && lastFmed && (
          <div>
            {firstFmed.toFixed(1)} Hz → {lastFmed.toFixed(1)} Hz
          </div>
        )}
      </div>
    </div>
  );
}
