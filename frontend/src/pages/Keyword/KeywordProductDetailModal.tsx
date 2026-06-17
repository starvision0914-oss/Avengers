import { useEffect, useState } from 'react';
import { X, ChevronLeft, ChevronRight, Package, Loader2 } from 'lucide-react';
import { fetchProductDetail, type ProductDetail } from '../../api/keyword';
import { themeStyles, fmt, FIELD_LABELS, PRICE_FIELDS, SALE_STATUS_LABEL, SALE_STATUS_COLOR, MARKETS } from './constants';
import CategoryPath from '../../components/CategoryPath';

interface Props {
  dark: boolean;
  productId: number | null;
  onClose: () => void;
}

export default function KeywordProductDetailModal({ dark, productId, onClose }: Props) {
  const s = themeStyles(dark);
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'changed' | 'all'>('changed');
  const [imgIdx, setImgIdx] = useState(0);

  useEffect(() => {
    if (!productId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setImgIdx(0);
    setTab('changed');
    fetchProductDetail(productId)
      .then(setDetail)
      .finally(() => setLoading(false));
  }, [productId]);

  useEffect(() => {
    if (!productId) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [productId, onClose]);

  if (!productId) return null;

  const images = detail
    ? [detail.image_large, detail.image_medium, detail.image_small].filter(Boolean) as string[]
    : [];

  const changed = (detail?.changed_fields || []).filter(f => FIELD_LABELS[f]);
  const allFields = Object.keys(FIELD_LABELS);
  const fields = tab === 'changed' ? changed : allFields;

  const detailHtml = (detail?.detail_html as string) || '';

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in"
      onClick={onClose}
    >
      <div
        className={`relative w-full max-w-6xl max-h-[92vh] overflow-hidden rounded-2xl border ${s.card} shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={`flex items-center justify-between px-5 py-3 border-b ${s.border}`}>
          <div className="flex items-center gap-3">
            <span className={`font-mono text-[12px] ${s.text2}`}>{detail?.product_code}</span>
            {detail && (
              <span
                className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                style={{ backgroundColor: `${SALE_STATUS_COLOR[detail.sale_status]}25`, color: SALE_STATUS_COLOR[detail.sale_status] }}
              >
                {SALE_STATUS_LABEL[detail.sale_status]}
              </span>
            )}
            {changed.length > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-500/15 text-orange-500 text-[10px] font-bold">
                ◐ {changed.length}개 변경됨
              </span>
            )}
          </div>
          <button onClick={onClose} className={`p-1 rounded ${s.cardHover} ${s.text2}`} aria-label="닫기">
            <X size={18} />
          </button>
        </header>

        <div className="overflow-y-auto" style={{ maxHeight: 'calc(92vh - 56px)' }}>
          {loading ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 size={32} className="text-blue-500 animate-spin" />
            </div>
          ) : !detail ? (
            <div className={`p-12 text-center ${s.text2}`}>상세 정보를 불러올 수 없습니다.</div>
          ) : (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 p-5">
                <div className="lg:col-span-5 space-y-3">
                  <ImageGallery images={images} idx={imgIdx} onIdx={setImgIdx} dark={dark} />
                  <div>
                    <div className={`text-[10px] font-bold ${s.text3} mb-1.5`}>마켓 노출</div>
                    <div className="grid grid-cols-2 gap-1.5">
                      {MARKETS.map(m => {
                        const v = (detail as any)[m.key];
                        const on = v && v !== '' && v !== '0' && v !== 'N';
                        return (
                          <div
                            key={m.key}
                            className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-semibold"
                            style={{
                              backgroundColor: on ? `${m.color}20` : (dark ? '#0f1117' : '#f9fafb'),
                              color: on ? m.color : (dark ? '#6b7280' : '#9ca3af'),
                              border: `1px solid ${on ? m.color : (dark ? '#2a2b35' : '#e5e7eb')}`,
                            }}
                          >
                            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: on ? m.color : 'currentColor' }} />
                            {m.label}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  <div className={`rounded-lg px-3 py-2 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
                    <div className={`text-[10px] ${dark ? 'text-gray-500' : 'text-gray-400'}`}>카테고리</div>
                    <div className="mt-0.5">
                      <CategoryPath path={String(detail.category_name || '')} dark={dark} code={String(detail.category_code || '')} />
                    </div>
                  </div>
                  <MetaCard label="제조사" value={String(detail.manufacturer || '-')} dark={dark} />
                  <MetaCard label="원산지" value={String(detail.origin || '-')} dark={dark} />
                </div>

                <div className="lg:col-span-4 space-y-3">
                  <div className="flex items-center gap-1 border-b border-transparent">
                    <TabBtn active={tab === 'changed'} onClick={() => setTab('changed')} dark={dark}>
                      변경 ({changed.length})
                    </TabBtn>
                    <TabBtn active={tab === 'all'} onClick={() => setTab('all')} dark={dark}>
                      전체 ({allFields.length})
                    </TabBtn>
                  </div>
                  <FieldDiffTable detail={detail} fields={fields} dark={dark} mode={tab} />
                </div>

                <div className="lg:col-span-3 space-y-3">
                  <OptionsTree detail={detail} dark={dark} />
                  <KeywordsCard detail={detail} dark={dark} />
                </div>
              </div>

              {detailHtml && (
                <div className={`border-t ${s.border} px-5 py-4`}>
                  <div className={`text-[12px] font-bold ${s.text1} mb-2`}>본문 상세설명</div>
                  <iframe
                    srcDoc={detailHtml}
                    sandbox="allow-same-origin"
                    className={`w-full rounded-lg border ${s.border}`}
                    style={{ minHeight: 320, height: 480, background: '#fff' }}
                    title="상품 상세설명"
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ImageGallery({ images, idx, onIdx, dark }: { images: string[]; idx: number; onIdx: (n: number) => void; dark: boolean }) {
  const s = themeStyles(dark);
  if (images.length === 0) {
    return (
      <div className={`aspect-square w-full rounded-lg flex items-center justify-center ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
        <Package size={40} className={s.text3} />
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <div className={`relative aspect-square w-full rounded-lg overflow-hidden ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
        <img src={images[idx]} alt="" className="w-full h-full object-contain" />
        {images.length > 1 && (
          <>
            <button
              onClick={() => onIdx((idx - 1 + images.length) % images.length)}
              className="absolute left-1 top-1/2 -translate-y-1/2 p-1 rounded-full bg-black/40 text-white hover:bg-black/60"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => onIdx((idx + 1) % images.length)}
              className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded-full bg-black/40 text-white hover:bg-black/60"
            >
              <ChevronRight size={16} />
            </button>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="flex gap-1 justify-center">
          {images.map((_, i) => (
            <button
              key={i}
              onClick={() => onIdx(i)}
              className={`w-1.5 h-1.5 rounded-full transition-colors ${i === idx ? 'bg-blue-500' : dark ? 'bg-[#2a2b35]' : 'bg-gray-300'}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MetaCard({ label, value, dark }: { label: string; value: string; dark: boolean }) {
  const s = themeStyles(dark);
  return (
    <div className={`rounded-lg px-3 py-2 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
      <div className={`text-[10px] ${s.text3}`}>{label}</div>
      <div className={`text-[12px] font-medium ${s.text1} truncate`}>{value}</div>
    </div>
  );
}

function TabBtn({ active, onClick, dark, children }: { active: boolean; onClick: () => void; dark: boolean; children: React.ReactNode }) {
  const s = themeStyles(dark);
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-[12px] font-semibold rounded-t-lg border-b-2 transition-colors ${
        active ? 'border-blue-500 text-blue-500' : `border-transparent ${s.text2} hover:border-gray-400`
      }`}
    >
      {children}
    </button>
  );
}

function FieldDiffTable({
  detail, fields, dark, mode,
}: {
  detail: ProductDetail; fields: string[]; dark: boolean; mode: 'changed' | 'all';
}) {
  const s = themeStyles(dark);
  if (fields.length === 0) {
    return <div className={`text-center py-8 ${s.text2} text-[12px]`}>{mode === 'changed' ? '변경된 필드가 없습니다' : '필드 정보가 없습니다'}</div>;
  }
  return (
    <div className={`rounded-lg border ${s.border} overflow-hidden`}>
      <table className="w-full text-[11px]">
        <thead className={dark ? 'bg-[#0f1117]' : 'bg-gray-50'}>
          <tr className={s.text3}>
            <th className="px-3 py-2 text-left font-medium w-[140px]">항목</th>
            <th className="px-3 py-2 text-left font-medium">원본</th>
            <th className="px-3 py-2 text-left font-medium">현재</th>
          </tr>
        </thead>
        <tbody className={`divide-y ${s.divider}`}>
          {fields.map(f => {
            const cur = (detail as any)[f];
            const orig = (detail as any)[`orig_${f}`];
            const changed = String(cur ?? '') !== String(orig ?? '');
            const isPrice = PRICE_FIELDS.has(f);
            const display = (v: any) => isPrice ? fmt(Number(v) || 0) : (v ?? '').toString().slice(0, 200);
            return (
              <tr key={f} className={changed ? 'bg-orange-500/5' : ''}>
                <td className={`px-3 py-2 font-medium ${s.text2} align-top`}>{FIELD_LABELS[f] || f}</td>
                <td className={`px-3 py-2 ${changed ? s.text3 : s.text2} align-top`}>{display(orig)}</td>
                <td className={`px-3 py-2 align-top ${changed ? 'text-orange-500 font-semibold' : s.text1}`}>{display(cur)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function OptionsTree({ detail, dark }: { detail: ProductDetail; dark: boolean }) {
  const s = themeStyles(dark);
  const o1n = String(detail.option1_name || '');
  const o1v = String(detail.option1_values || '').split(/[,|/]/).map(x => x.trim()).filter(Boolean);
  const o2n = String(detail.option2_name || '');
  const o2v = String(detail.option2_values || '').split(/[,|/]/).map(x => x.trim()).filter(Boolean);
  const hasOpts = o1v.length > 0 || o2v.length > 0;
  return (
    <div className={`rounded-lg p-3 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
      <div className={`text-[11px] font-bold ${s.text1} mb-2`}>옵션</div>
      {!hasOpts && <div className={`text-[11px] ${s.text3}`}>옵션 정보 없음</div>}
      {o1v.length > 0 && (
        <div className="mb-2">
          <div className={`text-[10px] font-semibold ${s.text2} mb-1`}>{o1n || '옵션1'}</div>
          <div className="flex flex-wrap gap-1">
            {o1v.map(v => (
              <span key={v} className={`px-1.5 py-0.5 rounded text-[10px] ${dark ? 'bg-[#2a2b35] text-gray-300' : 'bg-white text-gray-700 border border-gray-200'}`}>{v}</span>
            ))}
          </div>
        </div>
      )}
      {o2v.length > 0 && (
        <div>
          <div className={`text-[10px] font-semibold ${s.text2} mb-1`}>{o2n || '옵션2'}</div>
          <div className="flex flex-wrap gap-1">
            {o2v.map(v => (
              <span key={v} className={`px-1.5 py-0.5 rounded text-[10px] ${dark ? 'bg-[#2a2b35] text-gray-300' : 'bg-white text-gray-700 border border-gray-200'}`}>{v}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KeywordsCard({ detail, dark }: { detail: ProductDetail; dark: boolean }) {
  const s = themeStyles(dark);
  const keywords = String(detail.keywords || '').split(/[,]/).map(x => x.trim()).filter(Boolean);
  if (keywords.length === 0) return null;
  return (
    <div className={`rounded-lg p-3 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
      <div className={`text-[11px] font-bold ${s.text1} mb-2`}>키워드</div>
      <div className="flex flex-wrap gap-1">
        {keywords.slice(0, 30).map((k, i) => (
          <span key={i} className={`px-1.5 py-0.5 rounded text-[10px] ${dark ? 'bg-[#2a2b35] text-gray-300' : 'bg-white text-gray-700 border border-gray-200'}`}>{k}</span>
        ))}
      </div>
    </div>
  );
}
