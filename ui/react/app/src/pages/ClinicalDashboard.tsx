import { useState, useEffect, useCallback } from 'react';
import PatientHeader from '@components/PatientHeader';
import RealTimeBiofeedback from '@components/RealTimeBiofeedback';
import FrequencyDomainChart from '@components/FrequencyDomainChart';
import FatigueTrend from '@components/FatigueTrend';
import ActionSidebar from '@components/ActionSidebar';
import { api } from '@api/client';
import type { TrialRead, SessionRead } from '@api/types';
import { useDeviceStore } from '@state/deviceStore';

// Mock patient data - in production, this would come from props or context
const MOCK_PATIENT = {
  id: 1,
  name: 'John Doe',
  affectedSide: 'left' as const,
  baselineMVC: 450.0, // microvolts
};

export default function ClinicalDashboard() {
  const { selectedChannel } = useDeviceStore();
  const [currentSession, setCurrentSession] = useState<SessionRead | null>(null);
  const [currentTrial, setCurrentTrial] = useState<TrialRead | null>(null);
  const [isTrialActive, setIsTrialActive] = useState(false);
  const [recentTrials, setRecentTrials] = useState<TrialRead[]>([]);
  const [trialStartTime, setTrialStartTime] = useState<Date | null>(null);
  const [psdUpdateKey, setPsdUpdateKey] = useState(0); // Force PSD re-render

  // Initialize or load current session
  useEffect(() => {
    // In production, load from API or context
    // For now, create a mock session
    const loadSession = async () => {
      try {
        // This would be: const session = await api.getCurrentSession();
        // For now, we'll use a placeholder
        setCurrentSession({
          id: 1,
          patient_id: MOCK_PATIENT.id,
          started_at: new Date().toISOString(),
          ended_at: null,
          notes: null,
        });
      } catch (err) {
        console.error('Failed to load session:', err);
      }
    };
    loadSession();
  }, []);

  // Update PSD chart periodically when trial is active
  useEffect(() => {
    if (isTrialActive && trialStartTime) {
      const interval = setInterval(() => {
        // Trigger re-render of PSD chart by updating key
        setPsdUpdateKey((prev) => prev + 1);
      }, 2000); // Update every 2 seconds
      return () => clearInterval(interval);
    }
  }, [isTrialActive, trialStartTime]);

  const handleStartTrial = useCallback(async () => {
    if (!currentSession) {
      alert('No active session. Please create a session first.');
      return;
    }

    try {
      const trial: TrialRead = await api.createTrial(currentSession.id, {
        session_id: currentSession.id,
        name: `Trial ${recentTrials.length + 1}`,
        channel: selectedChannel,
        limb: MOCK_PATIENT.affectedSide === 'left' ? 'affected' : 'healthy',
        movement_type: 'reps',
        started_at: new Date().toISOString(),
        mvc_rms_uv: currentTrial?.mvc_rms_uv || MOCK_PATIENT.baselineMVC,
      });

      setCurrentTrial(trial);
      setIsTrialActive(true);
      setTrialStartTime(new Date());
    } catch (err) {
      console.error('Failed to start trial:', err);
      alert('Failed to start trial. Please check your connection.');
    }
  }, [currentSession, selectedChannel, recentTrials.length, currentTrial]);

  const handleStopTrial = useCallback(async () => {
    if (!currentTrial) return;

    try {
      // Update trial with end time
      const endTime = new Date().toISOString();
      // In production: await api.updateTrial(currentTrial.id, { ended_at: endTime });
      
      // Compute PSD for the trial to get median frequency
      if (trialStartTime) {
        try {
          const psd = await api.analyticsPsd(
            selectedChannel,
            trialStartTime.toISOString(),
            endTime,
            { method: 'welch' }
          );
          
          // Store median frequency with trial (would update trial in production)
          const updatedTrial = { ...currentTrial, ended_at: endTime };
          setRecentTrials((prev) => [...prev, { ...updatedTrial, medianFrequency: psd.mdf } as any]);
        } catch (err) {
          console.error('Failed to compute PSD:', err);
        }
      }

      setIsTrialActive(false);
      setTrialStartTime(null);
      setCurrentTrial(null);
    } catch (err) {
      console.error('Failed to stop trial:', err);
    }
  }, [currentTrial, trialStartTime, selectedChannel]);

  const handleCaptureMVC = useCallback(async () => {
    if (!currentTrial) {
      alert('Please start a trial first.');
      return;
    }

    try {
      // Capture last 3 seconds of data for MVC calculation
      const end = new Date();
      const start = new Date(end.getTime() - 3000);
      const samples = await api.emgHistory(start.toISOString(), end.toISOString(), selectedChannel);
      
      if (Array.isArray(samples) && samples.length > 0) {
        // Calculate RMS from samples
        const rmsValues = samples
          .map((s: any) => s.rms ?? s.envelope ?? 0)
          .filter((v: number) => v > 0);
        
        if (rmsValues.length > 0) {
          const maxRms = Math.max(...rmsValues);
          await api.setTrialMVC(currentTrial.id, maxRms);
          
          // Update current trial
          setCurrentTrial((prev) => prev ? { ...prev, mvc_rms_uv: maxRms } : null);
          alert(`MVC captured: ${maxRms.toFixed(1)} µV`);
        }
      }
    } catch (err) {
      console.error('Failed to capture MVC:', err);
      alert('Failed to capture MVC. Please try again.');
    }
  }, [currentTrial, selectedChannel]);

  const handleFlagCompensation = useCallback(() => {
    // In production, this would create a compensation flag/note
    alert('Compensation flagged. This would be logged in production.');
  }, []);

  // Calculate time window for PSD (last 5 seconds of trial or recent data)
  const psdStartTime = trialStartTime 
    ? new Date(Math.max(trialStartTime.getTime(), Date.now() - 5000)).toISOString()
    : new Date(Date.now() - 5000).toISOString();
  const psdEndTime = new Date().toISOString();

  return (
    <div className="min-h-screen bg-clinical-bg p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Patient Header */}
        <PatientHeader
          patientName={MOCK_PATIENT.name}
          affectedSide={MOCK_PATIENT.affectedSide}
          baselineMVC={MOCK_PATIENT.baselineMVC}
          currentMVC={currentTrial?.mvc_rms_uv || null}
        />

        {/* Main Content Grid - Tablet Optimized */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Left Column: Real-time Biofeedback and Frequency Domain */}
          <div className="lg:col-span-3 space-y-4">
            {/* Real-Time Biofeedback */}
            <RealTimeBiofeedback
              channel={selectedChannel}
              mvcRmsUv={currentTrial?.mvc_rms_uv || MOCK_PATIENT.baselineMVC}
              targetZoneMin={20}
              targetZoneMax={80}
              windowSeconds={10}
            />

            {/* Frequency Domain and Fatigue Trend Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <FrequencyDomainChart
                  key={psdUpdateKey}
                  channel={selectedChannel}
                  startISO={psdStartTime}
                  endISO={psdEndTime}
                  height={300}
                />
              </div>
              <div className="md:col-span-1">
                <FatigueTrend
                  trials={recentTrials}
                  height={300}
                />
              </div>
            </div>
          </div>

          {/* Right Column: Action Sidebar - Optimized for one-handed tablet use */}
          <div className="lg:col-span-1">
            <div className="sticky top-4">
              <ActionSidebar
                isTrialActive={isTrialActive}
                onStartTrial={handleStartTrial}
                onStopTrial={handleStopTrial}
                onCaptureMVC={handleCaptureMVC}
                onFlagCompensation={handleFlagCompensation}
                disabled={!currentSession}
              />
            </div>
          </div>
        </div>

        {/* Trial Info Footer */}
        {currentTrial && (
          <div className="bg-white border border-clinical-border rounded-lg p-3">
            <div className="flex items-center justify-between text-sm">
              <div>
                <span className="text-clinical-text-dim">Current Trial: </span>
                <span className="font-semibold text-clinical-text">{currentTrial.name}</span>
              </div>
              {trialStartTime && (
                <div className="text-clinical-text-dim">
                  Duration: {Math.floor((Date.now() - trialStartTime.getTime()) / 1000)}s
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
