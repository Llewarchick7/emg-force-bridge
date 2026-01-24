import { Activity, AlertCircle } from 'lucide-react';

type PatientHeaderProps = {
  patientName?: string;
  affectedSide?: 'left' | 'right' | null;
  baselineMVC?: number | null; // in microvolts
  currentMVC?: number | null; // in microvolts
};

export default function PatientHeader({ 
  patientName = 'Patient', 
  affectedSide, 
  baselineMVC,
  currentMVC 
}: PatientHeaderProps) {
  const sideLabel = affectedSide ? `${affectedSide.charAt(0).toUpperCase() + affectedSide.slice(1)} Side` : 'Side Unknown';
  const statusLabel = affectedSide ? 'Affected' : 'Status Unknown';
  
  return (
    <div className="bg-white border border-clinical-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-lg font-semibold text-clinical-text">{patientName}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-clinical-text-dim">{sideLabel}</span>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                affectedSide 
                  ? 'bg-orange-100 text-orange-800 border border-orange-200' 
                  : 'bg-gray-100 text-gray-600 border border-gray-200'
              }`}>
                {affectedSide && <AlertCircle className="w-3 h-3" />}
                {statusLabel}
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-xs text-clinical-text-dim mb-1">Baseline MVC</div>
            <div className="text-lg font-semibold text-clinical-text">
              {baselineMVC != null ? `${baselineMVC.toFixed(1)} µV` : '—'}
            </div>
          </div>
          
          {currentMVC != null && currentMVC !== baselineMVC && (
            <div className="text-right">
              <div className="text-xs text-clinical-text-dim mb-1">Current MVC</div>
              <div className="text-lg font-semibold text-clinical-accent">
                {currentMVC.toFixed(1)} µV
              </div>
            </div>
          )}
          
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-clinical-accent" />
            <span className="text-sm font-medium text-clinical-text">Active Session</span>
          </div>
        </div>
      </div>
    </div>
  );
}
