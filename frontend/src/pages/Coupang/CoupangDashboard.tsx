import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ShoppingBag, Wallet, Package, Receipt } from 'lucide-react';
import api from '../../api/client';
import DateNavigator from '../../components/cpc/DateNavigator';
import DateRangePicker from '../../components/cpc/DateRangePicker';
import PeriodSelector from '../../components/cpc/PeriodSelector';
import { ymd } from '../../utils/format';
import type { PeriodMode, PeriodPreset } from '../../utils/periodRange';
import { resolveRange, yesterdayStr } from '../../utils/periodRange';

function todayStrKST(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
}

interface Row {
  no: number; login_id: string; seller_name: string;
  has_api_key: boolean; is_rocket_growth: boolean;
  product_count: number; approved_count: number; rejected_count: number;
  order_count: number; order_total: number; vat_total: number;
  last_synced: string | null;
}
interface DashResp {
  date_from: string; date_to: string;
  totals: { product_count: number; order_count: number; order_total: number; vat_total: number };
  rows: Row[];
}

const fmt = (n: number) => (n || 0).toLocaleString();
const COUPANG_COLOR = '#e6001b';

export default function CoupangDashboard() {
  const [data, setData] = useState<DashResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<PeriodMode>('monthly');
  const [date, setDate] = useState(todayStrKST());
  const [rangeStart, setRangeStart] = useState(todayStrKST());
  const [rangeEnd, setRangeEnd] = useState(todayStrKST());

  const { from, to } = resolveRange(mode, date, rangeStart, rangeEnd);

  const prevDate = () => {
    const d = new Date(date);
    if (mode === 'yearly') d.setFullYear(d.getFullYear() - 1);
    else if (mode === 'monthly') d.setMonth(d.getMonth() - 1);
    else d.setDate(d.getDate() - 1);
    setDate(ymd(d));
  };
  const nextDate = () => {
    const d = new Date(date);
    if (mode === 'yearly') d.setFullYear(d.getFullYear() + 1);
    else if (mode === 'monthly') d.setMonth(d.getMonth() + 1);
    else d.setDate(d.getDate() + 1);
    const next = ymd(d);
    if (next <= todayStrKST()) setDate(next);
  };
  const goToday = () => setDate(todayStrKST());

  const pickPeriod = (preset: PeriodPreset) => {
    const today = todayStrKST();
    if (preset === 'today') { setMode('daily'); setDate(today); }
    else if (preset === 'yesterday') { setMode('daily'); setDate(yesterdayStr()); }
    else if (preset === 'monthly') { setMode('monthly'); setDate(today); }
    else if (preset === 'yearly') { setMode('yearly'); setDate(today); }
    else if (preset === 'recent30') setMode('recent30');
    else setMode('range');
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<DashResp>('/coupang/dashboard/', { params: { date_from: from, date_to: to } });
      setData(data);
    } catch { /* noop */ } finally { setLoading(false); }
  }, [from, to]);
  useEffect(() => { load(); }, [load]);

  const t = data?.totals;
  const sums = (data?.rows || []).reduce((s, r) => {
    s.product_count += r.product_count || 0; s.order_count += r.order_count || 0;
    s.order_total += r.order_total || 0; s.vat_total += r.vat_total || 0;
    return s;
  }, { product_count: 0, order_count: 0, order_total: 0, vat_total: 0 });
  const cell = 'px-3 py-1.5';

  const Card = ({ icon, label, value, color }: any) => (
    <div className="bg-white border border-[#e0e0e0] rounded-lg px-4 py-3 flex items-center gap-3">
      <div className="p-2 rounded-lg" style={{ background: color + '1a', color }}>{icon}</div>
      <div><div className="text-[11px] text-[#888]">{label}</div><div className="text-[12px] font-bold text-[#333]">{value}</div></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#f5f6f8]">
      <div className="bg-white border-b border-[#e0e0e0] px-6 py-2 flex flex-wrap items-center gap-2">
        <div className="w-3 h-3 rounded-sm" style={{ background: COUPANG_COLOR }} />
        <h1 className="text-[12px] font-bold text-[#333]">쿠팡 대시보드</h1>
        {loading && <span className="text-[11px] text-[#999] animate-pulse">로딩중...</span>}
        <div className="ml-auto flex flex-wrap items-center gap-1.5 text-[12px]">
          <button onClick={load} className="inline-flex items-center gap-1 px-2.5 py-1 text-white rounded font-semibold" style={{ background: COUPANG_COLOR }}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> 새로고침
          </button>
          {mode === 'range' ? (
            <DateRangePicker startDate={rangeStart} endDate={rangeEnd}
              onStartChange={setRangeStart} onEndChange={setRangeEnd} onSearch={load} />
          ) : mode === 'recent30' ? (
            <span className="text-[12px] font-semibold text-[#333]">최근 30일</span>
          ) : (
            <DateNavigator date={date} onPrev={prevDate} onNext={nextDate} onToday={goToday} onDateChange={setDate} periodMode={mode} />
          )}
          <PeriodSelector mode={mode} date={date} onPick={pickPeriod} />
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-6 py-3 space-y-3">
        <div className="text-[12px] text-[#888]">기간: <b className="text-[#333]">{data?.date_from} ~ {data?.date_to}</b></div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          <Card icon={<Package size={18} />} color="#9333ea" label="등록상품" value={`${fmt(t?.product_count || 0)}개`} />
          <Card icon={<ShoppingBag size={18} />} color="#1e6fd9" label="주문건수" value={`${fmt(t?.order_count || 0)}건`} />
          <Card icon={<Wallet size={18} />} color={COUPANG_COLOR} label="주문금액(API, 수수료전)" value={`${fmt(t?.order_total || 0)}원`} />
        </div>

        {/* 부가세신고매출 — 선택기간과 무관한 '연간' 집계라 별도 그룹으로 분리(기존엔 기간KPI와 섞여 헷갈렸음) */}
        <div className="grid grid-cols-1 gap-2">
          <Card icon={<Receipt size={18} />} color="#555" label={`부가세신고매출 (${to.slice(0, 4)}년 연간 누적, 선택기간과 무관)`} value={`${fmt(t?.vat_total || 0)}원`} />
        </div>

        <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-[#f7f7f7] text-[#666]">
              <tr>
                <th className={`${cell} text-left`}>번호</th>
                <th className={`${cell} text-left`}>계정</th>
                <th className={`${cell} text-left`}>상호</th>
                <th className={`${cell} text-center`}>오픈API</th>
                <th className={`${cell} text-center`}>로켓그로스</th>
                <th className={`${cell} text-right`}>상품수</th>
                <th className={`${cell} text-right`}>승인/반려</th>
                <th className={`${cell} text-right`}>주문건수</th>
                <th className={`${cell} text-right`}>주문금액</th>
                <th className={`${cell} text-right`}>부가세매출(연)</th>
                <th className={`${cell} text-left`}>최근수집</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {(!data?.rows || data.rows.length === 0) ? (
                <tr><td colSpan={11} className="px-3 py-8 text-center text-[#aaa]">데이터 없음</td></tr>
              ) : (<>
                <tr className="bg-[#eef5ff] font-bold text-[#222] border-b-2 border-[#cfe0f5]">
                  <td className={cell}></td>
                  <td className={cell}>합계 ({data.rows.length}개)</td>
                  <td className={cell}></td>
                  <td className={cell}></td>
                  <td className={cell}></td>
                  <td className={`${cell} text-right`}>{fmt(sums.product_count)}</td>
                  <td className={cell}></td>
                  <td className={`${cell} text-right`}>{fmt(sums.order_count)}</td>
                  <td className={`${cell} text-right`} style={{ color: COUPANG_COLOR }}>{fmt(sums.order_total)}</td>
                  <td className={`${cell} text-right text-[#555]`}>{fmt(sums.vat_total)}</td>
                  <td className={cell}></td>
                </tr>
                {data.rows.map(r => (
                  <tr key={r.login_id} className="hover:bg-[#fafafa]">
                    <td className={`${cell} text-[#999] font-mono`}>{r.no}</td>
                    <td className={`${cell} font-mono`}>{r.login_id}</td>
                    <td className={cell}>{r.seller_name}</td>
                    <td className={`${cell} text-center`}>{r.has_api_key ? '✅' : <span className="text-[#ccc]">-</span>}</td>
                    <td className={`${cell} text-center`}>{r.is_rocket_growth ? 'O' : '-'}</td>
                    <td className={`${cell} text-right`}>{fmt(r.product_count)}</td>
                    <td className={`${cell} text-right`}>
                      <span className="text-green-600">{fmt(r.approved_count)}</span>
                      {r.rejected_count > 0 && <span className="text-red-500"> / {fmt(r.rejected_count)}</span>}
                    </td>
                    <td className={`${cell} text-right`}>{fmt(r.order_count)}</td>
                    <td className={`${cell} text-right font-semibold`} style={{ color: COUPANG_COLOR }}>{fmt(r.order_total)}</td>
                    <td className={`${cell} text-right text-[#555]`}>{fmt(r.vat_total)}</td>
                    <td className={`${cell} text-left text-[11px] text-[#999]`}>{r.last_synced ? r.last_synced.replace('T', ' ').slice(0, 16) : '-'}</td>
                  </tr>
                ))}
              </>)}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-[#aaa]">※ 주문금액 = 오픈API 기준(수수료 차감 전 총액). 부가세매출은 선택기간과 무관하게 해당 연도 전체 누적입니다.</p>
      </div>
    </div>
  );
}
