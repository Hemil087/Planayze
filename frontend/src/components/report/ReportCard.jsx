import { useState } from 'react';
import ScoreBadge from './ScoreBadge';
import FindingItem from './FindingItem';
import { SEVERITY_CONFIG, CATEGORY_LABELS, CATEGORY_ICONS } from '../../utils/constants';
import { C, F } from '../../utils/tokens';

function groupByCategory(findings) {
  const groups = {};
  for (const f of findings) {
    (groups[f.category] = groups[f.category] || []).push(f);
  }
  return groups;
}

function StatDot({ count, color, label }) {
  if (!count) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      <span style={{ fontSize: 11, color: C.mu }}>
        {count} {label}{count > 1 ? 's' : ''}
      </span>
    </div>
  );
}

function CategoryHeader({ category, count }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9 }}>
      <span style={{ fontFamily: F.mono, fontSize: 11, color: C.fn }}>
        {CATEGORY_ICONS[category] || '◆'}
      </span>
      <span style={{ fontSize: 11, fontWeight: 600, color: C.mu, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        {CATEGORY_LABELS[category] || category}
      </span>
      <span style={{ fontSize: 11, color: C.fn }}>({count})</span>
    </div>
  );
}

export default function ReportCard({ report }) {
  const [activeTab, setActiveTab] = useState('issues');
  if (!report) return null;

  const violationCount = report.cons?.filter(f => f.severity === 'VIOLATION').length || 0;
  const tradeoffCount  = report.cons?.filter(f => f.severity === 'TRADEOFF').length  || 0;
  const consByCategory = groupByCategory(report.cons || []);
  const prosByCategory = groupByCategory(report.pros || []);

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

      {/* ── SCORE + SUMMARY ───────────────────────────────────────────────── */}
      <div style={{
        background: C.su, border: `1px solid ${C.bd}`, borderRadius: 14,
        padding: '20px 22px', display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap',
      }}>
        <ScoreBadge score={report.overall_score} />
        <div style={{ flex: 1, minWidth: 180 }}>
          <div style={{ fontFamily: F.display, fontSize: 17, fontWeight: 600, color: C.tx, marginBottom: 10 }}>
            Analysis Report
          </div>
          <p style={{ fontSize: 12, color: C.mu, lineHeight: 1.7 }}>{report.summary_text}</p>
          <div style={{ display: 'flex', gap: 14, marginTop: 12, flexWrap: 'wrap' }}>
            <StatDot count={violationCount}      color={C.re} label="violation" />
            <StatDot count={tradeoffCount}       color={C.ye} label="tradeoff" />
            <StatDot count={report.pros?.length} color={C.gn} label="positive" />
          </div>
        </div>
      </div>

      {/* ── TABS ──────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 6 }}>
        {[
          { id: 'issues',    label: `Issues (${report.cons?.length || 0})` },
          { id: 'positives', label: `Positives (${report.pros?.length || 0})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pz-tab ${activeTab === tab.id ? 'active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── ISSUES ────────────────────────────────────────────────────────── */}
      {activeTab === 'issues' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {Object.entries(consByCategory).map(([category, findings]) => (
            <section key={category}>
              <CategoryHeader category={category} count={findings.length} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {findings.map(f => <FindingItem key={f.id} finding={f} />)}
              </div>
            </section>
          ))}
          {Object.keys(consByCategory).length === 0 && (
            <p style={{ textAlign: 'center', color: C.fn, padding: '32px 0', fontSize: 13 }}>
              No issues found — this is a strong floor plan.
            </p>
          )}
        </div>
      )}

      {/* ── POSITIVES ─────────────────────────────────────────────────────── */}
      {activeTab === 'positives' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {Object.entries(prosByCategory).map(([category, findings]) => (
            <section key={category}>
              <CategoryHeader category={category} count={findings.length} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {findings.map(f => <FindingItem key={f.id} finding={f} />)}
              </div>
            </section>
          ))}
          {Object.keys(prosByCategory).length === 0 && (
            <p style={{ textAlign: 'center', color: C.fn, padding: '32px 0', fontSize: 13 }}>
              No positive findings noted.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
