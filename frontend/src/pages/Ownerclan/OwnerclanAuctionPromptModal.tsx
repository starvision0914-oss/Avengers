import toast from 'react-hot-toast';

// 옥션(auction.co.kr / ESM PLUS) 상품명 생성 AI 프롬프트 — 옥션 실판매 485건 고객패턴 + 검색 상위노출(적합도) 분석 반영.
// 동기화본: /home/rejoice888/PUBLIC/auction_product_name_prompt.txt
const PROMPT = `옥션(auction.co.kr / ESM PLUS) 상품명 생성기 — 실판매·상위노출 최적화.

═══ 1. 옥션 고객 패턴 (자사 옥션 실판매 분석) ═══
- 주력 가격대 2~5만원 중가 = 전체의 80%. 5천원 이하는 거의 안 팔림 → 저가 미끼표현 말고 '실속·품질' 소구.
- 잘 팔리는 소구점: 대용량·세트·리필·다용도·가정용·업소용·국산·호환 (묶음·실용·교체수요에 반응).
- 타겟 명확형(남성·캠핑·선물)에 강하게 반응.

═══ 2. 옥션 상위노출(검색 랭킹) 전략 ═══
랭킹 = 적합도(상품명·카테고리 키워드 매칭) + 인기도(클릭·찜) + 판매실적 + 리뷰·신상품.
→ 상품명이 직접 좌우하는 건 '적합도'. 대표 검색어를 정확히, 옥션 카테고리에 맞게 배치하면 노출이 오른다.
- 검색용 상품명은 색인됨(100byte 이내, 한글1자≈3byte). 핵심 대표키워드는 반드시 맨 앞.
- 동일 핵심명사 최대 2회. 카테고리 정확 등록(오등록=노출저하).

═══ 3. 상품명 공식 ═══
[대표검색어] + [규격/수량·대용량/세트] + [핵심속성 1~2개] + [타겟/용도]  — 35~38자.
예) "캠핑 의자 접이식 경량 휴대용 폴딩체어 대용량"
   "주방세제 리필 대용량 2개 업소용 다용도"
   "남성 여름 반바지 빅사이즈 3색 국산 캐주얼"

═══ 4. 규칙 ═══
1) 옥션에서 실제 검색되는 대표키워드를 맨 앞에 + 옥션 카테고리에 정확히 매칭(적합도↑).
2) 38자 내외로 간결(길면 전환↓ — 실데이터).
3) 옥션 소구점 1개 이상 포함: 대용량/세트/리필/다용도/국산/업소용/가정용.
4) 규격·수량·색을 구체적으로(2개입/3색/대형).
5) 타겟 또는 용도 1개(남성/캠핑/선물/어린이).
금지(2개만): 라이선스 없는 브랜드·캐릭터명, 효능 단정(치료·특효·항암).

═══ 5. 출력 ═══
상품명(검색용) 1줄 + 사용 키워드 목록.
입력[원본명/카테고리/제품정보] → 위반판정 → 공식대로 생성 → 출력.`;

export default function OwnerclanAuctionPromptModal(
  { open, onClose, dark }: { open: boolean; onClose: () => void; dark: boolean },
) {
  if (!open) return null;
  const copy = async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(PROMPT);
      } else {
        const ta = document.createElement('textarea');
        ta.value = PROMPT; ta.style.position = 'fixed'; ta.style.left = '-9999px';
        document.body.appendChild(ta); ta.focus(); ta.select();
        const ok = document.execCommand('copy'); document.body.removeChild(ta);
        if (!ok) throw new Error('copy failed');
      }
      toast.success('옥션 프롬프트가 복사되었습니다');
    } catch {
      toast.error('복사 실패 — 입력창 클릭 후 Ctrl+A → Ctrl+C 하세요');
    }
  };
  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35] text-white' : 'bg-white border-gray-200 text-gray-900';
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className={`w-full max-w-3xl max-h-[88vh] rounded-xl border ${card} flex flex-col`} onClick={e => e.stopPropagation()}>
        <div className={`flex items-center gap-2 px-5 py-3 border-b ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
          <h3 className="text-[14px] font-bold">옥션 상품명변경 — AI 프롬프트</h3>
          <button onClick={copy} className="ml-auto px-3 py-1.5 text-[12px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded">📋 복사</button>
          <button onClick={onClose} className={`${dark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-700'} text-[15px] px-1`}>✕</button>
        </div>
        <div className="p-4 overflow-hidden flex flex-col">
          <p className={`text-[12px] mb-2 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
            옥션 실판매 고객패턴 + 상위노출(적합도) 분석 반영. <b>📋 복사</b>해서 AI에 붙여넣고 제품정보를 주세요.
          </p>
          <textarea readOnly value={PROMPT} onFocus={e => e.currentTarget.select()}
            className={`w-full h-[60vh] text-[12px] leading-[1.5] font-mono p-3 rounded border resize-none ${dark ? 'bg-[#0f1117] border-[#2a2b35] text-gray-200' : 'bg-gray-50 border-gray-200 text-gray-800'}`} />
        </div>
      </div>
    </div>
  );
}
