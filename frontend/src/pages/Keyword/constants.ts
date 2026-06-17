export const SALE_STATUS_LABEL: Record<number, string> = { 1: '판매중', 2: '품절', 3: '단종' };
export const SALE_STATUS_COLOR: Record<number, string> = {
  1: '#16a34a',
  2: '#f59e0b',
  3: '#dc2626',
};

export const FIELD_LABELS: Record<string, string> = {
  seller_code1: '판매자관리코드1', seller_code2: '판매자관리코드2',
  category_code: '카테고리코드', category_name: '카테고리명', market_category: '마켓카테고리',
  product_name: '원본상품명', market_product_name: '마켓상품명',
  ownerclan_price: '오너클랜판매가', consumer_price: '소비자준수가', market_price: '마켓실제판매가',
  shipping_fee: '배송비', shipping_type: '배송유형', min_qty: '최소구매수량', max_qty: '최대구매수량',
  company_notice: '업체공지', special_notice: '특별공지', return_fee: '반품배송비',
  option1_name: '옵션1명', option1_values: '옵션1값', option2_name: '옵션2명', option2_values: '옵션2값',
  combined_option: '조합형옵션', independent_option: '독립형', combined_option_detail: '조합형',
  product_attribute: '상품속성', product_grade: '상품등급', tax_type: '과세',
  compliance: '준수여부', age_restriction: '19세미만판매금지', return_possible: '단순변심반품가능',
  image_large: '이미지대', image_medium: '이미지중', image_small: '이미지소',
  manufacturer: '제작/수입사', brand: '브랜드', model_name: '모델명', origin: '원산지',
  keywords: '키워드', registered_at: '등록일', modified_at: '최종수정일',
  header_text: '상단문구', detail_html: '본문상세설명',
  notice_code: '정보고시코드', notice_category: '정보고시카테고리',
  notice_info: '정보고시항목정보', notice_html: '정보고시html',
  market_gmarket: '지마켓', market_auction: '옥션', market_11st: '11번가',
  market_coupang: '쿠팡', market_smartstore: '스마트스토어',
  market_promo: '마켓홍보문구', market_gift: '사은품',
  certification_type: '인증구분', certification_info: '인증정보',
};

export const PRICE_FIELDS = new Set([
  'ownerclan_price', 'consumer_price', 'market_price',
  'shipping_fee', 'min_qty', 'max_qty', 'return_fee',
]);

export const MARKETS = [
  { key: 'market_gmarket', label: '지마켓', color: '#6cc24a' },
  { key: 'market_auction', label: '옥션', color: '#dc2626' },
  { key: 'market_11st', label: '11번가', color: '#ff5a2e' },
  { key: 'market_coupang', label: '쿠팡', color: '#2563eb' },
  { key: 'market_smartstore', label: '스마트스토어', color: '#10b981' },
] as const;

export const fmt = (n: number | null | undefined) => (n ?? 0).toLocaleString();

export function themeStyles(dark: boolean) {
  return {
    bg: dark ? 'bg-[#0f1117]' : 'bg-[#f5f6fa]',
    bgInner: dark ? 'bg-[#0f1117]' : 'bg-gray-50',
    card: dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e5e7eb]',
    cardHover: dark ? 'hover:bg-[#1f2029]' : 'hover:bg-gray-50',
    text1: dark ? 'text-white' : 'text-gray-900',
    text2: dark ? 'text-gray-400' : 'text-gray-500',
    text3: dark ? 'text-gray-500' : 'text-gray-400',
    border: dark ? 'border-[#2a2b35]' : 'border-[#e5e7eb]',
    divider: dark ? 'divide-[#2a2b35]' : 'divide-gray-100',
    rowHover: dark ? 'hover:bg-[#1f2029]' : 'hover:bg-gray-50',
    inputBg: dark ? 'bg-[#0f1117] border-[#2a2b35] text-white' : 'bg-white border-gray-200 text-gray-900',
  };
}
