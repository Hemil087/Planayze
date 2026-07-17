// iconBg / iconColor / dot are now style values, not Tailwind classes.
// Components apply them with style={{ background: config.iconBg, color: config.iconColor }}

export const SEVERITY_CONFIG = {
  VIOLATION: {
    label:       'Violation',
    icon:        '✕',
    iconBg:      'rgba(248,113,113,0.10)',
    iconColor:   '#F87171',
    dot:         '#F87171',
    cardClass:   'violation',
  },
  TRADEOFF: {
    label:       'Tradeoff',
    icon:        '⚡',
    iconBg:      'rgba(251,191,36,0.10)',
    iconColor:   '#FBBF24',
    dot:         '#FBBF24',
    cardClass:   'tradeoff',
  },
  OBSERVATION: {
    label:       'Positive',
    icon:        '✓',
    iconBg:      'rgba(52,211,153,0.10)',
    iconColor:   '#34D399',
    dot:         '#34D399',
    cardClass:   'positive',
  },
};

export const CATEGORY_LABELS = {
  SPACE_EFFICIENCY: 'Space Efficiency',
  VENTILATION:      'Ventilation & Light',
  PRIVACY:          'Privacy',
  CIRCULATION:      'Circulation',
  ADJACENCY:        'Adjacency',
  SIZE_ADEQUACY:    'Size Adequacy',
};

// Geometric monospace symbols — no emoji
export const CATEGORY_ICONS = {
  SPACE_EFFICIENCY: '◼',
  VENTILATION:      '◈',
  PRIVACY:          '◧',
  CIRCULATION:      '◉',
  ADJACENCY:        '◫',
  SIZE_ADEQUACY:    '◱',
};
