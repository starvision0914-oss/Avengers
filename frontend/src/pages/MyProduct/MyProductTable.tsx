import { Eye, ArrowUp, ArrowDown, ArrowUpDown, Filter as FilterIcon, BadgeCheck } from 'lucide-react';
import type { MyProductItem, MySortColumn, SortOrder, FilterableColumn } from '../../api/myproduct';
import { themeStyles, fmt, MARKETS } from '../Ownerclan/constants';
import OwnerclanHoverImage from '../Ownerclan/OwnerclanHoverImage';
import CategoryPath from '../../components/CategoryPath';

interface Props {
  dark: boolean;
  items: MyProductItem[];
  onSelect: (id: number) => void;
  sort?: MySortColumn;
  order: SortOrder;
  onSort: (col: MySortColumn) => void;
  selectedIds: Set<number>;
  onToggleId: (id: number) => void;
  onToggleAll: () => void;
  filterCol?: FilterableColumn;
  filterVals: string[];
  onOpenFilter: (col: FilterableColumn, label: string, anchor: DOMRect) => void;
}

export default function MyProductTable({
  dark, items, onSelect, sort, order, onSort,
  selectedIds, onToggleId, onToggleAll,
  filterCol, filterVals, onOpenFilter,
}: Props) {
  const s = themeStyles(dark);
  const allChecked = items.length > 0 && items.every(p => selectedIds.has(p.id));
  const someChecked = !allChecked && items.some(p => selectedIds.has(p.id));

  const SortIcon = ({ col }: { col: MySortColumn }) => {
    if (sort !== col) return <ArrowUpDown size={11} className="opacity-40" />;
    return order === 'asc'
      ? <ArrowUp size={11} className="text-blue-500" />
      : <ArrowDown size={11} className="text-blue-500" />;
  };

  const SortableHeader = ({ col, label, align = 'left' }: { col: MySortColumn; label: string; align?: 'left' | 'right' | 'center' }) => (
    <button type="button" onClick={() => onSort(col)}
      className={`flex items-center gap-1 font-medium select-none cursor-pointer ${
        align === 'right' ? 'ml-auto' : align === 'center' ? 'mx-auto' : ''
      } ${sort === col ? 'text-blue-500' : ''} hover:text-blue-500 transition-colors`}>
      {label}
      <SortIcon col={col} />
    </button>
  );

  const FilterButton = ({ col, label }: { col: FilterableColumn; label: string }) => {
    const active = filterCol === col && filterVals.length > 0;
    return (
      <button type="button"
        onClick={(e) => { e.stopPropagation(); onOpenFilter(col, label, (e.currentTarget as HTMLElement).getBoundingClientRect()); }}
        className={`p-0.5 rounded hover:bg-blue-500/20 ${active ? 'text-blue-500' : s.text3}`}
        title={active ? `${label} 필터 적용중 (${filterVals.length}개)` : `${label} 필터`}>
        <FilterIcon size={11} fill={active ? 'currentColor' : 'none'} />
      </button>
    );
  };

  return (
    <div className={`rounded-xl border ${s.card} overflow-hidden`}>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead className={`${dark ? 'bg-[#0f1117]' : 'bg-gray-50'} sticky top-0`}>
            <tr className={s.text2}>
              <th className="px-3 py-2 text-center font-medium w-9">
                <input type="checkbox" checked={allChecked}
                  ref={el => { if (el) el.indeterminate = someChecked; }}
                  onChange={onToggleAll} onClick={e => e.stopPropagation()}
                  className="cursor-pointer accent-blue-600" />
              </th>
              <th className="px-3 py-2 text-left font-medium w-12">이미지</th>
              <th className="px-3 py-2 text-left font-medium w-36"><SortableHeader col="my_product_code" label="나의 W코드" /></th>
              <th className="px-3 py-2 text-left font-medium w-28"><SortableHeader col="source_product_code" label="원본 W코드" /></th>
              <th className="px-3 py-2 text-left font-medium w-56">
                <div className="flex items-center gap-1">
                  <SortableHeader col="category_code" label="카테고리" />
                  <FilterButton col="category_name" label="카테고리" />
                </div>
              </th>
              <th className="px-3 py-2 text-left font-medium">상품명</th>
              <th className="px-3 py-2 text-right font-medium w-24"><SortableHeader col="ownerclan_price" label="판매가" align="right" /></th>
              <th className="px-3 py-2 text-right font-medium w-24"><SortableHeader col="market_price" label="마켓가" align="right" /></th>
              <th className="px-3 py-2 text-right font-medium w-20"><SortableHeader col="shipping_fee" label="배송비" align="right" /></th>
              <th className="px-3 py-2 text-center font-medium w-32">마켓</th>
              <th className="px-3 py-2 text-center font-medium w-16">수정</th>
              <th className="px-3 py-2 text-center font-medium w-12"></th>
            </tr>
          </thead>
          <tbody className={`divide-y ${s.divider}`}>
            {items.map((p) => {
              const checked = selectedIds.has(p.id);
              const mod = !!p.is_modified;
              return (
                <tr key={p.id}
                  className={`${s.rowHover} cursor-pointer transition-colors ${mod ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-transparent'} ${checked ? (dark ? 'bg-blue-900/20' : 'bg-blue-50') : ''}`}
                  onClick={() => onSelect(p.id)}>
                  <td className="px-3 py-2 text-center" onClick={e => { e.stopPropagation(); onToggleId(p.id); }}>
                    <input type="checkbox" checked={checked}
                      onChange={() => onToggleId(p.id)}
                      onClick={e => e.stopPropagation()}
                      className="cursor-pointer accent-blue-600" />
                  </td>
                  <td className="px-3 py-2">
                    <OwnerclanHoverImage src={p.image_small || p.image_large} previewSrc={p.image_large || p.image_small} thumbnailSize={36} />
                  </td>
                  <td className={`px-3 py-2 font-mono text-[11px] ${s.text1}`}>{p.my_product_code}</td>
                  <td className={`px-3 py-2 font-mono text-[11px] ${s.text2}`}>{p.source_product_code}</td>
                  <td className="px-3 py-2 max-w-[220px]">
                    <CategoryPath path={p.category_name} dark={dark} compact code={p.category_code} />
                  </td>
                  <td className={`px-3 py-2 ${s.text1} max-w-md`}>
                    <div className="truncate" title={p.product_name}>{p.product_name || '-'}</div>
                  </td>
                  <td className={`px-3 py-2 text-right ${s.text2}`}>{fmt(p.ownerclan_price)}</td>
                  <td className={`px-3 py-2 text-right ${s.text2}`}>{fmt(p.market_price)}</td>
                  <td className={`px-3 py-2 text-right ${s.text2}`}>{fmt(p.shipping_fee)}</td>
                  <td className="px-3 py-2">
                    <div className="flex items-center justify-center gap-1">
                      {MARKETS.map(m => {
                        const v = (p as any)[m.key];
                        const on = v && v !== '' && v !== '0' && v !== 'N';
                        return (
                          <span key={m.key} title={`${m.label}: ${on ? '노출' : '미노출'}`}
                            className="w-2.5 h-2.5 rounded-full"
                            style={{ backgroundColor: on ? m.color : 'rgba(120,120,120,0.25)' }} />
                        );
                      })}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {mod ? (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-500 text-[10px] font-bold">
                        <BadgeCheck size={10} /> 수정
                      </span>
                    ) : (
                      <span className={`text-[10px] ${s.text3}`}>원본</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <Eye size={14} className={s.text3} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
