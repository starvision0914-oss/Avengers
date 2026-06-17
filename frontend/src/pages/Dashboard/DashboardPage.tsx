import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Sun, Moon, Smartphone, Send, Inbox, Circle, Users, CheckCircle2, AlertTriangle, TrendingUp, TrendingDown, BarChart3, RefreshCw } from 'lucide-react';
import { getProfitDashboard, getCrawlerStats } from '../../api/cpc';
import { getSmsDevices, getOutboxHistory, getLatestSmsList } from '../../api/sms';
import { useTheme } from '../../hooks/useTheme';
import SmsSendModal from '../../components/SmsSendModal';
import BlockedAccountsAlert from '../../components/BlockedAccountsAlert';

const fmt = (n: number) => (n || 0).toLocaleString();
const fmtShort = (n: number) => {
  if (Math.abs(n) >= 100000000) return (n / 100000000).toFixed(1) + '억';
  if (Math.abs(n) >= 10000) return (n / 10000).toFixed(0) + '만';
  return fmt(n);
};

interface DashboardData {
  date: string; month: string;
  totals: any; sellers: any[]; eleven_sellers: any[]; eleven_totals: any;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { dark, toggle } = useTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [crawlerStats, setCrawlerStats] = useState<any[]>([]);
  const [smsDevices, setSmsDevices] = useState<any[]>([]);
  const [showSendModal, setShowSendModal] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      getProfitDashboard().catch(() => null),
      getCrawlerStats().catch(() => []),
      getSmsDevices().catch(() => []),
    ]).then(([dash, stats, devs]) => {
      if (dash) setData(dash);
      setCrawlerStats(stats || []);
      setSmsDevices(devs || []);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, []);

  if (loading && !data) return <div className={`p-8 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>로딩 중...</div>;
  if (!data) return <div className="p-8 text-red-500">데이터 로드 실패</div>;

  const { totals: t, sellers, eleven_sellers, eleven_totals } = data;
  const onlineDevs = smsDevices.filter((d: any) => d.is_online).length;

  // 도넛 차트 데이터
  const adPie = [
    { name: '지마켓', value: t.month_ad || 0, color: '#6cc24a' },
    { name: '11번가', value: t.eleven_month_cost || 0, color: '#ff5a2e' },
  ].filter(d => d.value > 0);
  const adPieTotal = adPie.reduce((a, b) => a + b.value, 0);

  const bg = dark ? 'bg-[#0f1117]' : 'bg-[#f5f6fa]';
  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e5e7eb]';
  const text1 = dark ? 'text-white' : 'text-gray-900';
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';
  const text3 = dark ? 'text-gray-500' : 'text-gray-400';

  return (
    <div className={`min-h-screen ${bg} transition-colors duration-300`}>
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-4 space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${text1}`}>수익 대시보드</h1>
            <p className={`text-xs ${text3} mt-0.5`}>{data.month} | {data.date} | 30초 자동 새로고침</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className={`p-2 rounded-lg ${dark ? 'hover:bg-[#2a2b35]' : 'hover:bg-gray-100'}`}>
              <RefreshCw size={16} className={loading ? 'animate-spin text-blue-500' : text2} />
            </button>
            <button onClick={toggle} className={`p-2 rounded-lg ${dark ? 'hover:bg-[#2a2b35] text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}>
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </div>

        {/* 차단 계정 알림 */}
        <BlockedAccountsAlert />

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
          <SumCard label="지마켓 매출" value={t.month_sales} sub={`주문 ${fmt(t.month_orders)}건`} color="#2563eb" dark={dark} />
          <SumCard label="지마켓 광고비" value={t.month_ad} sub={`CPC ${fmtShort(t.month_cpc)} / AI ${fmtShort(t.month_ai)}`} color="#6cc24a" dark={dark} />
          <SumCard label="11번가 매출" value={t.eleven_month_sales || 0} sub={`${eleven_totals?.account_count || 0}개 계정`} color="#0369a1" dark={dark} />
          <SumCard label="11번가 광고비" value={t.eleven_month_cost} sub={`순수익 ${fmtShort(t.eleven_month_net_profit || 0)}`} color="#ff5a2e" dark={dark} />
          <SumCard label="11번가 순수익" value={t.eleven_month_net_profit || 0} color={(t.eleven_month_net_profit || 0) >= 0 ? '#16a34a' : '#dc2626'} dark={dark} />
          <SumCard label="오늘 매출" value={t.today_sales} color="#059669" dark={dark} />
          <SumCard label="총 잔액" value={t.balance + (t.eleven_balance || 0)} sub={`G ${fmtShort(t.balance)} / 11 ${fmtShort(t.eleven_balance || 0)}`} color="#8b5cf6" dark={dark} />
          <SumCard label="지마켓+11번가 순이익" value={(t.net_profit || 0) + (t.eleven_month_net_profit || 0)} sub={`G ${fmtShort(t.net_profit || 0)} / 11 ${fmtShort(t.eleven_month_net_profit || 0)}`} color={((t.net_profit || 0) + (t.eleven_month_net_profit || 0)) >= 0 ? '#16a34a' : '#dc2626'} dark={dark} highlight />
        </div>

        {/* 중간 행: 도넛 + 크롤러 + SMS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* 광고비 비중 도넛 */}
          <div className={`rounded-xl border ${card} p-4`}>
            <div className={`text-[12px] font-bold ${text1} mb-2`}>광고비 비중</div>
            <div className="flex items-center gap-4">
              <div className="w-[140px] h-[140px] relative shrink-0">
                {adPie.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={adPie} dataKey="value" innerRadius={40} outerRadius={60} paddingAngle={2} strokeWidth={0}>
                        {adPie.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <Tooltip formatter={(v: any) => `${fmt(Number(v))}원`} contentStyle={{ fontSize: 11, background: dark ? '#1a1b23' : '#fff', border: '1px solid #333', borderRadius: 8 }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className={`w-full h-full flex items-center justify-center ${text3} text-xs`}>데이터 없음</div>
                )}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className={`text-[9px] ${text3}`}>합계</span>
                  <span className={`text-[12px] font-bold ${text1}`}>{fmtShort(adPieTotal)}</span>
                </div>
              </div>
              <div className="space-y-2">
                {adPie.map(d => (
                  <div key={d.name} className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: d.color }} />
                    <div>
                      <div className={`text-[11px] ${text2}`}>{d.name}</div>
                      <div className={`text-[12px] font-bold ${text1}`}>{fmt(d.value)}원</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 크롤러 계정 카드 */}
          <div className={`rounded-xl border ${card} p-4`}>
            <div className={`text-[12px] font-bold ${text1} mb-3`}>크롤러 계정</div>
            <div className="space-y-3">
              {crawlerStats.map((s: any) => (
                <div key={s.platform} onClick={() => navigate('/crawler')} className={`flex items-center justify-between p-2.5 rounded-lg cursor-pointer ${dark ? 'bg-[#0f1117] hover:bg-[#1f2029]' : 'bg-gray-50 hover:bg-gray-100'}`}>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-8 rounded-full" style={{ backgroundColor: s.platform === 'gmarket' ? '#6cc24a' : '#ff5a2e' }} />
                    <div>
                      <div className={`text-[12px] font-bold ${text1}`}>{s.label}</div>
                      <div className={`text-[10px] ${text3}`}>{s.total}개 계정</div>
                    </div>
                  </div>
                  <div className="text-right">
                    {s.all_set ? (
                      <span className="text-[10px] text-green-500 flex items-center gap-1"><CheckCircle2 size={12} /> {s.ready_pct}%</span>
                    ) : (
                      <span className="text-[10px] text-amber-500 flex items-center gap-1"><AlertTriangle size={12} /> {s.without_password}개 미설정</span>
                    )}
                    {s.blocked > 0 && <div className="text-[9px] text-red-500">차단 {s.blocked}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SMS 카드 */}
          <div className={`rounded-xl border ${card} p-4`}>
            <div className={`text-[12px] font-bold ${text1} mb-3 flex items-center justify-between`}>
              <span>문자 관리</span>
              <button onClick={() => setShowSendModal(true)} className="text-[10px] bg-blue-600 hover:bg-blue-700 text-white px-2.5 py-1 rounded font-semibold flex items-center gap-1">
                <Send size={10} /> 발송
              </button>
            </div>
            <div className="space-y-2">
              <div className={`flex items-center justify-between p-2.5 rounded-lg ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
                <div className="flex items-center gap-2">
                  <Smartphone size={16} className={onlineDevs > 0 ? 'text-green-500' : 'text-gray-400'} />
                  <span className={`text-[12px] ${text1}`}>디바이스</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Circle size={8} className={onlineDevs > 0 ? 'text-green-500 fill-green-500' : 'text-gray-400 fill-gray-400'} />
                  <span className={`text-[11px] font-bold ${onlineDevs > 0 ? 'text-green-500' : text3}`}>{onlineDevs}대 온라인</span>
                </div>
              </div>
              <button onClick={() => navigate('/sms')} className={`w-full text-left p-2.5 rounded-lg ${dark ? 'bg-[#0f1117] hover:bg-[#1f2029]' : 'bg-gray-50 hover:bg-gray-100'}`}>
                <span className={`text-[12px] ${text1}`}>문자 관리 페이지 →</span>
              </button>
            </div>
          </div>
        </div>

        {/* 지마켓 테이블 */}
        <div className={`rounded-xl border ${card} overflow-hidden`}>
          <div className="px-4 py-3 border-b" style={{ borderColor: dark ? '#2a2b35' : '#e5e7eb' }}>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-[#6cc24a]" />
              <span className={`text-[12px] font-bold ${text1}`}>지마켓 광고비</span>
              <span className={`text-[11px] ${text3}`}>{sellers.length}개 계정</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className={dark ? 'bg-[#0f1117]' : 'bg-gray-50'}>
                <tr className={text2}>
                  <th className="px-3 py-2 text-left font-medium">아이디</th>
                  <th className="px-3 py-2 text-center font-medium">AI</th>
                  <th className="px-3 py-2 text-right font-medium">잔액</th>
                  <th className="px-3 py-2 text-right font-medium">오늘 CPC</th>
                  <th className="px-3 py-2 text-right font-medium">오늘 AI</th>
                  <th className="px-3 py-2 text-right font-medium">오늘 합계</th>
                  <th className="px-3 py-2 text-right font-medium">{data.month} CPC</th>
                  <th className="px-3 py-2 text-right font-medium">{data.month} AI</th>
                  <th className="px-3 py-2 text-right font-medium">{data.month} 합계</th>
                </tr>
              </thead>
              <tbody className={`divide-y ${dark ? 'divide-[#2a2b35]' : 'divide-gray-100'}`}>
                {sellers.map((s: any) => (
                  <tr key={s.gmarket_id} className={dark ? 'hover:bg-[#1f2029]' : 'hover:bg-gray-50'}>
                    <td className={`px-3 py-2 font-medium ${text1}`}>{s.gmarket_id}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${s.ai_status === 'ON' ? 'bg-green-500/20 text-green-500' : s.ai_status === 'OFF' ? 'bg-red-500/20 text-red-400' : (dark ? 'bg-[#2a2b35] text-gray-500' : 'bg-gray-100 text-gray-400')}`}>{s.ai_status}</span>
                    </td>
                    <td className={`px-3 py-2 text-right ${text1}`}>{fmt(s.balance)}</td>
                    <td className={`px-3 py-2 text-right ${text2}`}>{fmt(s.today_cpc)}</td>
                    <td className={`px-3 py-2 text-right ${text2}`}>{fmt(s.today_ai)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${text1}`}>{fmt(s.today_ad)}</td>
                    <td className={`px-3 py-2 text-right ${text2}`}>{fmt(s.month_cpc)}</td>
                    <td className={`px-3 py-2 text-right ${text2}`}>{fmt(s.month_ai)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${text1}`}>{fmt(s.month_ad)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className={dark ? 'bg-[#0f1117]' : 'bg-gray-100'}>
                <tr className={`font-bold ${text1}`}>
                  <td className="px-3 py-2">합계</td>
                  <td></td>
                  <td className="px-3 py-2 text-right">{fmt(t.balance)}</td>
                  <td className="px-3 py-2 text-right">{fmt(t.today_cpc)}</td>
                  <td className="px-3 py-2 text-right">{fmt(t.today_ai)}</td>
                  <td className="px-3 py-2 text-right">{fmt(t.today_ad)}</td>
                  <td className="px-3 py-2 text-right">{fmt(t.month_cpc)}</td>
                  <td className="px-3 py-2 text-right">{fmt(t.month_ai)}</td>
                  <td className="px-3 py-2 text-right">{fmt(t.month_ad)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* 11번가 테이블 */}
        <div className={`rounded-xl border ${card} overflow-hidden`}>
          <div className="px-4 py-3 border-b" style={{ borderColor: dark ? '#2a2b35' : '#e5e7eb' }}>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-[#ff5a2e]" />
              <span className={`text-[12px] font-bold ${text1}`}>11번가 광고비</span>
              <span className={`text-[11px] ${text3}`}>{eleven_sellers.length}개 계정</span>
              <span className={`ml-auto text-[10px] ${text3}`}>잔액 합계: <span className={`font-bold ${text1}`}>{fmt(eleven_totals?.balance || 0)}원</span></span>
            </div>
          </div>
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-[12px]">
              <thead className={`sticky top-0 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
                <tr className={text2}>
                  <th className="px-3 py-2 text-left font-medium">아이디</th>
                  <th className="px-3 py-2 text-center font-medium">AI</th>
                  <th className="px-3 py-2 text-center font-medium">타입</th>
                  <th className="px-3 py-2 text-right font-medium">잔액</th>
                  <th className="px-3 py-2 text-right font-medium">오늘 광고비</th>
                  <th className="px-3 py-2 text-right font-medium">{data.month} 광고비</th>
                  <th className="px-3 py-2 text-right font-medium">매출</th>
                  <th className="px-3 py-2 text-right font-medium">순수익</th>
                  <th className="px-3 py-2 text-center font-medium">등급</th>
                  <th className="px-3 py-2 text-right font-medium">수집</th>
                </tr>
              </thead>
              <tbody className={`divide-y ${dark ? 'divide-[#2a2b35]' : 'divide-gray-100'}`}>
                {eleven_sellers.map((s: any) => (
                  <tr key={s.seller_id} className={dark ? 'hover:bg-[#1f2029]' : 'hover:bg-gray-50'}>
                    <td className={`px-3 py-1.5 font-medium ${text1}`}>{s.seller_id}</td>
                    <td className="px-3 py-1.5 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${s.ai_status === 'ON' ? 'bg-green-500/20 text-green-500' : s.ai_status === 'OFF' ? 'bg-red-500/20 text-red-400' : (dark ? 'bg-[#2a2b35] text-gray-500' : 'bg-gray-100 text-gray-400')}`}>{s.ai_status}</span>
                    </td>
                    <td className={`px-3 py-1.5 text-center text-[10px] ${text3}`}>{s.cost_type === 'sellercash' ? '캐시' : '포인트'}</td>
                    <td className={`px-3 py-1.5 text-right ${s.balance < 0 ? 'text-red-500' : text1}`}>{fmt(s.balance)}</td>
                    <td className={`px-3 py-1.5 text-right ${text2}`}>{fmt(s.today_cost)}</td>
                    <td className={`px-3 py-1.5 text-right font-semibold ${text1}`}>{fmt(s.month_cost)}</td>
                    <td className={`px-3 py-1.5 text-right ${text2}`}>{s.sales ? fmt(s.sales) : '-'}</td>
                    <td className={`px-3 py-1.5 text-right font-semibold ${(s.sales || s.month_cost) ? ((s.net_profit || 0) >= 0 ? 'text-green-600' : 'text-red-500') : text3}`}>{(s.sales || s.month_cost) ? fmt(s.net_profit) : '-'}</td>
                    <td className={`px-3 py-1.5 text-center ${text3} text-[10px]`}>{s.grade ?? '-'}{s.grade_message ? ` ${s.grade_message}` : ''}</td>
                    <td className={`px-3 py-1.5 text-right text-[10px] ${text3}`}>{s.collected_at ? new Date(s.collected_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : '-'}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className={`sticky bottom-0 ${dark ? 'bg-[#0f1117]' : 'bg-gray-100'}`}>
                <tr className={`font-bold ${text1}`}>
                  <td className="px-3 py-2" colSpan={3}>합계 ({eleven_sellers.length}개)</td>
                  <td className="px-3 py-2 text-right">{fmt(eleven_totals?.balance || 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(eleven_totals?.today_cost || 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(eleven_totals?.month_cost || 0)}</td>
                  <td className="px-3 py-2 text-right">{fmt(eleven_totals?.month_sales || 0)}</td>
                  <td className={`px-3 py-2 text-right ${(eleven_totals?.month_net_profit || 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}>{fmt(eleven_totals?.month_net_profit || 0)}</td>
                  <td></td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

      </div>

      <SmsSendModal open={showSendModal} onClose={() => setShowSendModal(false)} />
    </div>
  );
}

function SumCard({ label, value, sub, color, dark, highlight }: {
  label: string; value: number; sub?: string; color: string; dark: boolean; highlight?: boolean;
}) {
  const isNeg = value < 0;
  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e5e7eb]';
  return (
    <div className={`rounded-xl border ${card} p-3 md:p-4 transition-all hover:scale-[1.02]`}
      style={highlight ? { boxShadow: `inset 0 0 0 1px ${color}` } : undefined}>
      <div className={`text-[10px] md:text-[11px] font-medium mb-1 ${dark ? 'text-gray-500' : 'text-gray-400'}`}>{label}</div>
      <div className="text-[12px] md:text-[20px] font-bold flex items-center gap-1" style={{ color }}>
        {fmt(value)}<span className={`text-[10px] ${dark ? 'text-gray-600' : 'text-gray-300'}`}>원</span>
        {highlight && (isNeg ? <TrendingDown size={14} /> : <TrendingUp size={14} />)}
      </div>
      {sub && <div className={`text-[9px] md:text-[10px] mt-0.5 ${dark ? 'text-gray-600' : 'text-gray-400'}`}>{sub}</div>}
    </div>
  );
}
