import ScoreBadge from './ScoreBadge';
import FindingItem from './FindingItem';

export default function ReportCard({ report }) {
  if (!report) return null;

  return (
    <div className="space-y-8">
      {/* Score + Summary */}
      <div className="flex flex-col sm:flex-row items-start gap-6">
        <ScoreBadge score={report.overall_score} />
        <div className="flex-1">
          <h2 className="font-display text-2xl text-gray-900 mb-2">Analysis Summary</h2>
          <p className="text-gray-600 leading-relaxed">{report.summary_text}</p>
        </div>
      </div>

      {/* Cons */}
      {report.cons?.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-3">
            Issues Found ({report.cons.length})
          </h3>
          <div className="space-y-3">
            {report.cons.map((f) => (
              <FindingItem key={f.id} finding={f} />
            ))}
          </div>
        </section>
      )}

      {/* Pros */}
      {report.pros?.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-3">
            Positive Aspects ({report.pros.length})
          </h3>
          <div className="space-y-3">
            {report.pros.map((f) => (
              <FindingItem key={f.id} finding={f} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}