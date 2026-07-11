export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
        ${isUser
          ? 'bg-brand-600 text-white rounded-br-md'
          : 'bg-gray-100 text-gray-800 rounded-bl-md'
        }`}
      >
        <p>{message.content}</p>
        {message.tools?.length > 0 && (
          <div className="flex gap-1 mt-1.5 flex-wrap">
            {message.tools.map((t, i) => (
              <span key={i} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-black/10">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}