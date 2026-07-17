import { useState, useEffect, useCallback } from 'react';
import UploadZone from './components/upload/UploadZone';
import ReportCard from './components/report/ReportCard';
import ChatPanel from './components/chat/ChatPanel';
import { uploadFloorPlan, startAnalysis, pollStatus, fetchReport, RateLimitError } from './utils/api';
import { C, F } from './utils/tokens';

const STEPS = {
  UPLOAD:    'upload',
  ANALYZING: 'analyzing',
  REPORT:    'report',
  ERROR:     'error',
};

const PIPELINE_STAGES = [
  { label: 'Uploading floor plan',        desc: 'Transmitting to analysis server',        key: 'upload' },
  { label: 'Extracting room geometry',    desc: 'Gemini Vision → structured JSON',         key: 'extract' },
  { label: 'Running rule engine',         desc: '6 categories, deterministic Python',      key: 'rules' },
  { label: 'Applying consistency filter', desc: '5-run majority vote, suppressing noise',  key: 'filter' },
  { label: 'Generating report',           desc: 'Scoring + LLM summary writing',           key: 'report' },
];

const FEATURES = [
  {
    tag:   'Pydantic v2 + retry',
    title: 'Schema-validated extraction',
    desc:  'Gemini returns geometry as structured JSON. Schema violations trigger automatic retry with the specific error appended to the prompt.',
  },
  {
    tag:   '6 rule categories',
    title: 'Deterministic rule engine',
    desc:  'Every finding is Python code over extracted geometry — no LLM reasoning about rules. Grounded in NBC 2016 and RERA.',
  },
  {
    tag:   'Majority-vote filter',
    title: 'Self-consistency filter',
    desc:  'The pipeline runs N times. Findings appearing in fewer than 3 of 5 runs are suppressed — noise never reaches the report.',
  },
  {
    tag:   'Function calling',
    title: 'Geometry chat agent',
    desc:  'Gemini calls deterministic tools: room_area(), fits_furniture(), sun_exposure() — tool outputs, not model speculation.',
  },
];

// ── LOGO MARK ─────────────────────────────────────────────────────────────────
// Floor plan outline with measurement bracket — communicates the product immediately
function LogoMark({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="1" y="2" width="20" height="28" rx="1.5" stroke="#F0A500" strokeWidth="2.5" />
      <line x1="1"  y1="16" x2="13" y2="16" stroke="#F0A500" strokeWidth="2.5" />
      <line x1="13" y1="2"  x2="13" y2="16" stroke="#F0A500" strokeWidth="2.5" />
      <line x1="24" y1="2"  x2="30" y2="2"  stroke="#F0A500" strokeWidth="1.5" />
      <line x1="24" y1="30" x2="30" y2="30" stroke="#F0A500" strokeWidth="1.5" />
      <line x1="27" y1="2"  x2="27" y2="30" stroke="#F0A500" strokeWidth="1" />
    </svg>
  );
}

// ── GHOST BLUEPRINT ───────────────────────────────────────────────────────────
// Architectural floor plan outline at 5.5% opacity in the hero background
function BlueprintBg() {
  return (
    <svg
      style={{ position: 'absolute', right: '3%', top: '50%', transform: 'translateY(-50%)', opacity: 0.055, pointerEvents: 'none' }}
      width="360" height="290" viewBox="0 0 420 320" fill="none" stroke="#F0A500" strokeWidth="1.5"
    >
      <rect x="15" y="15" width="390" height="290" rx="2" />
      <line x1="190" y1="15"  x2="190" y2="210" />
      <line x1="15"  y1="210" x2="265" y2="210" />
      <line x1="265" y1="15"  x2="265" y2="210" />
      <line x1="190" y1="155" x2="405" y2="155" />
      <line x1="330" y1="155" x2="330" y2="305" />
      <line x1="190" y1="265" x2="330" y2="265" />
      <path d="M190 193 A17 17 0 0 1 207 210" strokeDasharray="2 2" strokeWidth="1" />
      <path d="M248 15  A17 17 0 0 0 265 32"  strokeDasharray="2 2" strokeWidth="1" />
      <line x1="15"  y1="70"  x2="15"  y2="118" strokeWidth="4" />
      <line x1="405" y1="50"  x2="405" y2="98"  strokeWidth="4" />
      <line x1="80"  y1="15"  x2="148" y2="15"  strokeWidth="4" />
      <line x1="15"  y1="4"   x2="405" y2="4"   strokeWidth=".5" />
      <line x1="15"  y1="0"   x2="15"  y2="8"   strokeWidth=".5" />
      <line x1="405" y1="0"   x2="405" y2="8"   strokeWidth=".5" />
      <line x1="416" y1="15"  x2="416" y2="305" strokeWidth=".5" />
      <line x1="412" y1="15"  x2="420" y2="15"  strokeWidth=".5" />
      <line x1="412" y1="305" x2="420" y2="305" strokeWidth=".5" />
    </svg>
  );
}

// ── NAV BUTTON ────────────────────────────────────────────────────────────────
function NavBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '5px 12px',
        borderRadius: 8,
        fontSize: 12,
        fontWeight: 500,
        cursor: 'pointer',
        transition: 'all 0.15s',
        background: active ? C.acd : 'rgba(255,255,255,0.04)',
        border: `1px solid ${active ? 'rgba(240,165,0,0.3)' : C.bd}`,
        color: active ? C.ac : C.mu,
        fontFamily: F.body,
      }}
    >
      {children}
    </button>
  );
}

// ── MAIN APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const [step,        setStep]        = useState(STEPS.UPLOAD);
  const [planId,      setPlanId]      = useState(null);
  const [report,      setReport]      = useState(null);
  const [error,       setError]       = useState(null);
  const [isRateLimit, setIsRateLimit] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [showChat,    setShowChat]    = useState(false);
  const [previewUrl,  setPreviewUrl]  = useState(null);

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
          setError('Analysis failed. The floor plan may be unclear — try a higher-resolution image.');
          setStep(STEPS.ERROR);
        } else {
          setActiveStage(prev => Math.min(prev + 1, 3));
        }
      } catch (_) { /* keep polling */ }
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
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: C.bg, color: C.tx, fontFamily: F.body }}>

      {/* ── HEADER ─────────────────────────────────────────────────────────── */}
      <header style={{
        background: 'rgba(7,13,26,0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${C.bd}`,
        position: 'sticky', top: 0, zIndex: 20, height: 54,
      }}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-full flex items-center justify-between">
          <button
            onClick={handleReset}
            style={{ display: 'flex', alignItems: 'center', gap: 9, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            <LogoMark size={22} />
            <span style={{ fontFamily: F.display, fontSize: 16, fontWeight: 600, color: C.tx, letterSpacing: '-0.02em' }}>
              Plan<span style={{ color: C.ac }}>alyze</span>
            </span>
          </button>

          {step === STEPS.REPORT && (
            <div className="flex items-center gap-2">
              <NavBtn active={showChat} onClick={() => setShowChat(s => !s)}>⌥ Chat</NavBtn>
              <NavBtn onClick={handleReset}>New plan</NavBtn>
            </div>
          )}
        </div>
      </header>

      <main style={{ flex: 1 }}>

        {/* ── UPLOAD ───────────────────────────────────────────────────────── */}
        {step === STEPS.UPLOAD && (
          <div className="animate-fade-in">
            {/* Hero */}
            <div className="dot-grid relative overflow-hidden" style={{ padding: '64px 22px 48px', textAlign: 'center' }}>
              <BlueprintBg />
              <div style={{ position: 'relative', maxWidth: 580, margin: '0 auto' }}>
                {/* Status badge */}
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 7,
                  padding: '4px 13px', borderRadius: 9999, marginBottom: 22,
                  background: C.acd, border: '1px solid rgba(240,165,0,0.2)',
                }}>
                  <span className="animate-pulse-dot" style={{ width: 5, height: 5, borderRadius: '50%', background: C.ac, display: 'block' }} />
                  <span style={{ fontFamily: F.mono, fontSize: 10, color: C.ac, letterSpacing: '0.05em' }}>
                    NBC 2016 · RERA · Gemini 2.5 Flash
                  </span>
                </div>

                <h1 style={{
                  fontFamily: F.display,
                  fontSize: 'clamp(28px, 5vw, 46px)',
                  fontWeight: 700, lineHeight: 1.1, color: C.tx,
                  marginBottom: 14, letterSpacing: '-0.03em',
                }}>
                  Know if this apartment<br />
                  <span style={{ color: C.ac }}>is worth buying.</span>
                </h1>

                <p style={{ fontSize: 15, color: C.mu, lineHeight: 1.75, maxWidth: 460, margin: '0 auto 36px' }}>
                  Upload a floor plan. Get a verifiable analysis grounded in NBC 2016 standards — every finding cites the exact room and rule that triggered it.
                </p>

                <div style={{ maxWidth: 430, margin: '0 auto' }}>
                  <UploadZone onFileSelected={handleFile} />
                </div>
              </div>
            </div>

            {/* Feature cards */}
            <div className="max-w-5xl mx-auto" style={{ padding: '32px 22px 56px' }}>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {FEATURES.map((f) => (
                  <div key={f.title} className="feat-card">
                    <span style={{
                      fontFamily: F.mono, fontSize: 10, padding: '2px 8px', borderRadius: 4,
                      background: C.acd, color: C.ac, border: '1px solid rgba(240,165,0,0.15)',
                      display: 'inline-block', marginBottom: 10,
                    }}>{f.tag}</span>
                    <h3 style={{ fontFamily: F.display, fontSize: 13, fontWeight: 600, color: C.tx, marginBottom: 6 }}>{f.title}</h3>
                    <p style={{ fontSize: 12, color: C.mu, lineHeight: 1.65 }}>{f.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── ANALYZING ─────────────────────────────────────────────────────── */}
        {step === STEPS.ANALYZING && (
          <div className="animate-fade-in" style={{ maxWidth: 460, margin: '0 auto', padding: '40px 22px' }}>
            {previewUrl && (
              <div style={{ marginBottom: 18, borderRadius: 12, overflow: 'hidden', border: `1px solid ${C.bd}`, background: C.su }}>
                <img src={previewUrl} alt="Floor plan" style={{ width: '100%', maxHeight: 180, objectFit: 'contain', padding: 12 }} />
              </div>
            )}
            <div style={{ background: C.su, border: `1px solid ${C.bd}`, borderRadius: 14, padding: '22px 20px' }}>
              <div style={{ fontFamily: F.display, fontSize: 13, fontWeight: 600, color: C.tx, marginBottom: 20 }}>
                Running analysis pipeline
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {PIPELINE_STAGES.map((stage, i) => {
                  const done   = i < activeStage;
                  const active = i === activeStage;
                  return (
                    <div key={stage.key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{
                        width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: done   ? 'rgba(52,211,153,0.12)'  : active ? 'rgba(240,165,0,0.12)' : '#0A1322',
                        border:     `1.5px solid ${done ? 'rgba(52,211,153,0.3)' : active ? 'rgba(240,165,0,0.4)' : C.bd}`,
                        transition: 'all 0.4s',
                      }}>
                        {done   ? <span style={{ color: C.gn, fontWeight: 700, fontSize: 10 }}>✓</span>
                        : active ? <span className="animate-pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: C.ac, display: 'block' }} />
                        :          <span style={{ fontFamily: F.mono, fontSize: 9, color: C.fn }}>{i + 1}</span>}
                      </div>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: active ? 600 : 400, color: done ? C.gn : active ? C.tx : C.fn, transition: 'color 0.3s' }}>
                          {stage.label}
                        </div>
                        {active && <div style={{ fontFamily: F.mono, fontSize: 10, color: C.ac, marginTop: 2 }}>{stage.desc}</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
              <p style={{ fontFamily: F.mono, fontSize: 10, color: C.fn, marginTop: 20, textAlign: 'center' }}>
                typically 30–60 seconds
              </p>
            </div>
          </div>
        )}

        {/* ── REPORT ────────────────────────────────────────────────────────── */}
        {step === STEPS.REPORT && (
          <div className="animate-fade-in max-w-6xl mx-auto" style={{ padding: '20px 22px 52px' }}>
            <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                {previewUrl && (
                  <div style={{
                    marginBottom: 18, borderRadius: 12, overflow: 'hidden',
                    border: `1px solid ${C.bd}`, background: C.su,
                    ...(showChat ? {} : { maxWidth: 600, marginLeft: 'auto', marginRight: 'auto' }),
                  }}>
                    <img src={previewUrl} alt="Floor plan" style={{ width: '100%', maxHeight: 220, objectFit: 'contain', padding: 12 }} />
                  </div>
                )}
                <ReportCard report={report} />
              </div>

              {showChat && (
                <div
                  className="animate-slide-up"
                  style={{
                    width: 300, flexShrink: 0,
                    position: 'sticky', top: 62,
                    height: 'calc(100vh - 80px)',
                    border: `1px solid ${C.bd}`,
                    borderRadius: 14, overflow: 'hidden',
                    display: 'flex', flexDirection: 'column',
                  }}
                >
                  <ChatPanel planId={planId} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── ERROR ─────────────────────────────────────────────────────────── */}
        {step === STEPS.ERROR && (
          <div className="animate-fade-in" style={{ maxWidth: 420, margin: '0 auto', padding: '72px 22px', textAlign: 'center' }}>
            <div style={{
              width: 56, height: 56, margin: '0 auto 20px',
              background: 'rgba(248,113,113,0.10)', borderRadius: 16,
              border: '1px solid rgba(248,113,113,0.20)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 22,
            }}>
              {isRateLimit ? '⏳' : '⚠'}
            </div>
            <h2 style={{ fontFamily: F.display, fontSize: 22, fontWeight: 600, color: C.tx, marginBottom: 10 }}>
              {isRateLimit ? 'Daily limit reached' : 'Something went wrong'}
            </h2>
            <p style={{ fontSize: 13, color: C.mu, marginBottom: 8 }}>{error}</p>
            {isRateLimit && (
              <p style={{ fontSize: 12, color: C.fn, marginBottom: 20 }}>
                This is a portfolio project with limited API credits. The limit resets daily — please try again tomorrow.
              </p>
            )}
            {!isRateLimit && (
              <button
                onClick={handleReset}
                style={{
                  marginTop: 14, padding: '9px 22px',
                  background: C.ac, color: '#0A0C14',
                  fontWeight: 600, fontFamily: F.display, fontSize: 13,
                  borderRadius: 10, border: 'none', cursor: 'pointer',
                }}
              >
                Try again
              </button>
            )}
          </div>
        )}
      </main>

      {/* ── FOOTER ─────────────────────────────────────────────────────────── */}
      <footer style={{
        textAlign: 'center', padding: '13px 22px',
        borderTop: ' 1px solid rgba(29,46,69,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 9,
      }}>
        <LogoMark size={13} />
        <span style={{ fontFamily: F.mono, fontSize: 10, color: C.fn }}>
          Findings grounded in NBC 2016 &amp; RERA — traceable, not generated
        </span>
      </footer>
    </div>
  );
}
