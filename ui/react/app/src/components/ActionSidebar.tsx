import { Play, Square, Target, Flag, Loader2 } from 'lucide-react';
import { useState } from 'react';

type ActionSidebarProps = {
  isTrialActive: boolean;
  onStartTrial: () => void;
  onStopTrial: () => void;
  onCaptureMVC: () => void;
  onFlagCompensation: () => void;
  disabled?: boolean;
};

export default function ActionSidebar({
  isTrialActive,
  onStartTrial,
  onStopTrial,
  onCaptureMVC,
  onFlagCompensation,
  disabled = false,
}: ActionSidebarProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (action: () => void | Promise<void>, actionName: string) => {
    if (disabled || loading) return;
    setLoading(actionName);
    try {
      await action();
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-clinical-text mb-4">Actions</h3>
      
      <div className="flex flex-col gap-3">
        {/* Start/Stop Trial Button */}
        {!isTrialActive ? (
          <button
            onClick={() => handleAction(onStartTrial, 'start')}
            disabled={disabled || loading !== null}
            className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-clinical-accent text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading === 'start' ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            Start Trial
          </button>
        ) : (
          <button
            onClick={() => handleAction(onStopTrial, 'stop')}
            disabled={disabled || loading !== null}
            className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading === 'stop' ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Square className="w-5 h-5" />
            )}
            Stop Trial
          </button>
        )}

        {/* Capture MVC Button */}
        <button
          onClick={() => handleAction(onCaptureMVC, 'mvc')}
          disabled={disabled || loading !== null || isTrialActive}
          className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-clinical-text text-white rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading === 'mvc' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Target className="w-5 h-5" />
          )}
          Capture MVC
        </button>

        {/* Flag Compensation Button */}
        <button
          onClick={() => handleAction(onFlagCompensation, 'flag')}
          disabled={disabled || loading !== null}
          className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading === 'flag' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Flag className="w-5 h-5" />
          )}
          Flag Compensation
        </button>
      </div>

      {/* Status Indicator */}
      <div className="mt-4 pt-4 border-t border-clinical-border">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isTrialActive ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
          <span className="text-xs text-clinical-text-dim">
            {isTrialActive ? 'Trial Active' : 'Trial Inactive'}
          </span>
        </div>
      </div>
    </div>
  );
}
