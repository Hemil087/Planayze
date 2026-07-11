import { useState } from 'react';
import ScoreBadge from './ScoreBadge';
import FindingItem from './FindingItem';
import { SEVERITY_CONFIG, CATEGORY_LABELS, CATEGORY_ICONS } from '../../utils/constants';

function groupByCategory(findings) {
  const groups = {};
  for (const f of findings) {
    const cat = f.category;
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(f);
  }
  return groups;
}

function StatPill({ count, severity }) {
  const config = SEVERITY_CONFIG[severity];
  if (!count) return null;
  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      <span className="text-sm font-medium text-gray-700">{count}</span>
      <span className="text-sm text-gray-400">{config.label.toLowerCase()}</span>
    </div>
  );
}

export default function ReportCard({ report }) {
  const [activeTab, setActiveTab] = useState('issues');

  if (!report) return null;

  const violationCount = report.cons?.filter(f => f.severity === 'VIOLATION').length || 0;
  const tradeoffCount = report.cons?.filter(f => f.severity === 'TRADEOFF').length || 0;
  const consByCategory = groupByCategory(report.cons || []);
  const prosByCategory = groupByCategory(report.pros || []);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Score + Summary Header */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <ScoreBadge score={report.overall_score} />
          <div className="flex-1 text-center sm:text-left">
            <h2 className="font-display text-2xl text-gray-900 mb-3">Analysis Report</h2>
            <p className="text-gray-500 leading-relaxed text-sm">{report.summary_text}</p>
            <div className="flex items-center gap-4 mt-4 justify-center sm:justify-start">
              <StatPill count={violationCount} severity="VIOLATION" />
              <StatPill count={tradeoffCount} severity="TRADEOFF" />
              <StatPill count={report.pros?.length} severity="OBSERVATION" />
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
        {[
          { id: 'issues', label: `Issues (${report.cons?.length || 0})` },
          { id: 'positives', label: `Positives (${report.pros?.length || 0})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-all ${
              activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Issues Tab — grouped by category */}
      {activeTab === 'issues' && (
        <div className="space-y-6 animate-fade-in">
          {Object.entries(consByCategory).map(([category, findings]) => (
            <section key={category}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-base">{CATEGORY_ICONS[category] || '📋'}</span>
                <h3 className="text-sm font-semibold text-gray-700">
                  {CATEGORY_LABELS[category] || category}
                </h3>
                <span className="text-xs text-gray-400 font-medium">({findings.length})</span>
              </div>
              <div className="space-y-2">
                {findings.map(f => <FindingItem key={f.id} finding={f} />)}
              </div>
            </section>
          ))}
          {Object.keys(consByCategory).length === 0 && (
            <p className="text-center text-gray-400 py-8">No issues found — this is a great floor plan!</p>
          )}
        </div>
      )}

      {/* Positives Tab — grouped by category */}
      {activeTab === 'positives' && (
        <div className="space-y-6 animate-fade-in">
          {Object.entries(prosByCategory).map(([category, findings]) => (
            <section key={category}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-base">{CATEGORY_ICONS[category] || '📋'}</span>
                <h3 className="text-sm font-semibold text-gray-700">
                  {CATEGORY_LABELS[category] || category}
                </h3>
                <span className="text-xs text-gray-400 font-medium">({findings.length})</span>
              </div>
              <div className="space-y-2">
                {findings.map(f => <FindingItem key={f.id} finding={f} />)}
              </div>
            </section>
          ))}
          {Object.keys(prosByCategory).length === 0 && (
            <p className="text-center text-gray-400 py-8">No positive findings noted.</p>
          )}
        </div>
      )}
    </div>
  );
}