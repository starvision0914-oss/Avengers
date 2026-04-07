import { useEffect, useState } from 'react';
import {
  getCrawlerAccounts, createCrawlerAccount, updateCrawlerAccount, deleteCrawlerAccount,
  getCrawlerLogs, triggerCrawl, getGmarketSnapshots, getElevenCosts,
  getGmarketGrades, getElevenGrades
} from '../../api/crawler';
import { Plus, Play, Trash2, Edit2, RefreshCw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const STATUS_COLORS: Record<string, string> = {
  '정상': 'bg-green-100 text-green-700',
  '차단됨': 'bg-red-100 text-red-700',
};

export default function CrawlerPage() {
  const [tab, setTab] = useState('accounts');
  const [accounts, setAccounts] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [elevenCosts, setElevenCosts] = useState<any[]>([]);
  const [gmGrades, setGmGrades] = useState<any[]>([]);
  const [elGrades, setElGrades] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ platform: 'gmarket', login_id: '', password_enc: '', seller_name: '', display_order: 0 });
  const [crawling, setCrawling] = useState('');
  const [platformFilter, setPlatformFilter] = useState('all');

  const loadAccounts = () => getCrawlerAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || []));
  const loadLogs = () => getCrawlerLogs().then(d => setLogs(Array.isArray(d) ? d : d.results || []));
  const loadSnapshots = () => getGmarketSnapshots().then(d => setSnapshots(Array.isArray(d) ? d : d.results || []));
  const loadElevenCosts = () => getElevenCosts().then(d => setElevenCosts(Array.isArray(d) ? d : d.results || []));
  const loadGrades = () => {
    getGmarketGrades().then(d => setGmGrades(Array.isArray(d) ? d : d.results || []));
    getElevenGrades().then(d => setElGrades(Array.isArray(d) ? d : d.results || []));
  };

  useEffect(() => {
    loadAccounts();
    loadLogs();
    loadSnapshots();
    loadElevenCosts();
    loadGrades();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) {
        await updateCrawlerAccount(editing.id, form);
        toast.success('수정 완료');
      } else {
        await createCrawlerAccount(form);
        toast.success('추가 완료');
      }
      setShowForm(false);
      setEditing(null);
      loadAccounts();
    } catch { toast.error('저장 실패'); }
  };

  const handleEdit = (a: any) => {
    setEditing(a);
    setForm({ platform: a.platform, login_id: a.login_id, password_enc: '', seller_name: a.seller_name, display_order: a.display_order });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('삭제하시겠습니까?')) return;
    await deleteCrawlerAccount(id);
    toast.success('삭제됨');
    loadAccounts();
  };

  const handleCrawl = async (platform: string, type: string) => {
    const key = `${platform}_${type}`;
    setCrawling(key);
    try {
      await triggerCrawl({ platform, type });
      toast.success(`${platform} ${type === 'cost' ? '광고비' : '등급'} 크롤링 시작됨`);
    } catch { toast.error('크롤링 시작 실패'); }
    setTimeout(() => setCrawling(''), 3000);
  };

  const filteredAccounts = platformFilter === 'all' ? accounts : accounts.filter(a => a.platform === platformFilter);
  const gmAccounts = accounts.filter(a => a.platform === 'gmarket');
  const elAccounts = accounts.filter(a => a.platform === '11st');

  const tabs = [
    { key: 'accounts', label: '계정 관리' },
    { key: 'data', label: '수집 데이터' },
    { key: 'grades', label: '등급 현황' },
    { key: 'logs', label: '로그' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">크롤러 관리</h1>
        <div className="flex gap-2">
          <button onClick={() => handleCrawl('gmarket', 'cost')} disabled={!!crawling}
            className="flex items-center gap-1 bg-blue-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            <Play size={14} /> {crawling === 'gmarket_cost' ? '실행중...' : '지마켓 광고비'}
          </button>
          <button onClick={() => handleCrawl('11st', 'cost')} disabled={!!crawling}
            className="flex items-center gap-1 bg-orange-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50">
            <Play size={14} /> {crawling === '11st_cost' ? '실행중...' : '11번가 광고비'}
          </button>
          <button onClick={() => handleCrawl('gmarket', 'grade')} disabled={!!crawling}
            className="flex items-center gap-1 bg-purple-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50">
            <Play size={14} /> {crawling === 'gmarket_grade' ? '실행중...' : '지마켓 등급'}
          </button>
          <button onClick={() => handleCrawl('11st', 'grade')} disabled={!!crawling}
            className="flex items-center gap-1 bg-pink-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-pink-700 disabled:opacity-50">
            <Play size={14} /> {crawling === '11st_grade' ? '실행중...' : '11번가 등급'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b flex">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${tab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {/* === 계정 관리 탭 === */}
          {tab === 'accounts' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex gap-2">
                  {['all', 'gmarket', '11st'].map(p => (
                    <button key={p} onClick={() => setPlatformFilter(p)}
                      className={`px-3 py-1 rounded text-sm ${platformFilter === p ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
                      {p === 'all' ? '전체' : p === 'gmarket' ? '지마켓' : '11번가'}
                      {p === 'all' ? ` (${accounts.length})` : p === 'gmarket' ? ` (${gmAccounts.length})` : ` (${elAccounts.length})`}
                    </button>
                  ))}
                </div>
                <button onClick={() => { setEditing(null); setForm({ platform: 'gmarket', login_id: '', password_enc: '', seller_name: '', display_order: 0 }); setShowForm(true); }}
                  className="flex items-center gap-1 bg-blue-600 text-white px-3 py-2 rounded-lg text-sm">
                  <Plus size={14} /> 계정 추가
                </button>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left">플랫폼</th>
                    <th className="px-3 py-2 text-left">로그인 ID</th>
                    <th className="px-3 py-2 text-left">셀러명</th>
                    <th className="px-3 py-2 text-center">상태</th>
                    <th className="px-3 py-2 text-center">실패</th>
                    <th className="px-3 py-2 text-left">최근 수집</th>
                    <th className="px-3 py-2 text-center">관리</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAccounts.map(a => (
                    <tr key={a.id} className="border-t hover:bg-gray-50">
                      <td className="px-3 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs ${a.platform === 'gmarket' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'}`}>
                          {a.platform === 'gmarket' ? '지마켓' : '11번가'}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-medium">{a.login_id}</td>
                      <td className="px-3 py-2">{a.seller_name}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[a.crawling_status] || 'bg-gray-100'}`}>
                          {a.crawling_status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span className={a.fail_count > 0 ? 'text-red-600 font-medium' : 'text-gray-400'}>{a.fail_count}</span>
                      </td>
                      <td className="px-3 py-2 text-gray-500 text-xs">
                        {a.last_crawled_at ? new Date(a.last_crawled_at).toLocaleString('ko-KR') : '-'}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <button onClick={() => handleEdit(a)} className="text-blue-600 hover:text-blue-800 mr-2"><Edit2 size={14} /></button>
                        <button onClick={() => handleDelete(a.id)} className="text-red-600 hover:text-red-800"><Trash2 size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* === 수집 데이터 탭 === */}
          {tab === 'data' && (
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">지마켓 광고비 스냅샷 (최근)</h3>
                  <button onClick={loadSnapshots} className="text-sm text-blue-600"><RefreshCw size={14} /></button>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">계정</th>
                      <th className="px-3 py-2 text-right">잔액</th>
                      <th className="px-3 py-2 text-right">CPC</th>
                      <th className="px-3 py-2 text-right">AI</th>
                      <th className="px-3 py-2 text-right">합계</th>
                      <th className="px-3 py-2 text-left">수집일시</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(snapshots.length > 0 ? snapshots.slice(0, 50) : []).map((s: any) => (
                      <tr key={s.id} className="border-t">
                        <td className="px-3 py-2">{s.gmarket_id}</td>
                        <td className="px-3 py-2 text-right">{s.total_balance?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{s.gmarket_cpc?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{s.ai_usage?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right font-semibold">{s.total_usage?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-xs text-gray-500">{s.collected_at ? new Date(s.collected_at).toLocaleString('ko-KR') : ''}</td>
                      </tr>
                    ))}
                    {snapshots.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400">수집된 데이터가 없습니다.</td></tr>}
                  </tbody>
                </table>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">11번가 거래내역 (최근)</h3>
                  <button onClick={loadElevenCosts} className="text-sm text-blue-600"><RefreshCw size={14} /></button>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">계정</th>
                      <th className="px-3 py-2 text-left">거래일시</th>
                      <th className="px-3 py-2 text-left">유형</th>
                      <th className="px-3 py-2 text-left">내용</th>
                      <th className="px-3 py-2 text-right">금액</th>
                      <th className="px-3 py-2 text-right">잔액</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(elevenCosts.length > 0 ? elevenCosts.slice(0, 50) : []).map((c: any) => (
                      <tr key={c.id} className="border-t">
                        <td className="px-3 py-2">{c.seller_id}</td>
                        <td className="px-3 py-2 text-xs">{c.transaction_datetime ? new Date(c.transaction_datetime).toLocaleString('ko-KR') : ''}</td>
                        <td className="px-3 py-2">
                          <span className={`px-1.5 py-0.5 rounded text-xs ${c.transaction_type === 'CPC' ? 'bg-blue-100 text-blue-700' : c.transaction_type === 'CHARGE' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                            {c.transaction_type}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-xs">{c.raw_description}</td>
                        <td className="px-3 py-2 text-right">{c.amount?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{c.balance?.toLocaleString()}</td>
                      </tr>
                    ))}
                    {elevenCosts.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400">수집된 데이터가 없습니다.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* === 등급 현황 탭 === */}
          {tab === 'grades' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-3">지마켓 셀러 등급</h3>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">계정</th>
                      <th className="px-3 py-2 text-left">셀러ID</th>
                      <th className="px-3 py-2 text-left">등급</th>
                      <th className="px-3 py-2 text-right">최대수량</th>
                      <th className="px-3 py-2 text-left">승인상태</th>
                      <th className="px-3 py-2 text-left">연락처 유효기간</th>
                      <th className="px-3 py-2 text-left">수집일</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gmGrades.length > 0 ? gmGrades.map((g: any) => (
                      <tr key={g.id} className="border-t">
                        <td className="px-3 py-2">{g.gmarket_id}</td>
                        <td className="px-3 py-2">{g.seller_id}</td>
                        <td className="px-3 py-2 font-medium">{g.seller_grade}</td>
                        <td className="px-3 py-2 text-right">{g.max_item_count?.toLocaleString()}</td>
                        <td className="px-3 py-2">{g.approval_status}</td>
                        <td className="px-3 py-2">{g.contact_expiry}</td>
                        <td className="px-3 py-2 text-xs text-gray-500">{g.collected_at ? new Date(g.collected_at).toLocaleString('ko-KR') : ''}</td>
                      </tr>
                    )) : <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-400">등급 데이터가 없습니다.</td></tr>}
                  </tbody>
                </table>
              </div>

              <div>
                <h3 className="font-semibold mb-3">11번가 셀러 등급</h3>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">계정</th>
                      <th className="px-3 py-2 text-left">셀러명</th>
                      <th className="px-3 py-2 text-center">등급</th>
                      <th className="px-3 py-2 text-right">필요매출</th>
                      <th className="px-3 py-2 text-left">등급메시지</th>
                      <th className="px-3 py-2 text-left">수집일</th>
                    </tr>
                  </thead>
                  <tbody>
                    {elGrades.length > 0 ? elGrades.map((g: any) => (
                      <tr key={g.id} className="border-t">
                        <td className="px-3 py-2">{g.eleven_id}</td>
                        <td className="px-3 py-2">{g.seller_name}</td>
                        <td className="px-3 py-2 text-center font-bold text-lg">{g.grade}</td>
                        <td className="px-3 py-2 text-right">{g.required_sales?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-xs">{g.grade_message}</td>
                        <td className="px-3 py-2 text-xs text-gray-500">{g.collected_at ? new Date(g.collected_at).toLocaleString('ko-KR') : ''}</td>
                      </tr>
                    )) : <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400">등급 데이터가 없습니다.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* === 로그 탭 === */}
          {tab === 'logs' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">크롤링 로그 (최근 200건)</h3>
                <button onClick={loadLogs} className="text-sm text-blue-600 flex items-center gap-1"><RefreshCw size={14} /> 새로고침</button>
              </div>
              <div className="space-y-1 max-h-[600px] overflow-y-auto">
                {logs.map((l: any) => (
                  <div key={l.id} className={`flex items-start gap-2 px-3 py-1.5 text-sm rounded ${l.level === 'error' ? 'bg-red-50' : l.level === 'success' ? 'bg-green-50' : 'bg-gray-50'}`}>
                    {l.level === 'error' ? <XCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" /> :
                     l.level === 'success' ? <CheckCircle size={14} className="text-green-500 mt-0.5 flex-shrink-0" /> :
                     <AlertTriangle size={14} className="text-yellow-500 mt-0.5 flex-shrink-0" />}
                    <span className={`px-1.5 py-0.5 rounded text-xs flex-shrink-0 ${l.platform === 'gmarket' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'}`}>
                      {l.platform}
                    </span>
                    {l.account_id && <span className="text-gray-500 flex-shrink-0">[{l.account_id}]</span>}
                    <span className="flex-1">{l.message}</span>
                    <span className="text-xs text-gray-400 flex-shrink-0">{l.created_at ? new Date(l.created_at).toLocaleString('ko-KR') : ''}</span>
                  </div>
                ))}
                {logs.length === 0 && <div className="text-center py-8 text-gray-400">로그가 없습니다.</div>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add/Edit Account Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg p-6 w-[400px]">
            <h2 className="text-lg font-bold mb-4">{editing ? '계정 수정' : '계정 추가'}</h2>
            <div className="space-y-3">
              <select value={form.platform} onChange={e => setForm({...form, platform: e.target.value})} className="w-full border rounded px-3 py-2">
                <option value="gmarket">지마켓</option>
                <option value="11st">11번가</option>
              </select>
              <input value={form.login_id} onChange={e => setForm({...form, login_id: e.target.value})} placeholder="로그인 ID" className="w-full border rounded px-3 py-2" required />
              <input type="password" value={form.password_enc} onChange={e => setForm({...form, password_enc: e.target.value})} placeholder={editing ? '변경시에만 입력' : '비밀번호'} className="w-full border rounded px-3 py-2" required={!editing} />
              <input value={form.seller_name} onChange={e => setForm({...form, seller_name: e.target.value})} placeholder="셀러명" className="w-full border rounded px-3 py-2" />
              <input type="number" value={form.display_order} onChange={e => setForm({...form, display_order: +e.target.value})} placeholder="표시순서" className="w-full border rounded px-3 py-2" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => { setShowForm(false); setEditing(null); }} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">저장</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
