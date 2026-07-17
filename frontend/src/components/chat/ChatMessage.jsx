import { C, F } from '../../utils/tokens';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className="animate-slide-up" style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <div style={{
        maxWidth: '85%',
        padding: '9px 13px',
        fontSize: 12,
        lineHeight: 1.65,
        ...(isUser
          ? {
              background: C.ac,
              color: '#0A0C14',
              fontWeight: 500,
              borderRadius: '12px 12px 3px 12px',
            }
          : {
              background: C.su2,
              color: C.tx,
              border: `1px solid ${C.bd}`,
              borderRadius: '12px 12px 12px 3px',
            }
        ),
      }}>
        <p style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>

        {/* Tool call badges — shown on assistant messages */}
        {!isUser && message.tools?.length > 0 && (
          <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
            {[...new Set(message.tools)].map((t, i) => (
              <span key={i} style={{
                fontFamily: F.mono, fontSize: 9,
                padding: '2px 6px', borderRadius: 4,
                background: C.acd, color: C.ac,
              }}>
                ⚙ {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
