import { useState } from 'react';
import { Search, Filter } from 'lucide-react';
import type { ChangedFieldCounts } from '../../api/keyword';
import { themeStyles, FIELD_LABELS } from './constants';

interface FilterState {
  saleStatus?: number;
  isSynced?: number;
  search: string;
  changedField?: string;
}

interface Props {
  dark: boolean;
  filter: FilterState;
  onChange: (next: FilterState) => void;
  changedFieldCounts: ChangedFieldCounts;
}

export default function KeywordFilterPanel({ dark, filter, onChange, changedFieldCounts }: Props) {
  const s = themeStyles(dark);
  const [searchInput, setSearchInput] = useState(filter.search);
  const [fieldQuery, setFieldQuery] = useState('');

  const set = (patch: Partial<FilterState>) => onChange({ ...filter, ...patch });

  const matchedFields = Object.entries(changedFieldCounts)
    .filter(([k]) => {
      if (!fieldQuery) return true;
      const label = FIELD_LABELS[k] || k;
      return label.includes(fieldQuery) || k.includes(fieldQuery.toLowerCase());
    })
    .sort((a, b) => b[1] - a[1]);

  return (
    <aside className={`w-full lg:w-[240px] shrink-0 rounded-xl border ${s.card} p-4 space-y-5 lg:sticky lg:top-4 self-start`}>
      <div className="flex items-center gap-2">
        <Filter size={14} className={s.text2} />
        <h3 className={`text-[12px] font-bold ${s.text1}`}>필터</h3>
        <button
          onClick={() => onChange({ saleStatus: undefined, isSynced: undefined, search: '', changedField: undefined })}
          className={`ml-auto text-[10px] ${s.text3} hover:text-blue-500`}
        >
          초기화
        </button>
      </div>

      <div>
        <label className={`block text-[11px] font-semibold ${s.text2} mb-1.5`}>W코드 / 상품명 검색</label>
        <form
          onSubmit={(e) => { e.preventDefault(); set({ search: searchInput.trim() }); }}
          className="relative"
        >
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="검색..."
            className={`w-full text-[12px] px-3 py-2 pl-8 rounded-lg border ${s.inputBg} focus:outline-none focus:ring-1 focus:ring-blue-500`}
          />
          <Search size={14} className={`absolute left-2.5 top-1/2 -translate-y-1/2 ${s.text3}`} />
        </form>
      </div>

      <div>
        <label className={`block text-[11px] font-semibold ${s.text2} mb-1.5`}>판매 상태</label>
        <div className="space-y-1">
          {[
            { v: undefined, label: '전체' },
            { v: 1, label: '판매중', color: '#16a34a' },
            { v: 2, label: '품절', color: '#f59e0b' },
            { v: 3, label: '단종', color: '#dc2626' },
          ].map(opt => (
            <label
              key={opt.label}
              className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-[12px] ${
                filter.saleStatus === opt.v ? (dark ? 'bg-[#2a2b35]' : 'bg-gray-100') : ''
              } ${s.cardHover}`}
            >
              <input
                type="radio"
                name="saleStatus"
                checked={filter.saleStatus === opt.v}
                onChange={() => set({ saleStatus: opt.v })}
                className="accent-blue-500"
              />
              {opt.color && <span className="w-2 h-2 rounded-full" style={{ backgroundColor: opt.color }} />}
              <span className={s.text1}>{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className={`flex items-center gap-2 text-[11px] font-semibold ${s.text2} cursor-pointer`}>
          <input
            type="checkbox"
            checked={filter.isSynced === 0}
            onChange={(e) => set({ isSynced: e.target.checked ? 0 : undefined })}
            className="accent-orange-500"
          />
          수정사항만 보기
          {filter.isSynced === 0 && <span className="ml-auto text-[10px] text-orange-500">●</span>}
        </label>
      </div>

      <div>
        <label className={`block text-[11px] font-semibold ${s.text2} mb-1.5`}>변경 필드</label>
        <input
          type="text"
          value={fieldQuery}
          onChange={(e) => setFieldQuery(e.target.value)}
          placeholder="필드 검색..."
          className={`w-full text-[12px] px-2.5 py-1.5 rounded-lg border mb-2 ${s.inputBg} focus:outline-none focus:ring-1 focus:ring-blue-500`}
        />
        <div className={`max-h-[260px] overflow-y-auto space-y-0.5 -mx-1 px-1`}>
          <button
            onClick={() => set({ changedField: undefined })}
            className={`w-full text-left px-2 py-1.5 rounded text-[11px] ${
              !filter.changedField ? (dark ? 'bg-[#2a2b35] text-white' : 'bg-gray-100 text-gray-900') : `${s.text2} ${s.cardHover}`
            }`}
          >
            전체 ({Object.values(changedFieldCounts).reduce((a, b) => a + b, 0)})
          </button>
          {matchedFields.map(([k, count]) => (
            <button
              key={k}
              onClick={() => set({ changedField: k })}
              className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-[11px] ${
                filter.changedField === k ? 'bg-orange-500/15 text-orange-500' : `${s.text2} ${s.cardHover}`
              }`}
            >
              <span className="truncate">{FIELD_LABELS[k] || k}</span>
              <span className={`shrink-0 ml-2 text-[10px] ${filter.changedField === k ? 'text-orange-500' : s.text3}`}>{count}</span>
            </button>
          ))}
          {matchedFields.length === 0 && (
            <div className={`text-[11px] ${s.text3} px-2 py-3 text-center`}>변경된 필드가 없습니다</div>
          )}
        </div>
      </div>
    </aside>
  );
}
