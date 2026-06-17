import { Package, BadgeCheck } from 'lucide-react';
import type { MyProductItem } from '../../api/myproduct';
import { themeStyles, fmt, MARKETS } from '../Ownerclan/constants';

interface Props {
  dark: boolean;
  items: MyProductItem[];
  onSelect: (id: number) => void;
}

export default function MyProductGrid({ dark, items, onSelect }: Props) {
  const s = themeStyles(dark);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
      {items.map(p => {
        const mod = !!p.is_modified;
        return (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`text-left rounded-xl border ${s.card} overflow-hidden hover:scale-[1.02] transition-all relative ${mod ? 'ring-1 ring-green-500/50' : ''}`}
          >
            <div className={`relative aspect-square ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
              {p.image_large ? (
                <img
                  src={p.image_large}
                  alt={p.product_name}
                  loading="lazy"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Package size={36} className={s.text3} />
                </div>
              )}
              {mod && (
                <div className="absolute top-2 right-2 inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-green-500 text-white text-[10px] font-bold">
                  <BadgeCheck size={10} /> 수정
                </div>
              )}
            </div>
            <div className="p-3 space-y-1.5">
              <div className={`font-mono text-[10px] ${s.text1}`}>{p.my_product_code}</div>
              <div className={`font-mono text-[9px] ${s.text3}`}>원본 {p.source_product_code}</div>
              <div className={`text-[12px] font-medium line-clamp-2 leading-snug ${s.text1}`}>
                {p.market_product_name || p.product_name || '-'}
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <div className={`text-[12px] font-bold ${s.text1}`}>
                  {fmt(p.market_price)}원
                </div>
              </div>
              <MarketBadges p={p} dark={dark} />
            </div>
          </button>
        );
      })}
    </div>
  );
}

function MarketBadges({ p, dark }: { p: MyProductItem; dark: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1 pt-1">
      {MARKETS.map(m => {
        const v = (p as any)[m.key];
        const on = v && v !== '' && v !== '0' && v !== 'N';
        return (
          <span
            key={m.key}
            title={m.label}
            className={`px-1.5 py-0.5 rounded text-[9px] font-bold transition-opacity ${on ? '' : 'opacity-30'}`}
            style={{
              backgroundColor: on ? `${m.color}25` : (dark ? '#2a2b35' : '#f3f4f6'),
              color: on ? m.color : (dark ? '#6b7280' : '#9ca3af'),
            }}
          >
            {m.label}
          </span>
        );
      })}
    </div>
  );
}
