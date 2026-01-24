import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip } from 'recharts';
import { api } from '@api/client';
import type { PSDResponse } from '@api/types';

type FrequencyDomainChartProps = {
  channel: number;
  startISO: string;
  endISO: string;
  height?: number;
};

export default function FrequencyDomainChart({
  channel,
  startISO,
  endISO,
  height = 300,
}: FrequencyDomainChartProps) {
  const [psdData, setPsdData] = useState<PSDResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    api.analyticsPsd(channel, startISO, endISO, {
      method: 'welch',
      nperseg: 512,
      noverlap: 256,
      scaling: 'density',
    })
      .then((data) => {
        if (active) {
          setPsdData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || 'Failed to compute PSD');
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [channel, startISO, endISO]);

  const chartData = psdData
    ? psdData.freqs.map((freq, idx) => ({
        frequency: freq,
        power: psdData.psd[idx],
      }))
    : [];

  // Filter to EMG-relevant frequency range (typically 10-500 Hz)
  const filteredData = chartData.filter((d) => d.frequency >= 10 && d.frequency <= 500);

  if (loading) {
    return (
      <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm" style={{ height }}>
        <div className="flex items-center justify-center h-full">
          <div className="text-clinical-text-dim">Computing PSD...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm" style={{ height }}>
        <div className="flex items-center justify-center h-full text-clinical-error">
          Error: {error}
        </div>
      </div>
    );
  }

  if (!psdData || filteredData.length === 0) {
    return (
      <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm" style={{ height }}>
        <div className="flex items-center justify-center h-full text-clinical-text-dim">
          No data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-clinical-text">Frequency Domain (Welch PSD)</h3>
          <p className="text-xs text-clinical-text-dim">Power vs Frequency</p>
        </div>
        {psdData.mdf != null && (
          <div className="text-right">
            <div className="text-xs text-clinical-text-dim">Median Frequency</div>
            <div className="text-lg font-semibold text-clinical-accent">
              {psdData.mdf.toFixed(1)} Hz
            </div>
          </div>
        )}
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="frequency"
              type="number"
              domain={[10, 500]}
              label={{ value: 'Frequency (Hz)', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle' } }}
              stroke="#475569"
              fontSize={11}
            />
            <YAxis
              scale="log"
              domain={['auto', 'auto']}
              label={{ value: 'Power (µV²/Hz)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
              stroke="#475569"
              fontSize={11}
              tickFormatter={(value) => value.toExponential(1)}
            />
            <Tooltip
              formatter={(value: number) => [`${value.toExponential(2)} µV²/Hz`, 'Power']}
              labelFormatter={(label) => `Frequency: ${label.toFixed(1)} Hz`}
            />
            <Line
              type="monotone"
              dataKey="power"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            {/* Median Frequency Drop-line */}
            {psdData.mdf != null && (
              <ReferenceLine
                x={psdData.mdf}
                stroke="#dc2626"
                strokeWidth={2}
                strokeDasharray="5 5"
                label={{
                  value: `f_med = ${psdData.mdf.toFixed(1)} Hz`,
                  position: 'top',
                  fill: '#dc2626',
                  fontSize: 11,
                  fontWeight: 'bold',
                }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-4 mt-2 text-xs text-clinical-text-dim">
        <div className="flex items-center gap-2">
          <div className="w-3 h-1 bg-red-600 border-dashed border-t-2"></div>
          <span>Median Frequency (f_med)</span>
        </div>
        {psdData.mnf != null && (
          <div>
            Mean Frequency: {psdData.mnf.toFixed(1)} Hz
          </div>
        )}
      </div>
    </div>
  );
}
