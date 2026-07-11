import { SEVERITY_CONFIG, CATEGORY_LABELS } from '../../utils/constants';

export default function FindingItem({ finding }) {
  const config = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.OBSERVATION;

  return (
    <div className={`group rounded-lg border p-4 transition-all duration-200 hover:shadow-md ${config.border}`}>
      <div className="flex items-start gap-3">
        <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-sm ${config.iconBg}`}>
          {config.icon}
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="font-semibold text-sm text-gray-900">{finding.title}</h4>
          <p className="text-sm text-gray-500 mt-1 leading-relaxed">
            {finding.detail}
          </p>
          {finding.room_names?.length > 0 && (
            <div className="flex gap-1.5 mt-2.5 flex-wrap">
              {finding.room_names.map((room) => (
                <span key={room} className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 border border-gray-200">
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