export function scoreColor(score) {
  if (score >= 70) return 'text-score-good';
  if (score >= 40) return 'text-score-mid';
  return 'text-score-bad';
}

export function scoreBgColor(score) {
  if (score >= 70) return 'bg-green-50 border-green-200';
  if (score >= 40) return 'bg-amber-50 border-amber-200';
  return 'bg-red-50 border-red-200';
}

export function scoreLabel(score) {
  if (score >= 80) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Fair';
  if (score >= 30) return 'Below Average';
  return 'Poor';
}