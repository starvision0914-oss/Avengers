import type { PeriodMode } from '../../types/cpc';

const OPTIONS: { key: PeriodMode; label: string }[] = [
  { key: 'daily', label: '일간' },
  { key: 'monthly', label: '월간' },
  { key: 'yearly', label: '년간' },
  { key: 'range', label: '기간별' },
];

interface Props {
  value: PeriodMode;
  onChange: (mode: PeriodMode) => void;
}

export default function PeriodSelector({ value, onChange }: Props) {
  return (
    <div className="inline-flex rounded overflow-hidden border border-[#d0d0d0] text-[11px]">
      {OPTIONS.map(o => (
        <button key={o.key} onClick={() => onChange(o.key)}
          className={`px-2.5 py-[3px] font-semibold transition-colors ${
            value === o.key ? 'bg-[#333] text-white' : 'bg-white text-[#666] hover:bg-[#f0f0f0]'
          }`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
