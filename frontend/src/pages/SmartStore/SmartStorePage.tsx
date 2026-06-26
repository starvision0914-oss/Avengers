import { useEffect, useState, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { RefreshCw, Settings, TrendingUp, ShoppingBag, Lock, Package } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import {
  getAccounts, getDashboard, getProductStats,
  type SmartStoreAccount, type DashboardResponse, type AccountRow, type ProductStats,
} from '../../api/smartstore';
import AccountSettingsModal from './AccountSettingsModal';
import SmartStoreProductsTab from './SmartStoreProductsTab';

const fmt = (n: number) => (n || 0).toLocaleString();
const fmtW = (n: number) => {
  if (Math.abs(n) >= 100_000_000) return (n / 100_000_000).toFixed(1) + '억';
  if (Math.abs(n) >= 10_000) return (n / 10_000).toFixed(0) + '만';
  return fmt(n);
};

function StatCard({ label, value, sub, color, dark }: {
  label: string; value: string; sub?: string; color?: string; dark: boolean;
}) {
  const card = dark ? 'bg-[#1a1d27] border-[#2d3144]' : 'bg-white border-gray-200';
  return (
    <div className={`${card} border rounded-xl p-4 flex flex-col gap-1`}>
      <div className={`text-xs ${dark ? 'text-gray-400' : 'text-gray-500'}`}>{label}</div>
      <div className={`text-2xl font-bold ${color || (dark ? 'text-white' : 'text-gray-800')}`}>{value}</div>
      {sub && <div className={`text-xs ${dark ? 'text-gray-500' : 'text-gray-400'}`}>{sub}</div>}
    </div>
  );
}

export default function SmartStorePage() {
  const { dark } = useTheme();
  const [tab, setTab] = useState<'dashboard' | 'products'>('dashboard');
  const [accounts, setAccounts] = useState<SmartStoreAccount[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [dash, setDash] = useState<DashboardResponse | null>(null);
  const [prodStats, setProdStats] = useState<ProductStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const today = new Date();
  const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
  const yesterday = new Date(today.getTime() - 86400000).toISOString().slice(0, 10);

  const [dateStart, setDateStart] = useState(startOfMonth);
  const [dateEnd, setDateEnd] = useState(yesterday);

  const loadAccounts = useCallback(async () => {
    const data = await getAccounts().catch(() => []);
    setAccounts(data);
  }, []);

  const loadDash = useCallback(async () => {
    setLoading(true);
    try {
      const [data, ps] = await Promise.all([
        getDashboard({
          start: dateStart,
          end: dateEnd,
          account_id: selectedIds.length > 0 ? selectedIds : undefined,
        }),
        getProductStats(),
      ]);
      setDash(data);
      setProdStats(ps);
    } finally {
      setLoading(false);
    }
  }, [dateStart, dateEnd, selectedIds]);

  useEffect(() => { loadAccounts(); }, [loadAccounts]);
  useEffect(() => { if (tab === 'dashboard') loadDash(); }, [loadDash, tab]);

  const toggleAccount = (id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const bg = dark ? 'bg-[#0f1117] text-gray-100' : 'bg-[#f5f6fa] text-gray-800';
  const card = dark ? 'bg-[#1a1d27] border-[#2d3144]' : 'bg-white border-gray-200';
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';
  const hdr = dark ? 'bg-[#13151f]' : 'bg-gray-50';

  const s = dash?.summary;
  const byAccount: AccountRow[] = dash?.by_account || [];
  const daily = dash?.daily || [];

  const chartData = daily.map(d => ({
    date: d.date.slice(5),
    정산: d.settlement,
    광고비: d.ad_cost,
  }));

  const TABS = [
    { key: 'dashboard', label: '대시보드', icon: TrendingUp },
    { key: 'products', label: '상품관리', icon: Package },
  ] as const;

  return (
    <div className={`min-h-screen ${bg} p-4`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShoppingBag size={22} className="text-[#03C75A]" />
          <h1 className="text-xl font-bold">스마트스토어</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(true)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border ${card} ${text2} hover:text-green-500`}
          >
            <Settings size={14} /> 계정설정
          </button>
          {tab === 'dashboard' && (
            <button
              onClick={loadDash}
              disabled={loading}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-[#03C75A] text-white hover:bg-green-600"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 새로고침
            </button>
          )}
        </div>
      </div>

      {/* 탭 */}
      <div className={`flex gap-1 mb-4 p-1 rounded-xl ${dark ? 'bg-[#1a1d27]' : 'bg-white'} border ${dark ? 'border-[#2d3144]' : 'border-gray-200'} w-fit`}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === key
                ? 'bg-[#03C75A] text-white'
                : dark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* ── 대시보드 탭 ── */}
      {tab === 'dashboard' && (
        <>
          {/* 계정 필터 */}
          <div className={`${card} border rounded-xl p-3 mb-4`}>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedIds([])}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  selectedIds.length === 0
                    ? 'bg-[#03C75A] text-white'
                    : dark ? 'bg-[#2d3144] text-gray-300' : 'bg-gray-100 text-gray-600'
                }`}
              >
                전체
              </button>
              {accounts.map(a => (
                <button
                  key={a.id}
                  onClick={() => toggleAccount(a.id)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1 ${
                    selectedIds.includes(a.id)
                      ? 'bg-[#03C75A] text-white'
                      : dark ? 'bg-[#2d3144] text-gray-300' : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {!a.has_pw && <Lock size={10} className="opacity-60" />}
                  {a.display_name}
                </button>
              ))}
            </div>
          </div>

          {/* 기간 선택 */}
          <div className={`${card} border rounded-xl p-3 mb-4 flex items-center gap-3`}>
            <span className={`text-xs ${text2}`}>기간</span>
            <input
              type="date"
              value={dateStart}
              onChange={e => setDateStart(e.target.value)}
              className={`text-sm px-2 py-1 rounded border ${dark ? 'bg-[#2d3144] border-[#3d4464] text-gray-200' : 'bg-white border-gray-300'}`}
            />
            <span className={text2}>~</span>
            <input
              type="date"
              value={dateEnd}
              onChange={e => setDateEnd(e.target.value)}
              className={`text-sm px-2 py-1 rounded border ${dark ? 'bg-[#2d3144] border-[#3d4464] text-gray-200' : 'bg-white border-gray-300'}`}
            />
            <button onClick={loadDash} className="px-3 py-1 bg-[#03C75A] text-white text-xs rounded-lg">
              조회
            </button>
          </div>

          {/* KPI 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard dark={dark} label="결제금액" value={fmtW(s?.total_sales || 0) + '원'} sub={`주문 ${fmt(s?.total_orders || 0)}건`} />
            <StatCard dark={dark} label="정산예정" value={fmtW(s?.total_settlement || 0) + '원'} color="text-[#03C75A]" sub={`취소 ${fmtW(s?.total_cancel || 0)}원`} />
            <StatCard dark={dark} label="광고비" value={fmtW(s?.total_ad_cost || 0) + '원'} color="text-orange-400" sub={`클릭 ${fmt(s?.total_clicks || 0)}회`} />
            <StatCard dark={dark} label="광고 ROAS" value={s?.roas != null ? s.roas + '%' : '-'} color={s?.roas != null && s.roas >= 200 ? 'text-[#03C75A]' : 'text-red-400'} sub="정산÷광고비" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            <div className={`${card} border rounded-xl p-4`}>
              <h3 className="text-sm font-semibold mb-3">일별 정산 추이</h3>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke={dark ? '#2d3144' : '#f0f0f0'} />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: dark ? '#6b7280' : '#9ca3af' }} />
                    <YAxis tickFormatter={v => fmtW(v)} tick={{ fontSize: 10, fill: dark ? '#6b7280' : '#9ca3af' }} />
                    <Tooltip
                      formatter={(v: number | string) => fmt(Number(v)) + '원'}
                      contentStyle={{ backgroundColor: dark ? '#1a1d27' : '#fff', border: 'none', borderRadius: 8 }}
                      labelStyle={{ color: dark ? '#e5e7eb' : '#374151' }}
                    />
                    <Bar dataKey="정산" fill="#03C75A" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="광고비" fill="#f97316" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className={`flex items-center justify-center h-48 ${text2} text-sm`}>
                  데이터 없음 — 크롤링 후 표시됩니다
                </div>
              )}
            </div>

            <div className={`${card} border rounded-xl p-4`}>
              <h3 className="text-sm font-semibold mb-3">계정별 현황</h3>
              {byAccount.length > 0 ? (
                <div className="overflow-auto max-h-52">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className={`${hdr} text-left`}>
                        <th className="px-2 py-1.5">계정</th>
                        <th className="px-2 py-1.5 text-right">정산</th>
                        <th className="px-2 py-1.5 text-right">광고비</th>
                        <th className="px-2 py-1.5 text-right">ROAS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {byAccount.map(row => (
                        <tr key={row.account_id} className={`border-t ${dark ? 'border-[#2d3144]' : 'border-gray-100'}`}>
                          <td className={`px-2 py-1.5 font-medium ${dark ? 'text-gray-200' : 'text-gray-700'}`}>{row.account_name}</td>
                          <td className="px-2 py-1.5 text-right text-[#03C75A]">{fmtW(row.settlement)}</td>
                          <td className="px-2 py-1.5 text-right text-orange-400">{fmtW(row.ad_cost)}</td>
                          <td className={`px-2 py-1.5 text-right font-medium ${
                            row.roas != null && row.roas >= 200 ? 'text-[#03C75A]' : row.roas != null ? 'text-red-400' : text2
                          }`}>{row.roas != null ? row.roas + '%' : '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className={`flex items-center justify-center h-48 ${text2} text-sm`}>
                  {accounts.filter(a => !a.has_pw).length > 0
                    ? `${accounts.filter(a => !a.has_pw).length}개 계정 비밀번호 미등록`
                    : '데이터 없음'}
                </div>
              )}
            </div>
          </div>

          {/* 비밀번호 미등록 경고 */}
          {accounts.filter(a => !a.has_pw).length > 0 && (
            <div className={`${card} border border-yellow-500/30 rounded-xl p-4 mb-4 flex items-start gap-3`}>
              <Lock size={18} className="text-yellow-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-semibold text-yellow-400 mb-1">비밀번호 미등록 계정</div>
                <div className={`text-xs ${text2} flex flex-wrap gap-1.5`}>
                  {accounts.filter(a => !a.has_pw).map(a => (
                    <span key={a.id} className={`px-2 py-0.5 rounded ${dark ? 'bg-[#2d3144]' : 'bg-gray-100'}`}>{a.display_name}</span>
                  ))}
                </div>
                <button onClick={() => setShowSettings(true)} className="mt-2 text-xs text-yellow-400 underline">
                  계정설정에서 비밀번호 입력 →
                </button>
              </div>
            </div>
          )}

          {/* 상품 현황 요약 */}
          {prodStats && prodStats.total > 0 && (
            <div className={`${card} border rounded-xl p-4`}>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Package size={16} className="text-[#03C75A]" />
                상품 현황
                <span className={`text-xs ${text2}`}>(총 {fmt(prodStats.total)}개)</span>
                <button onClick={() => setTab('products')} className="ml-auto text-xs text-[#03C75A] underline">
                  상품관리 →
                </button>
              </h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                {Object.entries(prodStats.by_status).map(([st, cnt]) => {
                  const label: Record<string, string> = { SALE: '판매중', SUSPENSION: '판매중지', OUTOFSTOCK: '품절', WAIT: '대기', PROHIBITION: '금지' };
                  const color = st === 'SALE' ? 'text-[#03C75A]' : st === 'SUSPENSION' ? 'text-red-400' : 'text-orange-400';
                  return (
                    <div key={st} className={`${dark ? 'bg-[#13151f]' : 'bg-gray-50'} rounded-lg p-2.5 text-center`}>
                      <div className={`text-xs ${text2} mb-0.5`}>{label[st] || st}</div>
                      <div className={`text-lg font-bold ${color}`}>{fmt(cnt)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── 상품관리 탭 ── */}
      {tab === 'products' && (
        <SmartStoreProductsTab accounts={accounts} />
      )}

      {/* 계정설정 모달 */}
      {showSettings && (
        <AccountSettingsModal
          accounts={accounts}
          onClose={() => { setShowSettings(false); loadAccounts(); }}
          onSaved={loadAccounts}
        />
      )}
    </div>
  );
}
