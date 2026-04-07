import { useEffect, useState } from 'react';
import { getGmarketSummary, getElevenSummary, getGmarketSnapshots, getElevenCosts, triggerCrawl } from '../../api/crawler';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { ChevronLeft, ChevronRight, Play, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import dayjs from 'dayjs';

type PeriodMode = 'daily' | 'monthly';

export default function CPCDashboard() {
  const [platform, setPlatform] = useState<'gmarket' | '11st'>('gmarket');
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [periodMode, setPeriodMode] = useState<PeriodMode>('daily');
  const [gmData, setGmData] = useState<any>({ totals: {}, sellers: [] });
  const [elData, setElData] = useState<any>({ totals: {}, sellers: [] });
  const [crawling, setCrawling] = useState('');
  const [selectedSeller, setSelectedSeller] = useState<string | null>(null);

  const load = () => {
    if (periodMode === 'daily') {
      getGmarketSummary({ date }).then(setGmData).catch(() => {});
      getElevenSummary({ date }).then(setElData).catch(() => {});
    } else {
      const from = dayjs(date).startOf('month').format('YYYY-MM-DD');
      const to = dayjs(date).endOf('month').format('YYYY-MM-DD');
      getGmarketSummary({ date_from: from, date_to: to }).then(setGmData).catch(() => {});
      getElevenSummary({ date_from: from, date_to: to }).then(setElData).catch(() => {});
    }
  };

  useEffect(() => { load(); }, [date, periodMode]);

  const moveDate = (dir: number) => {
    setDate(prev => dayjs(prev).add(dir, periodMode === 'daily' ? 'day' : 'month').format('YYYY-MM-DD'));
  };
  const goToday = () => setDate(dayjs().format('YYYY-MM-DD'));
  const isToday = date === dayjs().format('YYYY-MM-DD');
  const isFuture = dayjs(date).isAfter(dayjs(), 'day');

  const dateLabel = periodMode === 'daily'
    ? dayjs(date).format('YYYY-MM-DD (ddd)')
    : dayjs(date).format('YYYY년 MM월');

  const handleCrawl = async (p: string) => {
    setCrawling(p);
    await triggerCrawl({ platform: p, type: 'cost' });
    toast.success(`${p === 'gmarket' ? '지마켓' : '11번가'} 크롤링 시작`);
    setTimeout(() => { setCrawling(''); load(); }, 15000);
  };

  const data = platform === 'gmarket' ? gmData : elData;
  const sellers = data.sellers || [];
  const totals = data.totals || {};

  const fmt = (v: number) => (v || 0).toLocaleString();

  return (
    <div className="max-w-[1800px] mx-auto px-4 py-4 space-y-3">
      {/* Header: Platform Tabs + Date Nav + Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Platform Tabs */}
          <div className="flex border border-[#e0e0e0] rounded overflow-hidden">
            <button onClick={() => setPlatform('gmarket')}
              className={`px-5 py-2 text-[13px] font-semibold ${platform === 'gmarket' ? 'bg-[#1a73e8] text-white' : 'bg-white text-[#555] hover:bg-gray-50'}`}>
              지마켓
            </button>
            <button onClick={() => setPlatform('11st')}
              className={`px-5 py-2 text-[13px] font-semibold border-l border-[#e0e0e0] ${platform === '11st' ? 'bg-[#e67700] text-white' : 'bg-white text-[#555] hover:bg-gray-50'}`}>
              11번가
            </button>
          </div>

          {/* Date Navigator */}
          <div className="flex items-center gap-1">
            <button onClick={() => moveDate(-1)} className="p-1.5 hover:bg-gray-100 rounded text-[#666]"><ChevronLeft size={18} /></button>
            <div className="flex items-center gap-2">
              <input type="date" value={date} max={dayjs().format('YYYY-MM-DD')}
                onChange={e => setDate(e.target.value)}
                className="text-[13px] font-semibold text-[#333] bg-transparent border-none cursor-pointer" />
            </div>
            <button onClick={() => moveDate(1)} disabled={isFuture}
              className="p-1.5 hover:bg-gray-100 rounded text-[#666] disabled:opacity-20"><ChevronRight size={18} /></button>
            <button onClick={goToday} disabled={isToday}
              className="ml-1 px-3 py-1 text-[11px] border border-[#ddd] rounded hover:bg-gray-50 disabled:opacity-30">오늘</button>
          </div>

          {/* Period Mode */}
          <div className="flex border border-[#e0e0e0] rounded overflow-hidden">
            <button onClick={() => setPeriodMode('daily')}
              className={`px-3 py-1 text-[11px] ${periodMode === 'daily' ? 'bg-[#333] text-white' : 'bg-white text-[#666]'}`}>일별</button>
            <button onClick={() => setPeriodMode('monthly')}
              className={`px-3 py-1 text-[11px] border-l border-[#e0e0e0] ${periodMode === 'monthly' ? 'bg-[#333] text-white' : 'bg-white text-[#666]'}`}>월별</button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button onClick={() => handleCrawl(platform)} disabled={!!crawling}
            className="flex items-center gap-1 px-3 py-1.5 bg-[#1a73e8] text-white rounded text-[12px] hover:bg-[#1557b0] disabled:opacity-50">
            {crawling ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} />}
            수집
          </button>
          <button onClick={load} className="p-1.5 hover:bg-gray-100 rounded text-[#666]"><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* Summary Bar */}
      <div className="bg-white border border-[#e0e0e0] rounded-lg">
        <div className="flex items-center justify-between px-5 py-3">
          <div className="flex items-center gap-6 text-[13px]">
            {platform === 'gmarket' ? (
              <>
                <div><span className="text-[#888]">총잔액: </span><span className="font-semibold text-[#00a651]">{fmt(totals.balance)}</span></div>
                <div><span className="text-[#888]">총CPC: </span><span className="font-semibold text-[#1a73e8]">{fmt(totals.cpc_spend)}</span></div>
                <div><span className="text-[#888]">총AI: </span><span className="font-semibold text-[#7c3aed]">{fmt(totals.ai_spend)}</span></div>
                <div><span className="text-[#888]">총광고비: </span><span className="font-bold text-[#e04040]">{fmt(totals.ad_total)}</span></div>
              </>
            ) : (
              <>
                <div><span className="text-[#888]">총CPC: </span><span className="font-semibold text-[#e67700]">{fmt(totals.cpc_spend)}</span></div>
                <div><span className="text-[#888]">계정수: </span><span className="font-semibold">{totals.seller_count || 0}</span></div>
              </>
            )}
          </div>
          <div className="text-[11px] text-[#aaa]">
            {data.date && `기준일: ${data.date}`}
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white border border-[#e0e0e0] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]" style={{ fontVariantNumeric: 'tabular-nums' }}>
            <thead>
              <tr className="bg-[#f7f7f7] border-b border-[#e0e0e0]">
                <th className="px-3 py-[7px] text-center text-[#999] font-normal w-8">#</th>
                <th className="px-3 py-[7px] text-left text-[#555] font-semibold min-w-[120px]">셀러명</th>
                {platform === 'gmarket' ? (
                  <>
                    <th className="px-3 py-[7px] text-center text-[#555] font-semibold">광고상태</th>
                    <th className="px-3 py-[7px] text-right text-[#555] font-semibold">잔액</th>
                    <th className="px-3 py-[7px] text-right text-[#555] font-semibold">CPC</th>
                    <th className="px-3 py-[7px] text-center text-[#555] font-semibold">AI</th>
                    <th className="px-3 py-[7px] text-right text-[#555] font-bold">광고비합</th>
                    <th className="px-3 py-[7px] text-left text-[#555] font-semibold">등급</th>
                    <th className="px-3 py-[7px] text-left text-[#999] font-normal">수집</th>
                  </>
                ) : (
                  <>
                    <th className="px-3 py-[7px] text-right text-[#555] font-semibold">CPC</th>
                    <th className="px-3 py-[7px] text-right text-[#555] font-semibold">충전</th>
                    <th className="px-3 py-[7px] text-right text-[#555] font-semibold">잔액</th>
                    <th className="px-3 py-[7px] text-right text-[#555] font-semibold">건수</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {sellers.length > 0 ? sellers.map((s: any, i: number) => (
                <tr key={s.seller_id} onClick={() => setSelectedSeller(s.seller_id === selectedSeller ? null : s.seller_id)}
                  className={`border-b border-[#eee] cursor-pointer transition-colors ${
                    selectedSeller === s.seller_id ? 'bg-[#e8f5e9]' : i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'
                  } hover:bg-[#f0f7f0]`}>
                  <td className="px-3 py-[7px] text-center text-[#999]">{i + 1}</td>
                  <td className="px-3 py-[7px] text-left font-semibold text-[#222]">
                    <div className="flex items-center gap-1.5">
                      {platform === 'gmarket' && s.balance < 100000 && (
                        <span className="w-2 h-2 rounded-full bg-[#e04040] animate-pulse" title={`잔액: ${fmt(s.balance)}`} />
                      )}
                      {s.seller_id}
                    </div>
                  </td>
                  {platform === 'gmarket' ? (
                    <>
                      {/* 광고상태 */}
                      <td className="px-3 py-[7px] text-center">
                        {s.cpc_status ? (
                          <div className="flex items-center justify-center gap-1 text-[10px]">
                            <span className="px-1 py-0.5 rounded bg-blue-50 text-blue-700">간편 {s.cpc_status.cpc2_on}<span className="text-green-600">ON</span>/{s.cpc_status.cpc2_off}<span className="text-red-500">OFF</span></span>
                          </div>
                        ) : <span className="text-[#ccc] text-[10px]">-</span>}
                      </td>
                      <td className="px-3 py-[7px] text-right text-[#00a651]">{fmt(s.balance)}</td>
                      <td className={`px-3 py-[7px] text-right ${s.cpc_spend ? 'text-[#1a73e8]' : 'text-[#ccc]'}`}>{fmt(s.cpc_spend)}</td>
                      {/* AI 상태 */}
                      <td className="px-3 py-[7px] text-center">
                        {s.ai_status ? (
                          <div className="flex flex-col items-center gap-0.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${s.ai_status.actual_status === 'ON' ? 'bg-[#e8f5e9] text-[#00a651]' : 'bg-[#ffeef0] text-[#e04040]'}`}>
                              {s.ai_status.actual_status}
                            </span>
                            {s.ai_status.start_date && <span className="text-[9px] text-[#999]">{s.ai_status.start_date}</span>}
                          </div>
                        ) : (
                          <span className={`text-[10px] ${s.ai_spend ? 'text-[#7c3aed]' : 'text-[#ccc]'}`}>{fmt(s.ai_spend)}</span>
                        )}
                      </td>
                      <td className={`px-3 py-[7px] text-right font-bold ${s.ad_total ? 'text-[#1557b0]' : 'text-[#ccc]'}`}>{fmt(s.ad_total)}</td>
                      {/* 등급 */}
                      <td className="px-3 py-[7px] text-left text-[10px]">
                        {s.grade_info ? (
                          <div>
                            <span className={`font-semibold ${(s.grade_info.max_item_count || 0) >= 10000 ? 'text-[#e04040]' : 'text-[#333]'}`}>
                              {s.grade_info.seller_grade}
                            </span>
                            <span className="text-[#999] ml-1">({(s.grade_info.max_item_count || 0).toLocaleString()})</span>
                          </div>
                        ) : <span className="text-[#ccc]">-</span>}
                      </td>
                      <td className="px-3 py-[7px] text-left text-[10px] text-[#aaa]">
                        {s.collected_at ? new Date(s.collected_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : ''}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className={`px-3 py-[7px] text-right ${s.cpc_spend ? 'text-[#e67700] font-semibold' : 'text-[#ccc]'}`}>{fmt(s.cpc_spend)}</td>
                      <td className={`px-3 py-[7px] text-right ${s.charge ? 'text-[#00a651]' : 'text-[#ccc]'}`}>{fmt(s.charge)}</td>
                      <td className="px-3 py-[7px] text-right text-[#333]">{fmt(s.balance)}</td>
                      <td className="px-3 py-[7px] text-right text-[#999]">{s.tx_count || 0}</td>
                    </>
                  )}
                </tr>
              )) : (
                <tr>
                  <td colSpan={platform === 'gmarket' ? 9 : 6} className="px-4 py-12 text-center text-[#aaa]">
                    {date} 수집된 데이터가 없습니다. 수집 버튼을 클릭하세요.
                  </td>
                </tr>
              )}
            </tbody>
            {sellers.length > 0 && (
              <tfoot>
                <tr className="bg-[#f7f7f7] border-t-2 border-[#ddd] font-bold text-[12px]">
                  <td className="px-3 py-[8px] text-center text-[#999]">#</td>
                  <td className="px-3 py-[8px] text-left text-[#333]">합계 ({sellers.length})</td>
                  {platform === 'gmarket' ? (
                    <>
                      <td className="px-3 py-[8px]"></td>{/* 광고상태 */}
                      <td className="px-3 py-[8px] text-right text-[#00a651]">{fmt(totals.balance)}</td>
                      <td className="px-3 py-[8px] text-right text-[#1a73e8]">{fmt(totals.cpc_spend)}</td>
                      <td className="px-3 py-[8px] text-center text-[#7c3aed]">{fmt(totals.ai_spend)}</td>
                      <td className="px-3 py-[8px] text-right text-[#e04040]">{fmt(totals.ad_total)}</td>
                      <td className="px-3 py-[8px]"></td>{/* 등급 */}
                      <td className="px-3 py-[8px]"></td>{/* 수집 */}
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-[8px] text-right text-[#e67700]">{fmt(totals.cpc_spend)}</td>
                      <td className="px-3 py-[8px] text-right text-[#00a651]">{fmt(sellers.reduce((s: number, d: any) => s + (d.charge || 0), 0))}</td>
                      <td className="px-3 py-[8px] text-right">{fmt(sellers.reduce((s: number, d: any) => s + (d.balance || 0), 0))}</td>
                      <td className="px-3 py-[8px] text-right text-[#999]">{sellers.reduce((s: number, d: any) => s + (d.tx_count || 0), 0)}</td>
                    </>
                  )}
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* Chart */}
      {sellers.length > 0 && (
        <div className="bg-white border border-[#e0e0e0] rounded-lg p-5">
          <h3 className="text-[13px] font-semibold text-[#333] mb-3">계정별 광고비</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={sellers.map((s: any) => ({
              name: s.seller_id,
              CPC: s.cpc_spend || 0,
              ...(platform === 'gmarket' ? { AI: s.ai_spend || 0 } : { 충전: s.charge || 0 }),
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `${v.toLocaleString()}원`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {platform === 'gmarket' ? (
                <>
                  <Bar dataKey="CPC" fill="#1a73e8" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="AI" fill="#7c3aed" radius={[2, 2, 0, 0]} />
                </>
              ) : (
                <>
                  <Bar dataKey="CPC" fill="#e67700" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="충전" fill="#00a651" radius={[2, 2, 0, 0]} />
                </>
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
