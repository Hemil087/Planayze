import { useState, useRef, useCallback } from 'react';
import { C, F } from '../../utils/tokens';

export default function UploadZone({ onFileSelected, disabled }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  }, [onFileSelected]);

  const handleDragOver  = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
      style={{
        padding: '44px 28px',
        textAlign: 'center',
        opacity: disabled ? 0.4 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,application/pdf"
        onChange={(e) => e.target.files[0] && onFileSelected(e.target.files[0])}
        style={{ display: 'none' }}
        disabled={disabled}
      />

      {/* Upload icon */}
      <div style={{
        width: 50, height: 50, margin: '0 auto 15px',
        background: C.acd, borderRadius: 13,
        border: '1px solid rgba(240,165,0,0.20)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#F0A500" strokeWidth="1.75">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </div>

      <p style={{ fontFamily: F.display, fontSize: 14, fontWeight: 600, color: C.tx, marginBottom: 5 }}>
        Drop your floor plan here
      </p>
      <p style={{ fontSize: 13, color: C.mu }}>
        or{' '}
        <span style={{ color: C.ac, fontWeight: 500 }}>browse files</span>
      </p>
      <p style={{ fontFamily: F.mono, fontSize: 10, color: C.fn, marginTop: 10 }}>
        JPEG · PNG · PDF — up to 20 MB
      </p>
    </div>
  );
}
