import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, RateLimitError } from '../../utils/api';
import ChatMessage from './ChatMessage';
import { C, F } from '../../utils/tokens';

const SUGGESTIONS = [
  'Does a queen bed fit in Bedroom 3?',
  'What rooms get morning sun?',
  'How do I get from Kitchen to Bedroom 1?',
  'What is the area of the living room?',
];

export default function ChatPanel({ planId }) {
  const [messages, setMessages] = useState([]);
  const [input,    setInput]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    const userMsg = { role: 'user', content: msg };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage(planId, updated);
      setMessages([...updated, { role: 'assistant', content: res.reply, tools: res.tool_calls_made }]);
    } catch (err) {
      const errContent = err instanceof RateLimitError
        ? '⏳ Daily chat limit reached. This is a portfolio project with limited API credits — please try again tomorrow.'
        : `Something went wrong: ${err.message}`;
      setMessages([...updated, { role: 'assistant', content: errContent }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: C.bg }}>

      {/* ── HEADER ─────────────────────────────────────────────────────────── */}
      <div style={{ padding: '12px 15px', borderBottom: `1px solid ${C.bd}`, background: C.su, flexShrink: 0 }}>
        <div style={{ fontFamily: F.display, fontSize: 12, fontWeight: 600, color: C.tx }}>
          Chat with your floor plan
        </div>
        <div style={{ fontSize: 10, color: C.fn, marginTop: 2 }}>Geometry tools — not guesswork</div>
      </div>

      {/* ── MESSAGES ───────────────────────────────────────────────────────── */}
      <div className="custom-scrollbar" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Suggestions (shown until first message is sent) */}
        {messages.length === 0 && (
          <div style={{ paddingTop: 10 }}>
            <p style={{ fontSize: 10, color: C.fn, textAlign: 'center', marginBottom: 9 }}>Try asking</p>
            {SUGGESTIONS.map((q) => (
              <button key={q} className="chat-suggest" onClick={() => handleSend(q)}>{q}</button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, paddingLeft: 2 }}>
            <div className="bounce-0" style={{ width: 6, height: 6, borderRadius: '50%', background: C.ac }} />
            <div className="bounce-1" style={{ width: 6, height: 6, borderRadius: '50%', background: C.ac, opacity: 0.7 }} />
            <div className="bounce-2" style={{ width: 6, height: 6, borderRadius: '50%', background: C.ac, opacity: 0.4 }} />
            <span style={{ fontSize: 11, color: C.fn }}>Checking floor plan data...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── INPUT ──────────────────────────────────────────────────────────── */}
      <div style={{ padding: 10, borderTop: `1px solid ${C.bd}`, background: C.su, flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 7 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask about rooms, sizes, furniture..."
            className="chat-input"
            disabled={loading}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            style={{
              padding: '9px 12px', background: C.ac,
              border: 'none', borderRadius: 10, cursor: 'pointer', flexShrink: 0,
              opacity: (loading || !input.trim()) ? 0.3 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#0A0C14" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
