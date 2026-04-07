import { useEffect, useState } from 'react';
import { getDailyCosts, getDeposits, getChart, createDailyCost, createDeposit, createTransaction, getTransactions } from '../../api/cpc';
import { getAccounts } from '../../api/accounts';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid, Legend } from 'recharts';
import { Plus, TrendingUp } from 'lucide-react';
import dayjs from 'dayjs';
import toast from 'react-hot-toast';
import type { SellerAccount } from '../../types';

export default function CPCDashboard() {
  const [costs, setCosts] = useState<any>({ results: [] });
  const [chartData, setChartData] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<SellerAccount[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [showDepositForm, setShowDepositForm] = useState(false);
  const [form, setForm] = useState({ seller: '', date: dayjs().format('YYYY-MM-DD'), cpc_cost: 0, ai_cost: 0, total_cost: 0, clicks: 0, impressions: 0, conversions: 0, roas: 0 });
  const [depositForm, setDepositForm] = useState({ seller: '', deposit_date: dayjs().format('YYYY-MM-DD'), deposited_amount: 0, balance: 0, memo: '' });

  const load = () => {
    getDailyCosts().then(setCosts);
    getChart().then(setChartData);
    getAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || []));
  };

  useEffect(() => { load(); }, []);

  const handleSubmitCost = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDailyCost({ ...form, total_cost: Number(form.cpc_cost) + Number(form.ai_cost) });
      toast.success('광고비 추가 완료');
      setShowForm(false);
      load();
    } catch { toast.error('추가 실패'); }
  };

  const handleSubmitDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDeposit(depositForm);
      toast.success('입금 기록 추가 완료');
      setShowDepositForm(false);
      load();
    } catch { toast.error('추가 실패'); }
  };

  const costList = costs.results || costs;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">CPC 광고비 대시보드</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowDepositForm(true)} className="flex items-center gap-1 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
            <Plus size={16} /> 입금 기록
          </button>
          <button onClick={() => setShowForm(true)} className="flex items-center gap-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
            <Plus size={16} /> 광고비 입력
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><TrendingUp size={20} /> 일별 광고비 추이</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis tickFormatter={(v) => `${(v/10000).toFixed(0)}만`} />
              <Tooltip formatter={(v: number) => `${v.toLocaleString()}원`} />
              <Legend />
              <Bar dataKey="total_cpc" name="CPC" fill="#3B82F6" />
              <Bar dataKey="total_ai" name="AI" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center text-gray-400 py-12">데이터를 입력하면 차트가 표시됩니다.</div>
        )}
      </div>

      {/* Cost Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">날짜</th>
              <th className="px-4 py-3 text-left">셀러</th>
              <th className="px-4 py-3 text-right">CPC</th>
              <th className="px-4 py-3 text-right">AI</th>
              <th className="px-4 py-3 text-right">합계</th>
              <th className="px-4 py-3 text-right">클릭</th>
              <th className="px-4 py-3 text-right">ROAS</th>
            </tr>
          </thead>
          <tbody>
            {Array.isArray(costList) && costList.length > 0 ? costList.map((c: any) => (
              <tr key={c.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">{c.date}</td>
                <td className="px-4 py-3">{c.seller_name || c.seller_id_display}</td>
                <td className="px-4 py-3 text-right">{c.cpc_cost?.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{c.ai_cost?.toLocaleString()}</td>
                <td className="px-4 py-3 text-right font-semibold">{c.total_cost?.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{c.clicks?.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{c.roas}%</td>
              </tr>
            )) : (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">광고비 데이터가 없습니다. 위의 버튼으로 입력하세요.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add Cost Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSubmitCost} className="bg-white rounded-lg p-6 w-[480px] max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">광고비 입력</h2>
            <div className="space-y-3">
              <select value={form.seller} onChange={e => setForm({...form, seller: e.target.value})} className="w-full border rounded px-3 py-2" required>
                <option value="">셀러 선택</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.seller_name} ({a.seller_id})</option>)}
              </select>
              <input type="date" value={form.date} onChange={e => setForm({...form, date: e.target.value})} className="w-full border rounded px-3 py-2" />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500">CPC 비용</label>
                  <input type="number" value={form.cpc_cost} onChange={e => setForm({...form, cpc_cost: +e.target.value})} className="w-full border rounded px-3 py-2" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">AI 비용</label>
                  <input type="number" value={form.ai_cost} onChange={e => setForm({...form, ai_cost: +e.target.value})} className="w-full border rounded px-3 py-2" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">클릭수</label>
                  <input type="number" value={form.clicks} onChange={e => setForm({...form, clicks: +e.target.value})} className="w-full border rounded px-3 py-2" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">노출수</label>
                  <input type="number" value={form.impressions} onChange={e => setForm({...form, impressions: +e.target.value})} className="w-full border rounded px-3 py-2" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">전환수</label>
                  <input type="number" value={form.conversions} onChange={e => setForm({...form, conversions: +e.target.value})} className="w-full border rounded px-3 py-2" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">ROAS (%)</label>
                  <input type="number" step="0.01" value={form.roas} onChange={e => setForm({...form, roas: +e.target.value})} className="w-full border rounded px-3 py-2" />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">저장</button>
            </div>
          </form>
        </div>
      )}

      {/* Add Deposit Modal */}
      {showDepositForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSubmitDeposit} className="bg-white rounded-lg p-6 w-[400px]">
            <h2 className="text-lg font-bold mb-4">입금 기록</h2>
            <div className="space-y-3">
              <select value={depositForm.seller} onChange={e => setDepositForm({...depositForm, seller: e.target.value})} className="w-full border rounded px-3 py-2" required>
                <option value="">셀러 선택</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.seller_name} ({a.seller_id})</option>)}
              </select>
              <input type="date" value={depositForm.deposit_date} onChange={e => setDepositForm({...depositForm, deposit_date: e.target.value})} className="w-full border rounded px-3 py-2" />
              <div>
                <label className="text-xs text-gray-500">입금액</label>
                <input type="number" value={depositForm.deposited_amount} onChange={e => setDepositForm({...depositForm, deposited_amount: +e.target.value})} className="w-full border rounded px-3 py-2" />
              </div>
              <div>
                <label className="text-xs text-gray-500">잔액</label>
                <input type="number" value={depositForm.balance} onChange={e => setDepositForm({...depositForm, balance: +e.target.value})} className="w-full border rounded px-3 py-2" />
              </div>
              <textarea value={depositForm.memo} onChange={e => setDepositForm({...depositForm, memo: e.target.value})} placeholder="메모" className="w-full border rounded px-3 py-2" rows={2} />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowDepositForm(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded-lg">저장</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
