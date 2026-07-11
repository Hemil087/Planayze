import { useState, useRef, useCallback } from 'react';

export default function UploadZone({ onFileSelected, disabled }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  }, [onFileSelected]);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`
        relative border-2 border-dashed rounded-2xl p-14 text-center cursor-pointer
        transition-all duration-300
        ${dragOver
          ? 'border-brand-500 bg-brand-50 scale-[1.02] shadow-lg shadow-brand-100'
          : 'border-gray-200 hover:border-brand-400 hover:bg-gray-50/50'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,application/pdf"
        onChange={(e) => e.target.files[0] && onFileSelected(e.target.files[0])}
        className="hidden"
        disabled={disabled}
      />
      <div className="space-y-4">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-brand-50 flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-brand-600">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <div>
          <p className="text-base font-semibold text-gray-700">
            Drop your floor plan here
          </p>
          <p className="text-sm text-gray-400 mt-1">
            or <span className="text-brand-600 font-medium">browse files</span>
          </p>
        </div>
        <p className="text-xs text-gray-400">
          JPEG, PNG, or PDF — up to 20 MB
        </p>
      </div>
    </div>
  );
}