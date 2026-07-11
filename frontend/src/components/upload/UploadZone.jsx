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
        relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
        transition-all duration-200
        ${dragOver ? 'border-brand-600 bg-brand-50 scale-[1.01]' : 'border-gray-300 hover:border-brand-500 hover:bg-gray-50'}
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
      <div className="space-y-3">
        <div className="text-4xl">📐</div>
        <p className="text-lg font-medium text-gray-700">
          Drop your floor plan here
        </p>
        <p className="text-sm text-gray-500">
          JPEG, PNG, or PDF — up to 20 MB
        </p>
      </div>
    </div>
  );
}