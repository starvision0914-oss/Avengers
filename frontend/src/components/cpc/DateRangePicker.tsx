interface Props {
  startDate: string;
  endDate: string;
  onStartChange: (d: string) => void;
  onEndChange: (d: string) => void;
  onSearch: () => void;
}

export default function DateRangePicker({ startDate, endDate, onStartChange, onEndChange, onSearch }: Props) {
  return (
    <div className="flex items-center gap-1.5 text-[12px]">
      <input type="date" value={startDate} onChange={e => onStartChange(e.target.value)}
        className="bg-white border border-[#ddd] rounded px-1.5 py-[2px] text-[12px]" />
      <span className="text-[#999]">~</span>
      <input type="date" value={endDate} onChange={e => onEndChange(e.target.value)}
        className="bg-white border border-[#ddd] rounded px-1.5 py-[2px] text-[12px]" />
      <button onClick={onSearch} className="px-2.5 h-[24px] bg-[#1a73e8] text-white text-[11px] font-semibold rounded hover:bg-[#1557b0]">조회</button>
    </div>
  );
}
