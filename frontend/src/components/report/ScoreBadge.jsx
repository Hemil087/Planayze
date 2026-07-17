import { C, F } from '../../utils/tokens';

function scoreAppearance(score) {
  if (score >= 70) return { stroke: C.gn, label: 'Good buy',               bg: 'rgba(52,211,153,0.12)',  text: C.gn };
  if (score >= 40) return { stroke: C.ac,  label: 'Proceed with caution',  bg: 'rgba(240,165,0,0.12)',   text: C.ac };
  return             { stroke: C.re,  label: 'Significant concerns',  bg: 'rgba(248,113,113,0.12)', text: C.re };
}

export default function ScoreBadge({ score }) {
  const { stroke, label, bg, text } = scoreAppearance(score);
  const circumference = 2 * Math.PI * 45; // r = 45
  const offset = circumference * (1 - score / 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, flexShrink: 0 }}>
      {/* Ring gauge */}
      <div style={{ position: 'relative', width: 112, height: 112 }}>
        <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
          {/* Track */}
          <circle cx="50" cy="50" r="45" fill="none" stroke={C.bd} strokeWidth="7" />
          {/* Score arc — animates from 0 to score on mount */}
          <circle
            cx="50" cy="50" r="45"
            fill="none"
            stroke={stroke}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="score-ring-animated"
          />
        </svg>
        {/* Numeric readout */}
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontFamily: F.display, fontSize: 28, fontWeight: 700, color: stroke, lineHeight: 1 }}>
            {score}
          </span>
          <span style={{ fontFamily: F.mono, fontSize: 8, color: C.fn, marginTop: 1 }}>/100</span>
        </div>
      </div>

      {/* Label pill */}
      <span style={{
        fontSize: 10, fontWeight: 600,
        padding: '3px 10px', borderRadius: 9999,
        background: bg, color: text,
      }}>
        {label}
      </span>
    </div>
  );
}
