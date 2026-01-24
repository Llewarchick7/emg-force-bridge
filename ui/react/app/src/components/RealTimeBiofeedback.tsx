import { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceArea, ResponsiveContainer, Tooltip } from 'recharts';
import { api } from '@api/client';
import type { EMGSample } from '@api/types';

type RealTimeBiofeedbackProps = {
  channel: number;
  mvcRmsUv: number | null; // MVC in microvolts for normalization
  targetZoneMin?: number; // Target zone min as %MVC (default 20%)
  targetZoneMax?: number; // Target zone max as %MVC (default 80%)
  windowSeconds?: number; // Time window to display (default 10s)
};

export default function RealTimeBiofeedback({
  channel,
  mvcRmsUv,
  targetZoneMin = 20,
  targetZoneMax = 80,
  windowSeconds = 10,
}: RealTimeBiofeedbackProps) {
  const [samples, setSamples] = useState<EMGSample[]>([]);

  useEffect(() => {
    let active = true;
    const interval = setInterval(async () => {
      const end = new Date();
      const start = new Date(end.getTime() - windowSeconds * 1000);
      try {
        const hist = await api.emgHistory(start.toISOString(), end.toISOString(), channel);
        if (active && Array.isArray(hist)) {
          setSamples(hist as EMGSample[]);
        }
      } catch (err) {
        console.error('Failed to fetch EMG history:', err);
      }
    }, 200); // Update every 200ms for smooth real-time display

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [channel, windowSeconds]);

  const chartData = useMemo(() => {
    if (!mvcRmsUv || mvcRmsUv <= 0) {
      // If no MVC, show raw values
      return samples.map((s) => ({
        time: new Date(s.timestamp).getTime(),
        value: s.rms ?? s.envelope ?? 0,
        percentMVC: null as number | null,
      }));
    }

    return samples.map((s) => {
      const rms = s.rms ?? s.envelope ?? 0;
      const percentMVC = (rms / mvcRmsUv) * 100;
      return {
        time: new Date(s.timestamp).getTime(),
        value: rms,
        percentMVC,
      };
    });
  }, [samples, mvcRmsUv]);

  const currentValue = chartData.length > 0 ? chartData[chartData.length - 1] : null;
  const inTargetZone = currentValue?.percentMVC != null 
    ? currentValue.percentMVC >= targetZoneMin && currentValue.percentMVC <= targetZoneMax
    : false;

  // Calculate y-axis domain for target zone visualization
  const yDomain = mvcRmsUv && mvcRmsUv > 0 
    ? [0, mvcRmsUv * (targetZoneMax / 100) * 1.2] // Show up to 120% of target zone max
    : undefined;

  return (
    <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-clinical-text">Real-Time Biofeedback</h3>
          <p className="text-xs text-clinical-text-dim">RMS Envelope</p>
        </div>
        <div className="flex items-center gap-4">
          {currentValue && (
            <div className="text-right">
              <div className="text-xs text-clinical-text-dim">Current</div>
              <div className={`text-lg font-bold ${inTargetZone ? 'text-clinical-success' : 'text-clinical-text'}`}>
                {currentValue.percentMVC != null 
                  ? `${currentValue.percentMVC.toFixed(1)}% MVC`
                  : `${currentValue.value.toFixed(1)} µV`}
              </div>
            </div>
          )}
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${
            inTargetZone 
              ? 'bg-green-100 text-green-800 border border-green-200' 
              : 'bg-gray-100 text-gray-600 border border-gray-200'
          }`}>
            {inTargetZone ? 'In Zone' : 'Out of Zone'}
          </div>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {/* Target Zone Overlay */}
            {mvcRmsUv && mvcRmsUv > 0 && (
              <ReferenceArea
                y1={mvcRmsUv * (targetZoneMin / 100)}
                y2={mvcRmsUv * (targetZoneMax / 100)}
                stroke="none"
                fill="#dcfce7"
                fillOpacity={0.3}
              />
            )}
            <XAxis
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${date.getSeconds()}s`;
              }}
              stroke="#475569"
              fontSize={11}
            />
            <YAxis
              domain={yDomain}
              tickFormatter={(value) => {
                if (mvcRmsUv && mvcRmsUv > 0) {
                  const percent = (value / mvcRmsUv) * 100;
                  return `${percent.toFixed(0)}%`;
                }
                return `${value.toFixed(0)}`;
              }}
              stroke="#475569"
              fontSize={11}
              label={{ value: mvcRmsUv ? '% MVC' : 'µV', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'percentMVC' && mvcRmsUv) {
                  return [`${((value / mvcRmsUv) * 100).toFixed(1)}% MVC`, '% MVC'];
                }
                return [`${value.toFixed(1)} µV`, 'RMS'];
              }}
              labelFormatter={(label) => new Date(label).toLocaleTimeString()}
            />
            <Line
              type="monotone"
              dataKey={mvcRmsUv && mvcRmsUv > 0 ? 'value' : 'value'}
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-4 mt-2 text-xs text-clinical-text-dim">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-200 rounded"></div>
          <span>Target Zone: {targetZoneMin}% - {targetZoneMax}% MVC</span>
        </div>
        {mvcRmsUv && (
          <div>
            MVC: {mvcRmsUv.toFixed(1)} µV
          </div>
        )}
      </div>
    </div>
  );
}
