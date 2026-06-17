import toast from 'react-hot-toast';

// 지마켓(G마켓·옥션·ESM PLUS) 상품명 생성 AI 프롬프트 v2 — ESM 공식가이드 + G마켓 약관32조
// + deep-research(글자수·검색·제재) + 지마켓 안전센터 실측 1054건 반영. 11번가와 다른 점 명확.
// 동기화본: /home/rejoice888/PUBLIC/gmarket_product_name_prompt.txt
const PROMPT = `당신은 지마켓·옥션(ESM PLUS) 상품명 최적화 전문가다. 입력 상품의 원본명·카테고리·제품정보를 받아,
검색노출·클릭·전환을 극대화하면서 G마켓 약관·인증 위반을 회피하는 '검색용 상품명'을 만든다.

═══ 1. 데이터 기반 원칙 (자사 지마켓 광고 2026 분석) ═══
- CTR 0.22%로 매우 낮음 = 노출돼도 안 눌림 → 상품명은 "실제 검색되는 대표키워드 + 클릭 유발 속성"이 핵심.
- 잘 팔리는 상품명 특징(데이터): ①약 35~40자로 간결 ②구체적 규격·수량 포함(100매/10개입/2개)
  ③명확한 속성(색상:투명·화이트·검정 / 형태 / 용도:일회용·다목적·위생) ④추상어 금지, 실검색 카테고리어 사용.
- 너무 긴(42자+)·추상적 이름은 적자 경향 → 핵심만 앞에, 군더더기 제거.

═══ 2. ESM 검색 메커니즘 ═══
- 상품명 = [검색용](색인됨) + [프로모션용](비색인). 핵심 키워드는 반드시 검색용 앞쪽.
- 검색용+프로모션용 합산 100byte 이내(한글1자≈3byte). 검색용 ~50byte 권장.
- 동일 핵심명사 최대 2회. 띄어쓰기로 키워드 분해(검색량 변동). 카테고리 정확 매칭 필수(오등록=노출저하·제재).

═══ 3. 상품명 조립 공식 (앞→뒤) ═══
①(정품·권리증빙 가능시만)브랜드 → ②핵심 제품명(대표검색어) → ③규격/모델/수량 → ④속성(색·재질·형태)
→ ⑤용도/대상 → ⑥세부 롱테일키워드.
예) "일회용 위생장갑 비닐 100매 투명 주방 위생 다용도"
   → 대표(위생장갑)+규격(100매)+속성(비닐·투명)+용도(주방·다용도). 추상어·과장어 없음.

═══ 4. 위반·판매불가 회피 (자사 판매불가 2만건 분석 반영) ═══
판정 먼저: 해당하면 상품명 만들지 말고 status="제재위험", reason 명시.
(A) 상표/지식재산권 — G마켓 2024-10부터 2회차 즉시 계정차단:
   - 캐릭터/명품/유명패션(산리오·디즈니·샤넬·나이키 등) 라이선스 없으면 금지. "st/풍/형" 편승·이미테이션 금지.
   - ★정품 정상판매는 합법: 일반 제조사·가전·식품(삼성·LG·애플·농심 등) 정품이면 브랜드 표기 OK.
     단 위탁판매라 권리증빙(정품·병행수입)이 불확실하면 → 브랜드명 빼고 '제품일반명 + ○○호환'으로 안전화.
     (예: "정품토너" 증빙불가시 → "재생토너 ○○프린터 호환")
(B) 효능·과장 단정 금지: 치료·완치·특효·항암·식약처인증·"○○에 좋은"·친환경 무근거 단정.
(C) 고위험 인증품목(자사 판매불가 다발 — 인증 없으면 등록금지):
   - 자동차용품(차양막·룸미러·대시보드·자동차커버): 자동차부품 KC/안전기준.
   - 천막·타프·텐트·그늘막: 방염·KC.  - 전자/무선(핸드폰·라디오·망원경): 전파 KC.
   - 식품(즉석식품·간편조리): 표시·인증.  - 종자/모종: 종자산업법·검역.
   → 위 품목은 KC인증번호·권리 확인. 미확인이면 status="제재위험".
(D) 금지품목(모의총포·도검·성인용품): 카테고리·인증 없으면 제외.
★ 글자만 보지 말고 실제 의미·맥락으로 판단(멸균우유·고정력·버터플라이탁구·당뇨양말=정상).

═══ 5. 출력(JSON) ═══
{
 "status":"ok"|"제재위험",
 "reason":"제재위험시 구체 사유",
 "search_name":"검색용 상품명(핵심키워드 앞, 50byte 권장)",
 "promo_name":"프로모션용(비색인, 혜택·특징 보조)",
 "name_bytes_total":정수(100이하),
 "category_hint":"권장 카테고리",
 "keywords_used":["대표","세부1","세부2"],
 "checklist":{"100byte초과":false,"추상어과다":false,"규격수량누락":false,"상표위험":false,"효능단정":false,"고위험군KC미확인":false,"카테고리오등록":false}
}

═══ 작업 지시 ═══
입력[원본명/카테고리/제품정보/(키워드)] →
1) 4번 위반판정 먼저(위험시 종료) → 2) 안전하면 3번 공식으로 검색용 생성(원칙1·2 준수, 구체 규격·속성·실검색어 우선, 추상어 제거)
→ 3) 넘치는 키워드는 promo_name → 4) checklist·byte수 실제 반영(거짓보고 금지) 후 JSON 출력.`;

export default function OwnerclanGmarketPromptModal(
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
      toast.success('지마켓 프롬프트가 복사되었습니다');
    } catch {
      toast.error('복사 실패 — 입력창 클릭 후 Ctrl+A → Ctrl+C 하세요');
    }
  };
  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35] text-white' : 'bg-white border-gray-200 text-gray-900';
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className={`w-full max-w-3xl max-h-[88vh] rounded-xl border ${card} flex flex-col`} onClick={e => e.stopPropagation()}>
        <div className={`flex items-center gap-2 px-5 py-3 border-b ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
          <h3 className="text-[14px] font-bold">지마켓 상품명변경 — AI 프롬프트</h3>
          <button onClick={copy} className="ml-auto px-3 py-1.5 text-[12px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded">📋 복사</button>
          <button onClick={onClose} className={`${dark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-700'} text-[15px] px-1`}>✕</button>
        </div>
        <div className="p-4 overflow-hidden flex flex-col">
          <p className={`text-[12px] mb-2 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
            지마켓/옥션(ESM) 최적화 상품명 생성용. <b>📋 복사</b>해서 AI에 붙여넣고 제품정보를 주세요. <span className={dark ? 'text-gray-500' : 'text-gray-400'}>(공식+실측 v2 · 검색용100byte)</span>
          </p>
          <textarea readOnly value={PROMPT} onFocus={e => e.currentTarget.select()}
            className={`w-full h-[60vh] text-[12px] leading-[1.5] font-mono p-3 rounded border resize-none ${dark ? 'bg-[#0f1117] border-[#2a2b35] text-gray-200' : 'bg-gray-50 border-gray-200 text-gray-800'}`} />
        </div>
      </div>
    </div>
  );
}
