import { scoreColor, scoreBgColor, scoreLabel } from '../../utils/formatters';

export default function ScoreBadge({ score }) {
  return (
    <div className={`inline-flex flex-col items-center rounded-2xl border px-8 py-5 ${scoreBgColor(score)}`}>
      <span className={`text-5xl font-bold font-display ${scoreColor(score)}`}>
        {score}
      </span>
      <span className="text-xs font-semibold uppercase tracking-widest text-gray-500 mt-1">
        / 100
      </span>
      <span className={`text-sm font-semibold mt-1 ${scoreColor(score)}`}>
        {scoreLabel(score)}
      </span>
    </div>
  );
}