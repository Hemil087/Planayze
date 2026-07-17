// Planalyze design tokens — import as { C, F } in every component

export const C = {
  bg:  '#070D1A',              // page background
  su:  '#0F1929',              // card / surface
  su2: '#152236',              // raised surface, assistant bubbles
  bd:  '#1D2E45',              // border
  bh:  '#2A3D56',              // border hover
  ac:  '#F0A500',              // amber gold — signature accent
  acd: 'rgba(240,165,0,0.10)',  // amber dim fill
  tx:  '#DDE6F5',              // primary text
  mu:  '#7090B0',              // muted text
  fn:  '#3A5070',              // faint / disabled text
  re:  '#F87171',              // violation / danger
  ye:  '#FBBF24',              // tradeoff / warning
  gn:  '#34D399',              // positive / success
};

export const F = {
  display: "'Space Grotesk', system-ui, sans-serif",
  body:    "'Inter', system-ui, sans-serif",
  mono:    "'JetBrains Mono', monospace",
};
