import { useState, useEffect, useCallback } from 'react';
import UploadZone from './components/upload/UploadZone';
import ReportCard from './components/report/ReportCard';
import ChatPanel from './components/chat/ChatPanel';
import { uploadFloorPlan, startAnalysis, pollStatus, fetchReport, RateLimitError } from './utils/api';

const STEPS = {
  UPLOAD: 'upload',
  ANALYZING: 'analyzing',
  REPORT: 'report',
  ERROR: 'error',
};

const PIPELINE_STAGES = [
  { label: 'Uploading floor plan', key: 'upload' },
  { label: 'Extracting room geometry', key: 'extract' },
  { label: 'Running rule engine', key: 'rules' },
  { label: 'Applying consistency filter', key: 'filter' },
  { label: 'Generating report', key: 'report' },
];

const FEATURES = [
  { icon: '🔍', title: 'Schema-Validated Extraction', desc: 'Gemini extracts geometry as structured JSON with retry on violations' },
  { icon: '⚖️', title: 'Deterministic Rules', desc: 'Every finding comes from Python code grounded in NBC 2016 standards' },
  { icon: '🛡️', title: 'Consistency Filter', desc: 'Pipeline runs N times — only recurring findings survive' },
  { icon: '💬', title: 'Chat with Your Plan', desc: 'Ask geometry questions answered by deterministic tools, not guesswork' },
];

export default function App() {
  const [step, setStep] = useState(STEPS.UPLOAD);
  const [planId, setPlanId] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [isRateLimit, setIsRateLimit] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [showChat, setShowChat] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);

  const handleFile = useCallback(async (file) => {
    try {
      setStep(STEPS.ANALYZING);
      setActiveStage(0);
      setPreviewUrl(URL.createObjectURL(file));

      const uploadRes = await uploadFloorPlan(file);
      const id = uploadRes.plan_id;
      setPlanId(id);

      setActiveStage(1);
      await startAnalysis(id);
      setActiveStage(2);
    } catch (err) {
      setIsRateLimit(err instanceof RateLimitError);
      setError(err.message);
      setStep(STEPS.ERROR);
    }
  }, []);

  useEffect(() => {
    if (step !== STEPS.ANALYZING || !planId) return;

    const interval = setInterval(async () => {
      try {
        const status = await pollStatus(planId);
        if (status.status === 'COMPLETED') {
          clearInterval(interval);
          setActiveStage(4);
          const reportData = await fetchReport(planId);
          setReport(reportData);
          setTimeout(() => setStep(STEPS.REPORT), 400);
        } else if (status.status === 'FAILED') {
          clearInterval(interval);
          setError('Analysis failed. The floor plan may be unclear — try a higher resolution image.');
          setStep(STEPS.ERROR);
        } else {
          // Simulate stage progress while processing
          setActiveStage(prev => Math.min(prev + 1, 3));
        }
      } catch (err) { /* keep polling */ }
    }, 3000);

    return () => clearInterval(interval);
  }, [step, planId]);

  const handleReset = () => {
    setStep(STEPS.UPLOAD);
    setPlanId(null);
    setReport(null);
    setError(null);
    setIsRateLimit(false);
    setShowChat(false);
    setPreviewUrl(null);
    setActiveStage(0);
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50/50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <button onClick={handleReset} className="flex items-center gap-2.5 hover:opacity-80 transition group">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <span className="text-white text-sm font-bold">P</span>
            </div>
            <span className="font-display text-lg text-gray-900">Planalyze</span>
          </button>
          {step === STEPS.REPORT && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowChat(!showChat)}
                className={`text-sm font-medium px-3.5 py-1.5 rounded-lg transition-all duration-200 ${
                  showChat
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                💬 Chat
              </button>
              <button
                onClick={handleReset}
                className="text-sm font-medium px-3.5 py-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                New Plan
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="flex-1">
        {/* ── UPLOAD ─────────────────────────────────────── */}
        {step === STEPS.UPLOAD && (
          <div className="animate-fade-in">
            {/* Hero */}
            <div className="max-w-2xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-10 text-center">
              <div className="inline-flex items-center gap-2 text-xs font-medium text-brand-700 bg-brand-50 px-3 py-1 rounded-full mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
                Powered by Gemini 2.5 Flash + NBC 2016
              </div>
              <h2 className="font-display text-4xl sm:text-5xl text-gray-900 mb-4 leading-tight">
                Know what you're buying<br />
                <span className="text-brand-600">before you buy it</span>
              </h2>
              <p className="text-gray-500 text-lg max-w-lg mx-auto">
                Upload a floor plan. Get a verifiable pros & cons report grounded in architecture standards — every finding traceable to a specific room and rule.
              </p>
            </div>

            {/* Upload */}
            <div className="max-w-lg mx-auto px-4 sm:px-6 pb-16">
              <UploadZone onFileSelected={handleFile} />
            </div>

            {/* Features */}
            <div className="max-w-4xl mx-auto px-4 sm:px-6 pb-20">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {FEATURES.map((f) => (
                  <div key={f.title} className="flex gap-3.5 p-4 rounded-xl border border-gray-100 bg-white hover:shadow-sm transition-shadow">
                    <span className="text-xl shrink-0 mt-0.5">{f.icon}</span>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-800">{f.title}</h3>
                      <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{f.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── ANALYZING ──────────────────────────────────── */}
        {step === STEPS.ANALYZING && (
          <div className="max-w-lg mx-auto px-4 sm:px-6 py-16 animate-fade-in">
            {previewUrl && (
              <div className="mb-8 rounded-2xl overflow-hidden border border-gray-200 shadow-sm bg-white">
                <img src={previewUrl} alt="Floor plan" className="w-full max-h-56 object-contain p-3" />
              </div>
            )}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
              <div className="space-y-3">
                {PIPELINE_STAGES.map((stage, i) => (
                  <div key={stage.key} className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 transition-all duration-500 ${
                      i < activeStage ? 'bg-green-100 text-green-600' :
                      i === activeStage ? 'bg-brand-100 text-brand-600' :
                      'bg-gray-100 text-gray-400'
                    }`}>
                      {i < activeStage ? '✓' :
                       i === activeStage ? (
                        <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
                       ) : (i + 1)}
                    </div>
                    <span className={`text-sm transition-colors duration-300 ${
                      i < activeStage ? 'text-green-700 font-medium' :
                      i === activeStage ? 'text-gray-900 font-medium' :
                      'text-gray-400'
                    }`}>
                      {stage.label}
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-5 text-center">This typically takes 30–60 seconds</p>
            </div>
          </div>
        )}

        {/* ── REPORT ─────────────────────────────────────── */}
        {step === STEPS.REPORT && (
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 animate-fade-in">
            <div className={`flex gap-6 ${showChat ? 'flex-col lg:flex-row' : ''}`}>
              <div className={`${showChat ? 'lg:w-3/5' : 'w-full max-w-3xl mx-auto'} transition-all duration-300`}>
                {previewUrl && (
                  <div className="mb-6 rounded-2xl overflow-hidden border border-gray-200 shadow-sm bg-white">
                    <img src={previewUrl} alt="Floor plan" className="w-full max-h-64 object-contain p-3" />
                  </div>
                )}
                <ReportCard report={report} />
              </div>

              {showChat && (
                <div className="lg:w-2/5 lg:sticky lg:top-16 lg:h-[calc(100vh-5rem)] border border-gray-200 rounded-2xl overflow-hidden bg-white shadow-sm animate-slide-up">
                  <ChatPanel planId={planId} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── ERROR ──────────────────────────────────────── */}
        {step === STEPS.ERROR && (
          <div className="max-w-md mx-auto px-4 sm:px-6 py-20 text-center animate-fade-in">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-red-50 flex items-center justify-center mb-5">
              <span className="text-2xl">{isRateLimit ? '⏳' : '⚠️'}</span>
            </div>
            <h2 className="font-display text-2xl text-gray-900 mb-2">
              {isRateLimit ? 'Daily limit reached' : 'Something went wrong'}
            </h2>
            <p className="text-gray-500 text-sm mb-2">{error}</p>
            {isRateLimit && (
              <p className="text-gray-400 text-xs mb-6">
                This is a portfolio project with limited API credits. The limit resets daily — please try again tomorrow!
              </p>
            )}
            {!isRateLimit && (
              <button
                onClick={handleReset}
                className="mt-4 px-6 py-2.5 bg-brand-600 text-white font-medium rounded-xl hover:bg-brand-700 transition-all active:scale-95 shadow-sm"
              >
                Try Again
              </button>
            )}
          </div>
        )}
      </main>

      <footer className="text-center py-4 text-[11px] text-gray-400 border-t border-gray-100">
        Rules grounded in NBC 2016 & RERA standards — findings are traceable, not generated
      </footer>
    </div>
  );
}