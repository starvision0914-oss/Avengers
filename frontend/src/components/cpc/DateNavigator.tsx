import { useRef } from 'react';
import { getKoreanDay, todayStr } from '../../utils/format';
import type { PeriodMode } from '../../types/cpc';

interface Props {
  date: string;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
  onDateChange?: (d: string) => void;
  periodMode?: PeriodMode;
}

export default function DateNavigator({ date, onPrev, onNext, onToday, onDateChange, periodMode = 'daily' }: Props) {
  const isToday = date === todayStr();
  const isFuture = date >= todayStr();
  const pickerRef = useRef<HTMLInputElement>(null);

  const label = periodMode === 'yearly'
    ? `${date.split('-')[0]}년`
    : periodMode === 'monthly'
      ? `${date.split('-')[0]}년 ${date.split('-')[1]}월`
      : `${date} (${getKoreanDay(date)})`;

  return (
    <div className="flex items-center gap-1">
      <button onClick={onPrev} className="w-7 h-7 flex items-center justify-center text-[#666] hover:text-[#333] text-[12px]">◀</button>
      <span
        onClick={() => onDateChange && pickerRef.current?.showPicker?.()}
        className={`text-[12px] font-semibold text-[#333] min-w-[130px] text-center ${onDateChange ? 'cursor-pointer hover:text-[#1a73e8]' : ''}`}
      >
        {label}
      </span>
      {onDateChange && (
        <input ref={pickerRef} type="date" value={date} max={todayStr()}
          onChange={e => { const v = e.target.value; if (v && v <= todayStr() && onDateChange) onDateChange(v); }}
          className="absolute opacity-0 w-0 h-0 pointer-events-none" />
      )}
      <button onClick={onNext} disabled={isFuture} className="w-7 h-7 flex items-center justify-center text-[#666] hover:text-[#333] text-[12px] disabled:opacity-20">▶</button>
      <button onClick={onToday} disabled={isToday} className="ml-1 px-2.5 h-[24px] border border-[#ddd] text-[#666] hover:text-[#333] text-[11px] rounded disabled:opacity-20">오늘</button>
    </div>
  );
}
