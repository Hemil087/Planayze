import { C, F } from '../../utils/tokens';
import { SEVERITY_CONFIG } from '../../utils/constants';

export default function FindingItem({ finding }) {
  const config   = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.OBSERVATION;
  const cardClass = config.cardClass; // 'violation' | 'tradeoff' | 'positive'

  return (
    <div className={`finding-card ${cardClass}`}>
      <div style={{ display: 'flex', gap: 11 }}>
        {/* Severity icon */}
        <div style={{
          width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: config.iconBg, color: config.iconColor,
          fontSize: 10, fontWeight: 700,
        }}>
          {config.icon}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Title */}
          <div style={{ fontSize: 13, fontWeight: 600, color: C.tx, marginBottom: 4 }}>
            {finding.title}
          </div>

          {/* Detail */}
          <div style={{ fontSize: 12, color: C.mu, lineHeight: 1.65 }}>
            {finding.detail}
          </div>

          {/* Room tags + Rule ID */}
          {(finding.room_names?.length > 0 || finding.rule_id) && (
            <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              {finding.room_names?.map((room) => (
                <span key={room} style={{
                  fontFamily: F.mono, fontSize: 10,
                  padding: '2px 7px', borderRadius: 4,
                  background: C.acd, color: C.ac,
                  border: '1px solid rgba(240,165,0,0.15)',
                }}>
                  {room}
                </span>
              ))}
              {finding.rule_id && (
                <span style={{
                  fontFamily: F.mono, fontSize: 9,
                  padding: '2px 6px', borderRadius: 4,
                  background: '#0B1520', color: C.fn,
                  border: `1px solid ${C.bd}`,
                  marginLeft: 'auto',
                }}>
                  {finding.rule_id}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
