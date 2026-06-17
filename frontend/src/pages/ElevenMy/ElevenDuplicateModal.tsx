import { useEffect, useState } from 'react';
import { X, AlertTriangle, Loader2, ChevronDown, ChevronRight as CR } from 'lucide-react';
import toast from 'react-hot-toast';
import { fetchDuplicates, type DuplicateMode, type DuplicateResult } from '../../api/elevenMy';
import { themeStyles, fmt } from '../Ownerclan/constants';

interface Props {
  dark: boolean;
  open: boolean;
  onClose: () => void;
}

const MODES: { v: DuplicateMode; label: string; desc: string }[] = [
  { v: 'strict', label: '정확 일치', desc: '상품명+가격 100% 동일' },
  { v: 'loose', label: '정규화 일치', desc: '특수문자/공백 무시한 상품명' },
  { v: 'image', label: '이미지 일치', desc: '같은 상품 이미지 URL' },
];

export default function ElevenDuplicateModal({ dark, open, onClose }: Props) {
  const s = themeStyles(dark);
  const [mode, setMode] = useState<DuplicateMode>('strict');
  const [data, setData] = useState<DuplicateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetchDuplicates(mode)
      .then(setData)
      .catch(() => toast.error('중복 검사 실패'))
      .finally(() => setLoading(false));
  }, [open, mode]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const toggleGroup = (key: string) => {
    setExpanded(prev => {
      const n = new Set(prev);
      if (n.has(key)) n.delete(key); else n.add(key);
      return n;
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className={`relative w-full max-w-5xl max-h-[92vh] overflow-hidden rounded-2xl border ${s.card} shadow-2xl flex flex-col`} onClick={e => e.stopPropagation()}>
        <header className={`flex items-center justify-between px-5 py-3 border-b ${s.border}`}>
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-orange-500" />
            <h2 className={`text-[12px] font-bold ${s.text1}`}>11번가 중복상품 검사</h2>
            {data && (
              <span className={`text-[11px] ${s.text3}`}>
                · 스캔 {fmt(data.total_scanned)} · 중복그룹 <b className="text-orange-500">{data.group_count}</b> · 위험상품 <b className="text-red-500">{fmt(data.total_duplicate_items)}</b>
              </span>
            )}
          </div>
          <button onClick={onClose} className={`p-1 rounded ${s.cardHover} ${s.text2}`}><X size={18} /></button>
        </header>

        <div className={`flex items-center gap-2 px-5 py-2 border-b ${s.border}`}>
          {MODES.map(m => (
            <button
              key={m.v}
              onClick={() => setMode(m.v)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold ${
                mode === m.v
                  ? 'bg-orange-500 text-white'
                  : dark ? 'bg-[#2a2b35] text-gray-300 hover:bg-[#353749]' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              title={m.desc}
            >
              {m.label}
            </button>
          ))}
          <span className={`text-[10px] ${s.text3} ml-2`}>
            {MODES.find(m => m.v === mode)?.desc}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {loading ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 size={28} className="animate-spin text-orange-500" />
            </div>
          ) : !data || data.group_count === 0 ? (
            <div className={`p-12 text-center ${s.text2}`}>
              <div className="text-2xl mb-2">✓</div>
              <div className={`${s.text1} font-semibold mb-1`}>중복 위험 상품 없음</div>
              <div className={`text-[11px] ${s.text3}`}>"{MODES.find(m => m.v === mode)?.label}" 기준 분석 결과</div>
            </div>
          ) : (
            data.groups.map((g) => {
              const isOpen = expanded.has(g.group_key);
              return (
                <div key={g.group_key} className={`rounded-lg border ${s.card}`}>
                  <button
                    onClick={() => toggleGroup(g.group_key)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-left ${s.cardHover}`}
                  >
                    {isOpen ? <ChevronDown size={14} className={s.text2} /> : <CR size={14} className={s.text2} />}
                    {g.sample_image && (
                      <img src={g.sample_image} alt="" className="w-8 h-8 rounded object-cover" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className={`text-[12px] font-semibold ${s.text1} truncate`}>{g.sample_name || '(상품명 없음)'}</div>
                      <div className={`text-[10px] ${s.text3}`}>{fmt(g.sample_price)}원</div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-500 text-[10px] font-bold">
                      {g.count}개 중복
                    </span>
                  </button>
                  {isOpen && (
                    <div className={`border-t ${s.border} divide-y ${dark ? 'divide-[#2a2b35]' : 'divide-gray-100'}`}>
                      {g.items.map(it => (
                        <div key={it.id} className={`flex items-center gap-3 px-4 py-2 ${s.cardHover}`}>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${dark ? 'bg-[#0f1117] text-gray-400' : 'bg-gray-100 text-gray-600'}`}>
                            {it.login_id}
                          </span>
                          <span className={`text-[11px] font-mono ${s.text2}`}>{it.product_no}</span>
                          <span className={`flex-1 text-[11px] truncate ${s.text1}`}>{it.product_name}</span>
                          <span className={`text-[11px] font-semibold ${s.text2}`}>{fmt(it.sale_price)}</span>
                          <span className={`text-[10px] ${s.text3}`}>재고 {it.stock_quantity}</span>
                          <a
                            href={`https://www.11st.co.kr/products/${it.product_no}`}
                            target="_blank" rel="noreferrer"
                            className="text-[10px] text-blue-500 hover:underline"
                          >
                            보기 →
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        <div className={`px-5 py-2 border-t ${s.border} text-[10px] ${s.text3}`}>
          11번가는 동일 셀러의 중복 상품을 자동 판매금지합니다. 위 그룹들은 정책 위반 위험이 있어 한 개만 남기고 나머지를 정리하시는 게 좋습니다.
        </div>
      </div>
    </div>
  );
}
