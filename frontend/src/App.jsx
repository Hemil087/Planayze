import { useState, useEffect, useCallback } from 'react';
import UploadZone from './components/upload/UploadZone';
import ReportCard from './components/report/ReportCard';
import ChatPanel from './components/chat/ChatPanel';
import { uploadFloorPlan, startAnalysis, pollStatus, fetchReport } from './utils/api';

const STEPS = {
  UPLOAD: 'upload',
  ANALYZING: 'analyzing',
  REPORT: 'report',
  ERROR: 'error',
};

export default function App() {
  const [step, setStep] = useState(STEPS.UPLOAD);
  const [planId, setPlanId] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState('Uploading...');
  const [showChat, setShowChat] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);

  // ── Upload + trigger analysis ──────────────────────────────
  const handleFile = useCallback(async (file) => {
    try {
      setStep(STEPS.ANALYZING);
      setProgress('Uploading floor plan...');
      setPreviewUrl(URL.createObjectURL(file));

      const uploadRes = await uploadFloorPlan(file);
      const id = uploadRes.plan_id;
      setPlanId(id);

      setProgress('Starting analysis...');
      await startAnalysis(id);

      setProgress('Analyzing floor plan — this takes 30–60 seconds...');
    } catch (err) {
      setError(err.message);
      setStep(STEPS.ERROR);
    }
  }, []);

  // ── Poll for completion ────────────────────────────────────
  useEffect(() => {
    if (step !== STEPS.ANALYZING || !planId) return;

    const interval = setInterval(async () => {
      try {
        const status = await pollStatus(planId);
        if (status.status === 'COMPLETED') {
          clearInterval(interval);
          setProgress('Loading report...');
          const reportData = await fetchReport(planId);
          setReport(reportData);
          setStep(STEPS.REPORT);
        } else if (status.status === 'FAILED') {
          clearInterval(interval);
          setError('Analysis failed. Please try again with a different image.');
          setStep(STEPS.ERROR);
        }
      } catch (err) {
        // Keep polling on transient errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [step, planId]);

  // ── Reset ──────────────────────────────────────────────────
  const handleReset = () => {
    setStep(STEPS.UPLOAD);
    setPlanId(null);
    setReport(null);
    setError(null);
    setShowChat(false);
    setPreviewUrl(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <button onClick={handleReset} className="flex items-center gap-2 hover:opacity-80 transition">
            <span className="text-xl">📐</span>
            <h1 className="font-display text-xl text-gray-900">Planalyze</h1>
          </button>
          {step === STEPS.REPORT && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowChat(!showChat)}
                className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                  showChat ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                💬 {showChat ? 'Hide Chat' : 'Chat with Plan'}
              </button>
              <button
                onClick={handleReset}
                className="text-sm font-medium px-4 py-2 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                ← New Plan
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        {/* Upload Step */}
        {step === STEPS.UPLOAD && (
          <div className="max-w-xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
            <div className="text-center mb-8">
              <h2 className="font-display text-3xl sm:text-4xl text-gray-900 mb-3">
                Analyze your floor plan
              </h2>
              <p className="text-gray-500 text-lg">
                Upload a floor plan and get a structured pros & cons report grounded in architecture standards.
              </p>
            </div>
            <UploadZone onFileSelected={handleFile} />
          </div>
        )}

        {/* Analyzing Step */}
        {step === STEPS.ANALYZING && (
          <div className="max-w-xl mx-auto px-4 sm:px-6 py-16 sm:py-24 text-center">
            {previewUrl && (
              <div className="mb-8 rounded-xl overflow-hidden border border-gray-200 shadow-sm">
                <img src={previewUrl} alt="Floor plan" className="w-full max-h-64 object-contain bg-white p-2" />
              </div>
            )}
            <div className="inline-flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
              <p className="text-gray-600 font-medium">{progress}</p>
              <p className="text-sm text-gray-400">
                Extracting geometry → running rules → building report
              </p>
            </div>
          </div>
        )}

        {/* Report Step */}
        {step === STEPS.REPORT && (
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
            <div className={`flex gap-6 ${showChat ? 'flex-col lg:flex-row' : ''}`}>
              {/* Report */}
              <div className={`${showChat ? 'lg:w-3/5' : 'w-full max-w-3xl mx-auto'}`}>
                {previewUrl && (
                  <div className="mb-6 rounded-xl overflow-hidden border border-gray-200 shadow-sm">
                    <img src={previewUrl} alt="Floor plan" className="w-full max-h-72 object-contain bg-white p-2" />
                  </div>
                )}
                <ReportCard report={report} />
              </div>

              {/* Chat */}
              {showChat && (
                <div className="lg:w-2/5 lg:sticky lg:top-20 lg:h-[calc(100vh-6rem)] border rounded-xl overflow-hidden bg-white shadow-sm">
                  <ChatPanel planId={planId} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error Step */}
        {step === STEPS.ERROR && (
          <div className="max-w-xl mx-auto px-4 sm:px-6 py-16 sm:py-24 text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h2 className="font-display text-2xl text-gray-900 mb-2">Something went wrong</h2>
            <p className="text-gray-500 mb-6">{error}</p>
            <button
              onClick={handleReset}
              className="px-6 py-2.5 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-xs text-gray-400 border-t">
        Planalyze — Rules grounded in NBC 2016 & RERA standards
      </footer>
    </div>
  );
}