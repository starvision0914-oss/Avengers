import { useEffect, useRef, useState, useMemo } from 'react';
import { Search, X, Check } from 'lucide-react';
import { fetchDistinctValues, type DistinctValue, type FilterableColumn } from '../../api/keyword';
import { themeStyles, fmt } from './constants';

interface Props {
  dark: boolean;
  open: boolean;
  column: FilterableColumn;
  columnLabel: string;
  selectedValues: string[];
  onApply: (values: string[]) => void;
  onClose: () => void;
  anchorRect: DOMRect | null;
}

export default function KeywordColumnFilterPopover({
  dark, open, column, columnLabel, selectedValues, onApply, onClose, anchorRect,
}: Props) {
  const s = themeStyles(dark);
  const [values, setValues] = useState<DistinctValue[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [draft, setDraft] = useState<Set<string>>(new Set(selectedValues));
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    setDraft(new Set(selectedValues));
    setSearch('');
    setLoading(true);
    fetchDistinctValues(column)
      .then(vs => setValues(vs))
      .catch(() => setValues([]))
      .finally(() => setLoading(false));
  }, [open, column]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    window.addEventListener('keydown', onKey);
    setTimeout(() => window.addEventListener('mousedown', onClick), 0);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('mousedown', onClick);
    };
  }, [open, onClose]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return values;
    return values.filter(v => (v.value || '').toLowerCase().includes(q));
  }, [values, search]);

  const allInFilteredChecked = filtered.length > 0 && filtered.every(v => draft.has(v.value));

  const toggleAllFiltered = () => {
    setDraft(prev => {
      const next = new Set(prev);
      if (allInFilteredChecked) filtered.forEach(v => next.delete(v.value));
      else filtered.forEach(v => next.add(v.value));
      return next;
    });
  };

  const toggleOne = (v: string) => {
    setDraft(prev => {
      const next = new Set(prev);
      if (next.has(v)) next.delete(v); else next.add(v);
      return next;
    });
  };

  const handleApply = () => { onApply(Array.from(draft)); onClose(); };
  const handleClear = () => { onApply([]); onClose(); };

  if (!open) return null;

  const top = anchorRect ? anchorRect.bottom + 4 : 100;
  const left = anchorRect ? Math.min(anchorRect.left, window.innerWidth - 320) : 100;

  return (
    <div
      ref={ref}
      className={`fixed z-50 w-[300px] rounded-xl border ${s.card} shadow-2xl flex flex-col`}
      style={{ top, left, maxHeight: 'min(440px, 80vh)' }}
    >
      <div className={`flex items-center justify-between px-3 py-2 border-b ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
        <div className={`text-[12px] font-semibold ${s.text1}`}>{columnLabel} 필터</div>
        <button onClick={onClose} className={`p-1 rounded ${s.cardHover} ${s.text2}`}>
          <X size={14} />
        </button>
      </div>

      <div className="px-3 pt-2">
        <div className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border ${s.inputBg}`}>
          <Search size={12} className={s.text3} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="값 검색..."
            className={`flex-1 bg-transparent outline-none text-[12px] ${s.text1}`}
            autoFocus
          />
        </div>
      </div>

      <label className={`flex items-center gap-2 px-3 py-2 cursor-pointer ${s.cardHover}`}>
        <input
          type="checkbox"
          checked={allInFilteredChecked}
          onChange={toggleAllFiltered}
          className="cursor-pointer accent-blue-600"
        />
        <span className={`text-[12px] font-semibold ${s.text1}`}>
          {search ? `검색 결과 전체 (${fmt(filtered.length)})` : `전체 (${fmt(values.length)})`}
        </span>
      </label>

      <div className="flex-1 overflow-y-auto px-1 pb-1 min-h-0">
        {loading ? (
          <div className={`px-3 py-4 text-[12px] text-center ${s.text3}`}>로딩...</div>
        ) : filtered.length === 0 ? (
          <div className={`px-3 py-4 text-[12px] text-center ${s.text3}`}>일치하는 값 없음</div>
        ) : (
          filtered.map(v => {
            const checked = draft.has(v.value);
            return (
              <label
                key={v.value}
                className={`flex items-center gap-2 px-3 py-1.5 rounded ${s.cardHover} cursor-pointer`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleOne(v.value)}
                  className="cursor-pointer accent-blue-600"
                />
                <span className={`flex-1 text-[12px] truncate ${checked ? s.text1 : s.text2}`} title={v.value}>
                  {v.value}
                </span>
                <span className={`text-[10px] ${s.text3}`}>{fmt(v.count)}</span>
              </label>
            );
          })
        )}
      </div>

      <div className={`flex items-center gap-2 px-3 py-2 border-t ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
        <button
          onClick={handleClear}
          className={`px-2 py-1 rounded text-[11px] ${s.text3} hover:underline`}
        >
          필터 해제
        </button>
        <span className={`ml-auto text-[10px] ${s.text3}`}>{fmt(draft.size)}개 선택</span>
        <button
          onClick={handleApply}
          className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold flex items-center gap-1"
        >
          <Check size={12} /> 적용
        </button>
      </div>
    </div>
  );
}
