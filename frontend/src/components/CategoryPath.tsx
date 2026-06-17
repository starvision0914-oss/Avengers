import { ChevronRight } from 'lucide-react';

interface Props {
  path: string | null | undefined;
  dark: boolean;
  compact?: boolean;
  code?: string | null;
}

export default function CategoryPath({ path, dark, compact = false, code }: Props) {
  const raw = (path || '').trim();
  if (!raw) {
    return <span className={dark ? 'text-gray-600' : 'text-gray-400'}>—</span>;
  }
  const parts = raw.split('>').map(s => s.trim()).filter(Boolean);
  const tooltip = code ? `${code} | ${raw}` : raw;

  const levelStyle = (i: number) => {
    if (i === 0) {
      return dark
        ? 'text-gray-100 font-semibold'
        : 'text-gray-900 font-semibold';
    }
    if (i === 1) {
      return dark ? 'text-gray-300' : 'text-gray-700';
    }
    if (i === 2) {
      return dark ? 'text-gray-400' : 'text-gray-500';
    }
    return dark ? 'text-gray-500' : 'text-gray-400';
  };

  const baseSize = compact ? 'text-[10px]' : 'text-[11px]';
  const firstSize = compact ? 'text-[10px]' : 'text-[11px]';

  return (
    <div
      title={tooltip}
      className="inline-flex items-center gap-0.5 max-w-full overflow-hidden whitespace-nowrap leading-tight"
    >
      {parts.map((p, i) => (
        <span key={i} className="inline-flex items-center gap-0.5 min-w-0">
          {i > 0 && (
            <ChevronRight
              size={compact ? 9 : 10}
              className={dark ? 'text-gray-600 shrink-0' : 'text-gray-400 shrink-0'}
            />
          )}
          <span
            className={`${i === 0 ? firstSize : baseSize} ${levelStyle(i)} truncate`}
          >
            {p}
          </span>
        </span>
      ))}
    </div>
  );
}
