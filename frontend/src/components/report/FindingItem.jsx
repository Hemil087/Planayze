import { SEVERITY_CONFIG, CATEGORY_LABELS } from '../../utils/constants';

export default function FindingItem({ finding }) {
  const config = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.OBSERVATION;
  const category = CATEGORY_LABELS[finding.category] || finding.category;

  return (
    <div className={`rounded-xl border p-4 ${config.color} transition-all hover:shadow-sm`}>
      <div className="flex items-start gap-3">
        <span className="text-lg mt-0.5 shrink-0">{config.icon}</span>
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-sm">{finding.title}</h4>
            <span className="text-[10px] font-medium uppercase tracking-wider opacity-60">
              {category}
            </span>
          </div>
          <p className="text-sm mt-1 opacity-80 leading-relaxed">
            {finding.detail}
          </p>
          {finding.room_names?.length > 0 && (
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {finding.room_names.map((room) => (
                <span key={room} className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-white/50 border border-current/10">
                  {room}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}