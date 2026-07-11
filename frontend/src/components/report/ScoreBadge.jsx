import { scoreLabel } from '../../utils/formatters';

function scoreColor(score) {
  if (score >= 70) return { stroke: '#16a34a', text: 'text-green-600', bg: 'bg-green-50' };
  if (score >= 40) return { stroke: '#ca8a04', text: 'text-yellow-600', bg: 'bg-yellow-50' };
  return { stroke: '#dc2626', text: 'text-red-600', bg: 'bg-red-50' };
}

export default function ScoreBadge({ score }) {
  const colors = scoreColor(score);
  const circumference = 2 * Math.PI * 45; // r=45
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          {/* Background ring */}
          <circle cx="50" cy="50" r="45" fill="none" stroke="#f1f5f9" strokeWidth="8" />
          {/* Score ring */}
          <circle
            cx="50" cy="50" r="45" fill="none"
            stroke={colors.stroke}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="score-ring-animated"
            style={{ '--score-offset': offset }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold font-display ${colors.text}`}>{score}</span>
          <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">/100</span>
        </div>
      </div>
      <span className={`text-xs font-semibold mt-2 px-3 py-1 rounded-full ${colors.bg} ${colors.text}`}>
        {scoreLabel(score)}
      </span>
    </div>
  );
}