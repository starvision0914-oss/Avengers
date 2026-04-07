import { useEffect, useState } from 'react';
import { getGmarketSummary, getElevenSummary, getGmarketGrades, getElevenGrades, getCpcStatus, getGmarketAi, getSt11Campaigns } from '../../api/crawler';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, PieChart, Pie, Cell } from 'recharts';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import dayjs from 'dayjs';

const COLORS = ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981', '#EF4444', '#6366F1', '#EC4899'];

export default function AnalysisPage() {
  const [platform, setPlatform] = useState<'gmarket' | '11st'>('gmarket');
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [gmData, setGmData] = useState<any>({ totals: {}, sellers: [] });
  const [elData, setElData] = useState<any>({ totals: {}, sellers: [] });
  const [gmGrades, setGmGrades] = useState<any[]>([]);
  const [elGrades, setElGrades] = useState<any[]>([]);
  const [cpcStatus, setCpcStatus] = useState<any[]>([]);
  const [gmAi, setGmAi] = useState<any[]>([]);
  const [st11Campaigns, setSt11Campaigns] = useState<any[]>([]);

  const load = () => {
    getGmarketSummary({ date }).then(setGmData).catch(() => {});
    getElevenSummary({ date }).then(setElData).catch(() => {});
    getGmarketGrades().then(d => setGmGrades(Array.isArray(d) ? d : d.results || []));
    getElevenGrades().then(d => setElGrades(Array.isArray(d) ? d : d.results || []));
    getCpcStatus().then(d => setCpcStatus(Array.isArray(d) ? d : d.results || []));
    getGmarketAi().then(d => setGmAi(Array.isArray(d) ? d : d.results || []));
    getSt11Campaigns().then(d => setSt11Campaigns(Array.isArray(d) ? d : d.results || []));
  };
  useEffect(() => { load(); }, [date]);

  const fmt = (v: number) => (v || 0).toLocaleString();
  const moveDate = (dir: number) => setDate(prev => dayjs(prev).add(dir, 'day').format('YYYY-MM-DD'));

  const sellers = platform === 'gmarket' ? (gmData.sellers || []) : (elData.sellers || []);
  const grades = platform === 'gmarket' ? gmGrades : elGrades;

  // 광고비 파이차트
  const pieData = platform === 'gmarket' ? [
    { name: 'CPC', value: gmData.totals?.cpc_spend || 0 },
    { name: 'AI', value: gmData.totals?.ai_spend || 0 },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{platform === 'gmarket' ? 'G분석' : '11분석'}</h1>
        <div className="flex items-center gap-3">
          <div className="flex border rounded overflow-hidden">
            <button onClick={() => setPlatform('gmarket')} className={`px-4 py-1.5 text-sm ${platform === 'gmarket' ? 'bg-blue-600 text-white' : 'bg-white'}`}>지마켓</button>
            <button onClick={() => setPlatform('11st')} className={`px-4 py-1.5 text-sm border-l ${platform === '11st' ? 'bg-orange-600 text-white' : 'bg-white'}`}>11번가</button>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => moveDate(-1)} className="p-1 hover:bg-gray-100 rounded"><ChevronLeft size={18} /></button>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} className="text-sm border rounded px-2 py-1" />
            <button onClick={() => moveDate(1)} className="p-1 hover:bg-gray-100 rounded"><ChevronRight size={18} /></button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* 광고비 분포 */}
        {pieData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-5">
            <h3 className="text-sm font-semibold mb-3">광고비 분포</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie>
                <Tooltip formatter={(v: number) => `${v.toLocaleString()}원`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* 매출 영역 (빈칸) */}
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-sm font-semibold mb-3">매출 현황</h3>
          <div className="flex items-center justify-center h-[200px] text-gray-400">매출 데이터 연동 예정</div>
        </div>
      </div>

      {/* 광고 상태 */}
      {platform === 'gmarket' && cpcStatus.length > 0 && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-sm font-semibold mb-3">광고 ON/OFF 현황</h3>
          <div className="grid grid-cols-4 gap-3">
            {cpcStatus.map((s: any) => (
              <div key={s.gmarket_id} className="border rounded p-3">
                <p className="font-medium text-sm">{s.gmarket_id}</p>
                <div className="flex gap-3 mt-1 text-xs">
                  <span>일반: <span className="text-green-600">{s.cpc1_on}ON</span>/<span className="text-red-600">{s.cpc1_off}OFF</span></span>
                  <span>간편: <span className="text-green-600">{s.cpc2_on}ON</span>/<span className="text-red-600">{s.cpc2_off}OFF</span></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI 상태 */}
      {platform === 'gmarket' && gmAi.length > 0 && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-sm font-semibold mb-3">AI 광고 상태</h3>
          <div className="grid grid-cols-4 gap-3">
            {gmAi.map((a: any) => (
              <div key={a.id} className="border rounded p-3">
                <p className="font-medium text-sm">{a.seller_id}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${a.actual_status === 'ON' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{a.actual_status}</span>
                  <span className="text-xs text-gray-500">{a.actual_reason}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 등급 현황 */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-sm font-semibold mb-3">셀러 등급</h3>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">계정</th>
              {platform === 'gmarket' ? (
                <>
                  <th className="px-3 py-2 text-left">등급</th>
                  <th className="px-3 py-2 text-right">최대수량</th>
                  <th className="px-3 py-2 text-left">승인</th>
                </>
              ) : (
                <>
                  <th className="px-3 py-2 text-center">등급</th>
                  <th className="px-3 py-2 text-right">필요매출</th>
                  <th className="px-3 py-2 text-left">메시지</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {grades.length > 0 ? grades.map((g: any) => (
              <tr key={g.id} className="border-t">
                <td className="px-3 py-2">{platform === 'gmarket' ? g.gmarket_id : g.eleven_id}</td>
                {platform === 'gmarket' ? (
                  <>
                    <td className="px-3 py-2 font-medium">{g.seller_grade}</td>
                    <td className="px-3 py-2 text-right">{g.max_item_count?.toLocaleString()}</td>
                    <td className="px-3 py-2">{g.approval_status}</td>
                  </>
                ) : (
                  <>
                    <td className="px-3 py-2 text-center font-bold text-lg">{g.grade}</td>
                    <td className="px-3 py-2 text-right">{g.required_sales?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-xs">{g.grade_message}</td>
                  </>
                )}
              </tr>
            )) : <tr><td colSpan={4} className="px-3 py-8 text-center text-gray-400">등급 데이터 없음</td></tr>}
          </tbody>
        </table>
      </div>

      {/* 셀러별 광고비 차트 */}
      {sellers.length > 0 && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-sm font-semibold mb-3">셀러별 광고비</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sellers.map((s: any) => ({
              name: s.seller_id,
              CPC: s.cpc_spend || 0,
              ...(platform === 'gmarket' ? { AI: s.ai_spend || 0 } : { 충전: s.charge || 0 }),
            }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={v => `${(v/10000).toFixed(0)}만`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `${v.toLocaleString()}원`} />
              <Legend />
              <Bar dataKey="CPC" fill={platform === 'gmarket' ? '#1a73e8' : '#e67700'} />
              {platform === 'gmarket' ? <Bar dataKey="AI" fill="#7c3aed" /> : <Bar dataKey="충전" fill="#00a651" />}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
