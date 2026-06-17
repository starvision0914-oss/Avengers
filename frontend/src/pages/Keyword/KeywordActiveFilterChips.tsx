import { X } from 'lucide-react';
import { themeStyles, FIELD_LABELS, SALE_STATUS_LABEL, SALE_STATUS_COLOR } from './constants';

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
}

export default function KeywordActiveFilterChips({ dark, filter, onChange }: Props) {
  const s = themeStyles(dark);
  const chips: { label: string; color?: string; onRemove: () => void }[] = [];

  if (filter.saleStatus !== undefined) {
    chips.push({
      label: SALE_STATUS_LABEL[filter.saleStatus] || `상태 ${filter.saleStatus}`,
      color: SALE_STATUS_COLOR[filter.saleStatus],
      onRemove: () => onChange({ ...filter, saleStatus: undefined }),
    });
  }
  if (filter.isSynced === 0) {
    chips.push({
      label: '수정사항만',
      color: '#ff5a2e',
      onRemove: () => onChange({ ...filter, isSynced: undefined }),
    });
  }
  if (filter.search) {
    chips.push({
      label: `검색: ${filter.search}`,
      onRemove: () => onChange({ ...filter, search: '' }),
    });
  }
  if (filter.changedField) {
    chips.push({
      label: `변경: ${FIELD_LABELS[filter.changedField] || filter.changedField}`,
      color: '#ff5a2e',
      onRemove: () => onChange({ ...filter, changedField: undefined }),
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className={`text-[10px] ${s.text3} mr-1`}>적용 중:</span>
      {chips.map((c, i) => (
        <span
          key={i}
          className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[11px] border ${s.border} ${s.text1}`}
          style={c.color ? { borderColor: c.color, color: c.color } : undefined}
        >
          {c.color && <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: c.color }} />}
          {c.label}
          <button onClick={c.onRemove} className="hover:opacity-70" aria-label="제거">
            <X size={11} />
          </button>
        </span>
      ))}
      <button
        onClick={() => onChange({ saleStatus: undefined, isSynced: undefined, search: '', changedField: undefined })}
        className={`text-[10px] ${s.text3} hover:text-blue-500 ml-1`}
      >
        모두 지우기
      </button>
    </div>
  );
}
