import { Award, Coins, Star, AlertCircle, Package, Clock, TrendingDown } from 'lucide-react';
import type { ElevenAccountSummary } from '../../api/elevenMy';
import { themeStyles, fmt } from '../Ownerclan/constants';

interface Props {
  accounts: ElevenAccountSummary[];
  dark: boolean;
  onSelectAccount?: (id: number) => void;
  selectedAccountId?: number;
}

function fmtMoney(n: number | null | undefined): string {
  if (n === null || n === undefined || n === 0) return '-';
  return fmt(n);
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '-';
  try {
    const d = new Date(s);
    return d.toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '-';
  }
}

export default function ElevenAccountSummaryCards({ accounts, dark, onSelectAccount, selectedAccountId }: Props) {
  const s = themeStyles(dark);

  if (!accounts || accounts.length === 0) {
    return (
      <div className={`rounded-xl border ${s.card} p-8 text-center ${s.text2}`}>
        집중관리 계정이 없습니다.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
      {accounts.map(a => {
        const selected = selectedAccountId === a.account_id;
        const isCash = a.cost_type === 'sellercash';
        const balanceLabel = isCash ? '셀러캐시' : '셀러포인트';
        const BalanceIcon = isCash ? Coins : Star;
        const balanceColor = isCash ? '#f59e0b' : '#8b5cf6';
        const statusColor = a.crawling_status === '정상' ? '#10b981' : a.crawling_status === '차단됨' ? '#ef4444' : '#9ca3af';

        return (
          <button
            key={a.account_id}
            onClick={() => onSelectAccount?.(a.account_id)}
            className={`text-left rounded-xl border ${s.card} p-3 transition-all hover:shadow-lg hover:scale-[1.01] ${selected ? 'ring-2 ring-blue-500 border-blue-500' : ''}`}
          >
            {/* Header */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="min-w-0 flex-1">
                <div className={`text-[12px] font-bold font-mono truncate ${s.text1}`}>{a.login_id}</div>
                {a.seller_name && <div className={`text-[10px] truncate ${s.text3}`}>{a.seller_name}</div>}
              </div>
              <span
                className="text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0"
                style={{ backgroundColor: `${statusColor}25`, color: statusColor }}
              >
                {a.crawling_status || '?'}
              </span>
            </div>

            {/* Grade */}
            <div className={`flex items-center gap-2 px-2 py-1.5 rounded-lg mb-2 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
              <Award size={14} className="text-amber-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-1">
                  <span className={`text-[12px] font-bold ${s.text1}`}>{a.grade ?? '?'}</span>
                  <span className={`text-[9px] ${s.text3}`}>등급</span>
                  {a.grade_message && <span className={`text-[9px] ${s.text2} truncate`}>· {a.grade_message}</span>}
                </div>
                {a.required_sales != null && a.required_sales > 0 && (
                  <div className={`text-[9px] ${s.text3}`}>다음 등급까지 {fmt(a.required_sales)}건</div>
                )}
              </div>
            </div>

            {/* Balance — 셀러캐시 + 셀러포인트 둘 다 표시 (데이터 그대로) */}
            <div className={`px-2 py-1.5 rounded-lg mb-2 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  <Coins size={12} className="text-amber-500 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className={`text-[9px] ${s.text3}`}>셀러캐시</div>
                    <div className={`text-[12px] font-bold ${s.text1} truncate`}>
                      {fmtMoney(a.office_cash ?? 0)}
                      <span className={`text-[9px] font-normal ${s.text3}`}>원</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <Star size={12} className="text-purple-500 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className={`text-[9px] ${s.text3}`}>셀러포인트</div>
                    <div className={`text-[12px] font-bold ${s.text1} truncate`}>
                      {fmtMoney(a.office_point ?? 0)}
                      <span className={`text-[9px] font-normal ${s.text3}`}>원</span>
                    </div>
                  </div>
                </div>
              </div>
              {(a.office_collected_at || a.balance_at) && (
                <div className={`text-[9px] ${s.text3} mt-1`}>수집: {fmtDate(a.office_collected_at || a.balance_at)}</div>
              )}
            </div>

            {/* 광고비 잔액 (office) + 30일 사용 */}
            <div className="flex items-center justify-between text-[10px] mb-1">
              <span className={`flex items-center gap-1 ${s.text3}`}>광고비 잔액</span>
              <span className={`font-semibold ${s.text1}`}>{fmtMoney(a.office_ad_balance)}원</span>
            </div>
            <div className="flex items-center justify-between text-[10px] mb-2">
              <span className={`flex items-center gap-1 ${s.text3}`}><TrendingDown size={10} />30일 사용</span>
              <span className={`font-semibold ${a.cost_30days > 0 ? 'text-red-500' : s.text3}`}>{fmtMoney(a.cost_30days)}</span>
            </div>

            {/* 상품 (셀러오피스 기준 + OpenAPI 기준) */}
            <div className={`px-2 py-1.5 rounded-lg mb-2 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
              <div className="flex items-center justify-between">
                <span className={`flex items-center gap-1 text-[10px] ${s.text3}`}><Package size={10} />등록가능</span>
                <span className={`text-[12px] font-bold ${a.available === 0 ? 'text-red-500' : s.text1}`}>
                  {a.available != null ? fmt(a.available) : '-'}<span className={`text-[9px] font-normal ${s.text3}`}>개</span>
                </span>
              </div>
              <div className={`flex items-center justify-between text-[9px] mt-0.5 ${s.text3}`}>
                <span>판매중 {a.products != null ? fmt(a.products) : '-'} / 한도 {a.product_limit != null ? fmt(a.product_limit) : '-'}</span>
                {a.banned != null && a.banned > 0 && <span className="text-red-500 font-bold">금지 {fmt(a.banned)}</span>}
              </div>
              <div className={`flex items-center justify-between text-[9px] mt-0.5 ${s.text3}`}>
                <span>OpenAPI 동기화 {fmt(a.product_count)}개</span>
                {a.last_synced && <span><Clock size={8} className="inline" /> {fmtDate(a.last_synced)}</span>}
              </div>
            </div>

            {/* 운영 상태 (셀러오피스 평가 텍스트) */}
            {(a.fulfillment || a.shipping || a.inquiry) && (
              <div className="grid grid-cols-3 gap-1 mb-2">
                {[
                  { l: '주문', v: a.fulfillment },
                  { l: '발송', v: a.shipping },
                  { l: '문의', v: a.inquiry },
                ].map((x) => {
                  const warn = x.v && x.v.includes('경고');
                  const ok = x.v && (x.v.includes('정상') || x.v.includes('우수'));
                  const color = warn ? '#ef4444' : ok ? '#10b981' : '#9ca3af';
                  return (
                    <div key={x.l} className="text-center px-1 py-0.5 rounded text-[9px]"
                         style={{ backgroundColor: `${color}15`, color }}>
                      <div className="font-bold">{x.l}</div>
                      <div className="truncate">{x.v || '-'}</div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 발송경고/미도착/가송장 뱃지 */}
            {((a.overdue ?? 0) > 0 || (a.undelivered ?? 0) > 0 || (a.draft ?? 0) > 0) && (
              <div className="flex flex-wrap gap-1 mb-1">
                {(a.overdue ?? 0) > 0 && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/15 text-red-500">발송기한경과 {a.overdue}</span>
                )}
                {(a.undelivered ?? 0) > 0 && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-orange-500/15 text-orange-500">미도착 {a.undelivered}</span>
                )}
                {(a.draft ?? 0) > 0 && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-yellow-500/15 text-yellow-600">가송장 {a.draft}</span>
                )}
              </div>
            )}

            {/* API key 미설정 / 셀러오피스 미수집 */}
            <div className="flex flex-wrap gap-1 mt-1">
              {!a.has_api_key && (
                <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-red-500/10 text-red-500 text-[9px] font-bold">
                  <AlertCircle size={9} /> API키 미설정
                </span>
              )}
              {!a.office_collected_at && (
                <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-500/10 text-gray-500 text-[9px]">
                  <AlertCircle size={9} /> 셀러오피스 미수집
                </span>
              )}
              {a.office_error && (
                <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-red-500/10 text-red-500 text-[9px] truncate max-w-full" title={a.office_error}>
                  오류
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
