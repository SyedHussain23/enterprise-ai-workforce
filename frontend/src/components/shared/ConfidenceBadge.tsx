import clsx from 'clsx';

interface Props {
  score: number;
  showLabel?: boolean;
}

export function ConfidenceBadge({ score, showLabel = true }: Props) {
  const { label, color } = getLevel(score);

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        color,
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
      {showLabel ? `${label} ${score}%` : `${score}%`}
    </span>
  );
}

function getLevel(score: number) {
  if (score >= 85) return { label: 'High', color: 'bg-emerald-50 text-emerald-700' };
  if (score >= 65) return { label: 'Medium', color: 'bg-amber-50 text-amber-700' };
  return { label: 'Low', color: 'bg-red-50 text-red-700' };
}
