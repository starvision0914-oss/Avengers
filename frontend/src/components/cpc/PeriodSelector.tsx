import type { PeriodMode, PeriodPreset } from '../../utils/periodRange';
import { yesterdayStr } from '../../utils/periodRange';
import { todayStr } from '../../utils/format';

// Overview/G마켓/스마트스토어/11번가 4개 대시보드 공통 기간 버튼.
// 반드시 이 컴포넌트 + utils/periodRange의 계산 함수만 사용해야 페이지 간 "같은 기간 = 같은 값"이 보장된다.
const BUTTONS: { key: PeriodPreset; label: string }[] = [
  { key: 'today', label: '오늘' },
  { key: 'yesterday', label: '어제' },
  { key: 'monthly', label: '당월' },
  { key: 'recent30', label: '한달' },
  { key: 'yearly', label: '1년' },
  { key: 'range', label: '기간별' },
];

interface Props {
  mode: PeriodMode;
  date: string;
  onPick: (preset: PeriodPreset) => void;
}

export default function PeriodSelector({ mode, date, onPick }: Props) {
  const isActive = (key: PeriodPreset) => {
    if (key === 'today') return mode === 'daily' && date === todayStr();
    if (key === 'yesterday') return mode === 'daily' && date === yesterdayStr();
    if (key === 'monthly') return mode === 'monthly';
    if (key === 'yearly') return mode === 'yearly';
    if (key === 'recent30') return mode === 'recent30';
    return mode === 'range';
  };

  return (
    <div className="inline-flex rounded overflow-hidden border border-[#d0d0d0] text-[11px]">
      {BUTTONS.map(o => (
        <button key={o.key} onClick={() => onPick(o.key)}
          className={`px-2.5 py-[3px] font-semibold transition-colors ${
            isActive(o.key) ? 'bg-[#333] text-white' : 'bg-white text-[#666] hover:bg-[#f0f0f0]'
          }`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
