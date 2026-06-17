import { useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { applyElevenNames, type OwnerclanProductItem } from '../../api/ownerclan';
import { themeStyles } from './constants';

interface Props {
  dark: boolean;
  open: boolean;
  products: OwnerclanProductItem[];   // 대상(선택된 것 우선, 없으면 현재 페이지)
  onClose: () => void;
  onApplied?: () => void;             // 저장 후 목록 새로고침용
}

// 11번가 상품명 최적화 규칙 (보고서 기반)
const BANNED = [
  '정품', '최저가', '초특가', '특가', '무료배송', '당일발송', '오늘출발', '당일출발',
  '1+1', '사은품', '이벤트', '할인', '세일', 'sale', 'SALE', '베스트', 'best', 'BEST',
  '강추', '추천', '인기', '핫딜', '땡처리', '품절임박', '한정', '단독', '신상', '신상품',
];
const MAX_LEN = 50;

function generateElevenName(p: OwnerclanProductItem): string {
  let base = (p.market_product_name || p.product_name || '').trim();
  // 1) 특수문자 → 공백 (한글/영문/숫자/공백만 유지)
  base = base.replace(/[^0-9A-Za-z가-힣\s]/g, ' ');
  // 2) 금지/과장 문구 제거
  for (const w of BANNED) base = base.replace(new RegExp(w, 'gi'), ' ');
  // 3) 토큰화 + 중복 단어 제거(앞 우선, 대소문자 무시)
  const seen = new Set<string>();
  let words = base.split(/\s+/).filter(Boolean).filter((w) => {
    const k = w.toLowerCase();
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  // 4) 브랜드(제조/수입사) 앞 보강
  const brand = (p.manufacturer || '').trim();
  const arr: string[] = [];
  if (brand && brand.length <= 20 && !words.some((w) => w.includes(brand))) arr.push(brand);
  arr.push(...words);
  // 5) 카테고리 말단 키워드 보강
  const catSeg = (p.category_name || '').split(/[>/]/).map((s) => s.trim()).filter(Boolean).pop();
  if (catSeg && catSeg.length <= 12 && !arr.some((w) => w.includes(catSeg))) arr.push(catSeg);
  // 6) 50자 컷 (단어 경계)
  let name = '';
  for (const w of arr) {
    if ((name ? name + ' ' + w : w).length > MAX_LEN) break;
    name = name ? name + ' ' + w : w;
  }
  return name.trim();
}

export default function OwnerclanElevenNameModal({ dark, open, products, onClose, onApplied }: Props) {
  const s = themeStyles(dark);
  const [rows, setRows] = useState<{ code: string; orig: string; gen: string }[]>([]);
  const [generated, setGenerated] = useState(false);
  const [saving, setSaving] = useState(false);

  const targets = useMemo(() => products, [products]);

  const setGen = (i: number, v: string) => setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, gen: v } : r)));

  const doSave = async () => {
    const items = rows.filter((r) => r.gen.trim()).map((r) => ({ code: r.code, name: r.gen.trim() }));
    if (!items.length) { toast.error('저장할 상품명이 없습니다.'); return; }
    setSaving(true);
    const tid = toast.loading('예비상품에 저장 중...');
    try {
      const r = await applyElevenNames(items);
      toast.success(`${r.updated}개 예비상품 상품명 저장 완료`, { id: tid });
      onApplied?.();
      onClose();
    } catch (e: any) {
      toast.error(`저장 실패: ${e.response?.data?.error || e.message}`, { id: tid });
    } finally {
      setSaving(false);
    }
  };

  const doGenerate = () => {
    if (!targets.length) {
      toast.error('대상 상품이 없습니다. 체크박스로 선택하거나 목록을 확인하세요.');
      return;
    }
    setRows(targets.map((p) => ({
      code: p.product_code,
      orig: p.market_product_name || p.product_name || '',
      gen: generateElevenName(p),
    })));
    setGenerated(true);
  };

  const copyOne = (t: string) => {
    navigator.clipboard?.writeText(t).then(() => toast.success('복사됨')).catch(() => toast.error('복사 실패'));
  };
  const copyAll = () => {
    const txt = rows.map((r) => r.gen).join('\n');
    navigator.clipboard?.writeText(txt).then(() => toast.success(`${rows.length}개 상품명 복사됨`)).catch(() => toast.error('복사 실패'));
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className={`rounded-xl border ${s.card} max-w-[1000px] w-[95%] max-h-[85vh] overflow-auto`} onClick={(e) => e.stopPropagation()}>
        <div className={`flex items-center gap-2 px-5 py-3 border-b ${s.border} sticky top-0 ${dark ? 'bg-[#1a1b23]' : 'bg-white'}`}>
          <h3 className={`text-[13px] font-bold ${s.text1}`}>11번가 상품명 생성</h3>
          <span className={`text-[11px] ${s.text3}`}>대상 {targets.length}개 (선택분 우선)</span>
          <button onClick={doGenerate} className="ml-auto px-3 py-1.5 text-[12px] font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg">생성</button>
          {generated && rows.length > 0 && (
            <>
              <button onClick={copyAll} className={`px-3 py-1.5 text-[12px] font-semibold rounded-lg ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}>전체 복사</button>
              <button onClick={doSave} disabled={saving} className="px-3 py-1.5 text-[12px] font-semibold bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg">예비상품에 저장</button>
            </>
          )}
          <button onClick={onClose} className={`px-2 py-1 text-[12px] ${s.text2} hover:${s.text1}`}>✕</button>
        </div>

        <div className={`px-5 py-2 text-[11px] ${s.text3} border-b ${s.border}`}>
          규칙: 특수문자·과장문구(정품/최저가/무료배송…) 제거 → 중복 단어 제거 → 브랜드·카테고리 키워드 보강 → 50자 컷 · <b>생성본은 직접 수정 후 저장 가능</b>
        </div>

        <div className="p-4">
          {!generated ? (
            <div className={`text-center py-10 text-[12px] ${s.text2}`}>
              상단 <b>생성</b> 버튼을 누르면 대상 {targets.length}개의 11번가 상품명을 만듭니다.
            </div>
          ) : rows.length === 0 ? (
            <div className={`text-center py-10 text-[12px] ${s.text2}`}>대상 상품이 없습니다.</div>
          ) : (
            <table className="w-full text-[12px]">
              <thead>
                <tr className={`${dark ? 'bg-[#0f1117]' : 'bg-gray-50'} ${s.text2}`}>
                  <th className="px-2 py-1.5 text-left font-medium w-24">W코드</th>
                  <th className="px-2 py-1.5 text-left font-medium">원본 상품명</th>
                  <th className="px-2 py-1.5 text-left font-medium">11번가 상품명 (생성)</th>
                  <th className="px-2 py-1.5 text-center font-medium w-16">길이</th>
                  <th className="px-2 py-1.5 text-center font-medium w-14"></th>
                </tr>
              </thead>
              <tbody className={`divide-y ${s.divider}`}>
                {rows.map((r, i) => (
                  <tr key={i} className={s.rowHover}>
                    <td className={`px-2 py-1.5 font-mono text-[11px] ${s.text3}`}>{r.code}</td>
                    <td className={`px-2 py-1.5 ${s.text3} max-w-[280px] truncate`} title={r.orig}>{r.orig}</td>
                    <td className="px-2 py-1.5">
                      <input
                        value={r.gen}
                        onChange={(e) => setGen(i, e.target.value)}
                        className={`w-full px-2 py-1 text-[12px] rounded border ${s.inputBg}`}
                      />
                    </td>
                    <td className={`px-2 py-1.5 text-center ${r.gen.length > MAX_LEN ? 'text-red-500' : s.text2}`}>{r.gen.length}</td>
                    <td className="px-2 py-1.5 text-center">
                      <button onClick={() => copyOne(r.gen)} className="text-[11px] text-blue-500 hover:underline">복사</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
