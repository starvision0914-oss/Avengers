import { useState, useEffect } from 'react';
import { X, Save, Loader2, BadgeCheck, Eye, EyeOff, Image as ImageIcon } from 'lucide-react';
import toast from 'react-hot-toast';
import { fetchMyProductDetail, updateMyProduct, type MyProductDetail } from '../../api/myproduct';
import { themeStyles } from '../Ownerclan/constants';

interface Props {
  dark: boolean;
  productId: number | null;
  onClose: () => void;
  onSaved: () => void;
}

const EDITABLE = ['product_name', 'category_code', 'category_name',
  'image_large', 'image_medium', 'image_small', 'detail_html'] as const;
type EditableKey = typeof EDITABLE[number];

export default function MyProductEditModal({ dark, productId, onClose, onSaved }: Props) {
  const s = themeStyles(dark);
  const [detail, setDetail] = useState<MyProductDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showSource, setShowSource] = useState(true);
  const [draft, setDraft] = useState<Record<EditableKey, string>>({
    product_name: '', category_code: '', category_name: '',
    image_large: '', image_medium: '', image_small: '', detail_html: '',
  });

  useEffect(() => {
    if (!productId) { setDetail(null); return; }
    setLoading(true);
    fetchMyProductDetail(productId)
      .then(d => {
        setDetail(d);
        const next = {} as Record<EditableKey, string>;
        EDITABLE.forEach(k => { next[k] = String((d as any)[k] || ''); });
        setDraft(next);
      })
      .catch((e) => toast.error(`상세 로드 실패: ${e.message || e}`))
      .finally(() => setLoading(false));
  }, [productId]);

  useEffect(() => {
    if (!productId) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [productId, onClose]);

  if (!productId) return null;

  const handleSave = async () => {
    if (!detail) return;
    const changed: Record<string, string> = {};
    EDITABLE.forEach(k => {
      if (draft[k] !== String((detail as any)[k] || '')) changed[k] = draft[k];
    });
    if (Object.keys(changed).length === 0) {
      toast('변경된 내용이 없습니다.');
      return;
    }
    setSaving(true);
    const tid = toast.loading('저장 중...');
    try {
      const r = await updateMyProduct(productId, changed);
      toast.success(`${r.updated || 0}건 저장 (${(r.fields || []).join(', ')})`, { id: tid });
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(`저장 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setSaving(false);
    }
  };

  const src = (detail?.source as Record<string, any>) || null;

  const inputCls = `w-full px-3 py-2 rounded-lg border text-[12px] ${s.inputBg} focus:outline-none focus:border-blue-500`;
  const labelCls = `text-[11px] font-bold ${s.text2} mb-1`;
  const sourceCls = `text-[11px] ${s.text3} mt-0.5 truncate`;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in"
      onClick={onClose}>
      <div className={`relative w-full max-w-5xl max-h-[92vh] overflow-hidden rounded-2xl border ${s.card} shadow-2xl`}
        onClick={(e) => e.stopPropagation()}>
        <header className={`flex items-center justify-between px-5 py-3 border-b ${s.border}`}>
          <div className="flex items-center gap-3">
            <span className={`font-mono text-[12px] font-bold ${s.text1}`}>{detail?.my_product_code || '...'}</span>
            <span className={`text-[10px] ${s.text3}`}>← 원본 {detail?.source_product_code || ''}</span>
            {detail?.is_modified ? (
              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-green-500/15 text-green-500 text-[10px] font-bold">
                <BadgeCheck size={10} /> 수정됨
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowSource(s => !s)}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] ${s.cardHover} ${s.text2}`}>
              {showSource ? <Eye size={12} /> : <EyeOff size={12} />}
              {showSource ? '원본 숨김' : '원본 보기'}
            </button>
            <button onClick={onClose} className={`p-1 rounded ${s.cardHover} ${s.text2}`} aria-label="닫기">
              <X size={18} />
            </button>
          </div>
        </header>

        <div className="overflow-y-auto" style={{ maxHeight: 'calc(92vh - 112px)' }}>
          {loading ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 size={32} className="text-blue-500 animate-spin" />
            </div>
          ) : !detail ? (
            <div className={`p-12 text-center ${s.text2}`}>상세 정보를 불러올 수 없습니다.</div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 p-5">

              <div className="space-y-4">
                <div>
                  <div className={labelCls}>상품명</div>
                  <input value={draft.product_name}
                    onChange={e => setDraft({ ...draft, product_name: e.target.value })}
                    className={inputCls} />
                  {showSource && src && (
                    <div className={sourceCls} title={src.product_name}>원본: {src.product_name || '(없음)'}</div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <div className={labelCls}>카테고리코드</div>
                    <input value={draft.category_code}
                      onChange={e => setDraft({ ...draft, category_code: e.target.value })}
                      className={inputCls} />
                    {showSource && src && (
                      <div className={sourceCls}>원본: {src.category_code || '(없음)'}</div>
                    )}
                  </div>
                  <div>
                    <div className={labelCls}>카테고리명</div>
                    <input value={draft.category_name}
                      onChange={e => setDraft({ ...draft, category_name: e.target.value })}
                      className={inputCls} />
                    {showSource && src && (
                      <div className={sourceCls}>원본: {src.category_name || '(없음)'}</div>
                    )}
                  </div>
                </div>

                {(['image_large', 'image_medium', 'image_small'] as const).map((key) => {
                  const labels = { image_large: '이미지 (큰)', image_medium: '이미지 (중)', image_small: '이미지 (소)' };
                  return (
                    <div key={key}>
                      <div className={labelCls}>{labels[key]}</div>
                      <input value={draft[key]}
                        onChange={e => setDraft({ ...draft, [key]: e.target.value })}
                        placeholder="https://..."
                        className={inputCls + ' font-mono text-[11px]'} />
                      {showSource && src && (
                        <div className={sourceCls} title={src[key]}>원본: {(src[key] || '(없음)').toString().slice(0, 60)}</div>
                      )}
                      <div className="mt-2 flex items-center gap-3">
                        <div className={`w-20 h-20 rounded border ${s.border} flex items-center justify-center overflow-hidden ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
                          {draft[key] ? (
                            <img src={draft[key]} alt="" className="w-full h-full object-contain"
                              onError={(e) => (e.currentTarget.style.display = 'none')} />
                          ) : (
                            <ImageIcon size={20} className={s.text3} />
                          )}
                        </div>
                        {showSource && src && src[key] && src[key] !== draft[key] && (
                          <div className={`w-20 h-20 rounded border ${s.border} flex items-center justify-center overflow-hidden ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'} opacity-60`}>
                            <img src={String(src[key])} alt="원본" className="w-full h-full object-contain" />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-3">
                <div>
                  <div className={labelCls}>본문 상세설명 (HTML)</div>
                  <textarea value={draft.detail_html}
                    onChange={e => setDraft({ ...draft, detail_html: e.target.value })}
                    className={inputCls + ' font-mono text-[11px] resize-y'}
                    rows={14} />
                </div>
                <div>
                  <div className={`text-[11px] font-bold ${s.text2} mb-1`}>미리보기</div>
                  <iframe srcDoc={draft.detail_html} sandbox="allow-same-origin"
                    className={`w-full rounded-lg border ${s.border}`}
                    style={{ minHeight: 280, height: 320, background: '#fff' }} title="상세 미리보기" />
                </div>
                {showSource && src?.detail_html && src.detail_html !== draft.detail_html && (
                  <div>
                    <div className={`text-[11px] font-bold ${s.text3} mb-1`}>원본 미리보기</div>
                    <iframe srcDoc={String(src.detail_html)} sandbox="allow-same-origin"
                      className={`w-full rounded-lg border ${s.border} opacity-70`}
                      style={{ minHeight: 200, height: 240, background: '#fff' }} title="원본 미리보기" />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <footer className={`flex items-center justify-end gap-2 px-5 py-3 border-t ${s.border}`}>
          <button onClick={onClose} disabled={saving}
            className={`px-4 py-2 rounded-lg text-[12px] font-semibold ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'} disabled:opacity-50`}>
            취소
          </button>
          <button onClick={handleSave} disabled={saving || loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold disabled:opacity-50">
            <Save size={13} />
            {saving ? '저장 중...' : '저장'}
          </button>
        </footer>
      </div>
    </div>
  );
}
