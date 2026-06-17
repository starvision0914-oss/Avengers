import { useEffect, useState } from 'react';
import { Plus, Trash2, Upload, Download, Search, Edit2, Save, X, RefreshCw, Star } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../api/client';
import { useTheme } from '../../hooks/useTheme';
import BlockedAccountsAlert from '../../components/BlockedAccountsAlert';

interface Account {
  id: number; platform: string; login_id: string; password_enc?: string;
  seller_name: string; is_active: boolean; fail_count: number;
  crawling_status: string; cost_type: string; last_crawled_at: string | null;
  display_order: number; is_focused: boolean; api_key: string;
}

const PLATFORMS = [
  { value: 'gmarket', label: '지마켓', color: '#6cc24a' },
  { value: '11st', label: '11번가', color: '#ff5a2e' },
];

export default function CrawlerAccountsPage() {
  const { dark } = useTheme();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ platform: '11st', login_id: '', password_enc: '', seller_name: '', cost_type: 'sellerpoint' });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const bg = dark ? 'bg-[#0f1117]' : 'bg-[#f5f6fa]';
  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e5e7eb]';
  const text1 = dark ? 'text-white' : 'text-gray-900';
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';
  const text3 = dark ? 'text-gray-500' : 'text-gray-400';
  const input = dark ? 'bg-[#0f1117] border-[#2a2b35] text-white' : 'bg-white border-gray-300 text-gray-900';

  const load = () => {
    setLoading(true);
    api.get('/cpc/crawler/accounts/', { params: { page_size: 200 } })
      .then(r => {
        const data = r.data?.results || r.data || [];
        setAccounts(Array.isArray(data) ? data : []);
      })
      .catch(() => toast.error('계정 로드 실패'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = accounts.filter(a => {
    if (filter === 'focused' && !a.is_focused) return false;
    else if (filter !== 'all' && filter !== 'focused' && a.platform !== filter) return false;
    if (search && !a.login_id.toLowerCase().includes(search.toLowerCase()) && !a.seller_name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const gmCount = accounts.filter(a => a.platform === 'gmarket').length;
  const stCount = accounts.filter(a => a.platform === '11st').length;

  const handleAdd = async () => {
    if (!form.login_id.trim()) { toast.error('아이디 필수'); return; }
    try {
      await api.post('/cpc/crawler/accounts/', form);
      toast.success('계정 추가 완료');
      setShowAdd(false);
      setForm({ platform: '11st', login_id: '', password_enc: '', seller_name: '', cost_type: 'sellerpoint' });
      load();
    } catch (e: any) {
      toast.error('추가 실패: ' + (e?.response?.data?.login_id?.[0] || e.message));
    }
  };

  const handleDelete = async (id: number, loginId: string) => {
    if (!confirm(`${loginId} 삭제할까요?`)) return;
    try {
      await api.delete(`/cpc/crawler/accounts/${id}/`);
      toast.success('삭제 완료');
      load();
    } catch { toast.error('삭제 실패'); }
  };

  const handleUpdate = async (a: Account) => {
    try {
      await api.patch(`/cpc/crawler/accounts/${a.id}/`, {
        seller_name: a.seller_name,
        cost_type: a.cost_type,
        is_active: a.is_active,
        api_key: a.api_key || '',
      });
      toast.success('수정 완료');
      setEditId(null);
      load();
    } catch { toast.error('수정 실패'); }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };
  const toggleSelectAll = () => {
    setSelectedIds(prev => {
      const visibleIds = filtered.map(a => a.id);
      const allSelected = visibleIds.every(id => prev.has(id));
      const next = new Set(prev);
      if (allSelected) visibleIds.forEach(id => next.delete(id));
      else visibleIds.forEach(id => next.add(id));
      return next;
    });
  };
  const handleBulkFocus = async (focused: boolean) => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) { toast.error('선택된 계정 없음'); return; }
    if (!confirm(`${ids.length}개 계정을 ${focused ? '집중관리 지정' : '집중관리 해제'}할까요?`)) return;
    try {
      const r = await api.post('/cpc/crawler/accounts/bulk-focus/', { ids, focused });
      toast.success(`${r.data.updated}개 ${focused ? '집중관리 지정' : '해제'} 완료`);
      setSelectedIds(new Set());
      load();
    } catch { toast.error('일괄 처리 실패'); }
  };

  const handleToggleFocus = async (a: Account) => {
    const next = !a.is_focused;
    setAccounts(prev => prev.map(x => x.id === a.id ? { ...x, is_focused: next } : x));
    try {
      await api.patch(`/cpc/crawler/accounts/${a.id}/`, { is_focused: next });
      toast.success(next ? `${a.login_id} 집중관리 ON` : `${a.login_id} 집중관리 OFF`, { duration: 1500 });
    } catch {
      setAccounts(prev => prev.map(x => x.id === a.id ? { ...x, is_focused: !next } : x));
      toast.error('집중관리 토글 실패');
    }
  };

  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await api.post('/cpc/crawler/accounts/excel-upload/', fd);
      toast.success(`엑셀 업로드: ${res.data.created}개 추가, ${res.data.updated}개 수정`);
      if (res.data.errors?.length) toast.error(`오류 ${res.data.errors.length}건`);
      load();
    } catch (err: any) {
      toast.error('업로드 실패: ' + (err?.response?.data?.error || err.message));
    }
    e.target.value = '';
  };

  return (
    <div className={`min-h-screen ${bg} transition-colors`}>
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-4 space-y-4">

        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className={`text-2xl font-bold ${text1}`}>크롤러 계정 관리</h1>
            <p className={`text-xs ${text3} mt-0.5`}>지마켓 {gmCount}개 · 11번가 {stCount}개 · 총 {accounts.length}개</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className={`p-2 rounded-lg ${dark ? 'hover:bg-[#2a2b35]' : 'hover:bg-gray-100'}`}>
              <RefreshCw size={16} className={loading ? 'animate-spin text-blue-500' : text2} />
            </button>
            <a href="/api/cpc/crawler/accounts/excel-sample/" download className={`flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-semibold ${dark ? 'bg-[#2a2b35] text-gray-300 hover:bg-[#3a3b45]' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
              <Download size={14} /> 샘플 엑셀
            </a>
            <label className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-semibold bg-green-600 text-white hover:bg-green-700 cursor-pointer">
              <Upload size={14} /> 엑셀 업로드
              <input type="file" accept=".xlsx,.xls" onChange={handleExcelUpload} className="hidden" />
            </label>
            <button onClick={() => setShowAdd(true)} className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700">
              <Plus size={14} /> 계정 추가
            </button>
          </div>
        </div>

        {/* 차단 알림 */}
        <BlockedAccountsAlert />

        {/* Filters */}
        <div className="flex items-center gap-2">
          {[{ v: 'all', l: '전체' }, ...PLATFORMS.map(p => ({ v: p.value, l: p.label })), { v: 'focused', l: '★ 집중관리' }].map(f => (
            <button key={f.v} onClick={() => setFilter(f.v)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${filter === f.v
                ? 'bg-blue-600 text-white'
                : dark ? 'bg-[#1a1b23] text-gray-400 hover:bg-[#2a2b35]' : 'bg-white text-gray-600 hover:bg-gray-100'}`}>
              {f.l}
            </button>
          ))}
          {selectedIds.size > 0 && (
            <>
              <div className={`mx-1 w-px h-6 ${dark ? 'bg-[#2a2b35]' : 'bg-gray-200'}`} />
              <span className={`text-xs ${text2}`}>선택 {selectedIds.size}개</span>
              <button
                onClick={() => handleBulkFocus(true)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-yellow-500 hover:bg-yellow-600 text-white inline-flex items-center gap-1"
              >
                <Star size={12} fill="currentColor" /> 집중관리 ON
              </button>
              <button
                onClick={() => handleBulkFocus(false)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${dark ? 'bg-[#2a2b35] hover:bg-[#3a3b45] text-gray-300' : 'bg-gray-200 hover:bg-gray-300 text-gray-700'} inline-flex items-center gap-1`}
              >
                <Star size={12} /> 해제
              </button>
              <button
                onClick={() => setSelectedIds(new Set())}
                className={`px-2 py-1.5 rounded-lg text-xs ${text3} hover:underline`}
              >
                선택 취소
              </button>
            </>
          )}
          <div className="relative ml-auto">
            <Search size={14} className={`absolute left-2.5 top-2.5 ${text3}`} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="검색..."
              className={`pl-8 pr-3 py-2 rounded-lg text-xs border ${input} w-48`} />
          </div>
        </div>

        {/* Table */}
        <div className={`rounded-xl border ${card} overflow-hidden`}>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className={dark ? 'bg-[#0f1117]' : 'bg-gray-50'}>
                <tr className={text2}>
                  <th className="px-3 py-2 text-center font-medium w-8">
                    <input
                      type="checkbox"
                      checked={filtered.length > 0 && filtered.every(a => selectedIds.has(a.id))}
                      ref={el => { if (el) el.indeterminate = selectedIds.size > 0 && !filtered.every(a => selectedIds.has(a.id)); }}
                      onChange={toggleSelectAll}
                      className="cursor-pointer accent-blue-600"
                    />
                  </th>
                  <th className="px-3 py-2 text-center font-medium w-8" title="집중관리">★</th>
                  <th className="px-3 py-2 text-left font-medium w-8">#</th>
                  <th className="px-3 py-2 text-left font-medium">플랫폼</th>
                  <th className="px-3 py-2 text-left font-medium">아이디</th>
                  <th className="px-3 py-2 text-left font-medium">셀러명</th>
                  <th className="px-3 py-2 text-center font-medium">타입</th>
                  <th className="px-3 py-2 text-center font-medium">활성</th>
                  <th className="px-3 py-2 text-center font-medium">상태</th>
                  <th className="px-3 py-2 text-center font-medium">fail</th>
                  <th className="px-3 py-2 text-right font-medium">수집</th>
                  <th className="px-3 py-2 text-left font-medium w-32">11번가 API키</th>
                  <th className="px-3 py-2 text-center font-medium w-20">동작</th>
                </tr>
              </thead>
              <tbody className={`divide-y ${dark ? 'divide-[#2a2b35]' : 'divide-gray-100'}`}>
                {filtered.map((a, i) => {
                  const plat = PLATFORMS.find(p => p.value === a.platform);
                  const isEdit = editId === a.id;
                  return (
                    <tr key={a.id} className={`${dark ? 'hover:bg-[#1f2029]' : 'hover:bg-gray-50'} ${a.is_focused ? (dark ? 'bg-yellow-500/5' : 'bg-yellow-50/60') : ''} ${selectedIds.has(a.id) ? (dark ? 'bg-blue-900/20' : 'bg-blue-50') : ''}`}>
                      <td className="px-3 py-1.5 text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(a.id)}
                          onChange={() => toggleSelect(a.id)}
                          className="cursor-pointer accent-blue-600"
                        />
                      </td>
                      <td className="px-3 py-1.5 text-center">
                        <button
                          onClick={() => handleToggleFocus(a)}
                          className={`p-0.5 rounded hover:scale-125 transition-transform ${a.is_focused ? 'text-yellow-400' : 'text-gray-400 hover:text-yellow-300'}`}
                          title={a.is_focused ? '집중관리 해제' : '집중관리 지정'}
                        >
                          <Star size={15} fill={a.is_focused ? 'currentColor' : 'none'} strokeWidth={2} />
                        </button>
                      </td>
                      <td className={`px-3 py-1.5 ${text3}`}>{i + 1}</td>
                      <td className="px-3 py-1.5">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold text-white" style={{ backgroundColor: plat?.color || '#888' }}>
                          {plat?.label || a.platform}
                        </span>
                      </td>
                      <td className={`px-3 py-1.5 font-mono font-medium ${text1}`}>{a.login_id}</td>
                      <td className={`px-3 py-1.5 ${text2}`}>
                        {isEdit ? (
                          <input value={a.seller_name} onChange={e => setAccounts(prev => prev.map(x => x.id === a.id ? { ...x, seller_name: e.target.value } : x))}
                            className={`w-full px-2 py-0.5 rounded border ${input} text-[11px]`} />
                        ) : a.seller_name || '-'}
                      </td>
                      <td className="px-3 py-1.5 text-center">
                        {isEdit ? (
                          <select value={a.cost_type} onChange={e => setAccounts(prev => prev.map(x => x.id === a.id ? { ...x, cost_type: e.target.value } : x))}
                            className={`px-1 py-0.5 rounded border ${input} text-[10px]`}>
                            <option value="sellerpoint">포인트</option>
                            <option value="sellercash">캐시</option>
                          </select>
                        ) : (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${a.cost_type === 'sellercash' ? 'bg-amber-500/20 text-amber-500' : (dark ? 'bg-[#2a2b35] text-gray-400' : 'bg-gray-100 text-gray-500')}`}>
                            {a.cost_type === 'sellercash' ? '캐시' : '포인트'}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-1.5 text-center">
                        <span className={`w-2 h-2 rounded-full inline-block ${a.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                      </td>
                      <td className="px-3 py-1.5 text-center">
                        <span className={`text-[10px] ${a.crawling_status === '정상' ? 'text-green-500' : a.crawling_status === '차단됨' ? 'text-red-500' : text3}`}>
                          {a.crawling_status}
                        </span>
                      </td>
                      <td className={`px-3 py-1.5 text-center ${a.fail_count >= 30 ? 'text-red-500 font-bold' : a.fail_count >= 10 ? 'text-amber-500' : text3}`}>
                        {a.fail_count}
                      </td>
                      <td className={`px-3 py-1.5 text-right text-[10px] ${text3}`}>
                        {a.last_crawled_at ? new Date(a.last_crawled_at).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                      </td>
                      <td className="px-3 py-1.5">
                        {a.platform !== '11st' ? (
                          <span className={`text-[10px] ${text3}`}>—</span>
                        ) : isEdit ? (
                          <input value={a.api_key || ''} onChange={e => setAccounts(prev => prev.map(x => x.id === a.id ? { ...x, api_key: e.target.value } : x))}
                            placeholder="11st OpenAPI key"
                            className={`w-full px-2 py-0.5 rounded border ${input} text-[10px] font-mono`} />
                        ) : a.api_key ? (
                          <span className={`text-[10px] font-mono ${text2}`}>****{a.api_key.slice(-4)}</span>
                        ) : (
                          <span className="text-[10px] font-semibold text-red-500">미설정</span>
                        )}
                      </td>
                      <td className="px-3 py-1.5 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {isEdit ? (
                            <>
                              <button onClick={() => handleUpdate(a)} className="text-green-500 hover:text-green-400"><Save size={14} /></button>
                              <button onClick={() => { setEditId(null); load(); }} className="text-gray-400 hover:text-gray-300"><X size={14} /></button>
                            </>
                          ) : (
                            <>
                              <button onClick={() => setEditId(a.id)} className="text-blue-500 hover:text-blue-400"><Edit2 size={13} /></button>
                              <button onClick={() => handleDelete(a.id, a.login_id)} className="text-red-500 hover:text-red-400"><Trash2 size={13} /></button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 && (
            <div className={`text-center py-8 ${text3}`}>
              {search ? '검색 결과 없음' : '등록된 계정이 없습니다'}
            </div>
          )}
        </div>
      </div>

      {/* 추가 모달 */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]" onClick={() => setShowAdd(false)}>
          <div className={`${card} rounded-xl shadow-2xl w-[420px] border`} onClick={e => e.stopPropagation()}>
            <div className="px-5 py-3 border-b" style={{ borderColor: dark ? '#2a2b35' : '#e5e7eb' }}>
              <h2 className={`font-bold ${text1}`}>계정 추가</h2>
            </div>
            <div className="p-5 space-y-3">
              <div>
                <label className={`text-xs ${text2} block mb-1`}>플랫폼</label>
                <select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })}
                  className={`w-full border rounded-lg px-3 py-2 text-sm ${input}`}>
                  <option value="gmarket">지마켓</option>
                  <option value="11st">11번가</option>
                </select>
              </div>
              <div>
                <label className={`text-xs ${text2} block mb-1`}>아이디</label>
                <input value={form.login_id} onChange={e => setForm({ ...form, login_id: e.target.value })}
                  className={`w-full border rounded-lg px-3 py-2 text-sm ${input}`} placeholder="셀러 로그인 ID" />
              </div>
              <div>
                <label className={`text-xs ${text2} block mb-1`}>비밀번호</label>
                <input value={form.password_enc} onChange={e => setForm({ ...form, password_enc: e.target.value })}
                  type="password" className={`w-full border rounded-lg px-3 py-2 text-sm ${input}`} placeholder="비밀번호" />
              </div>
              <div>
                <label className={`text-xs ${text2} block mb-1`}>셀러명 (선택)</label>
                <input value={form.seller_name} onChange={e => setForm({ ...form, seller_name: e.target.value })}
                  className={`w-full border rounded-lg px-3 py-2 text-sm ${input}`} placeholder="셀러 이름" />
              </div>
              <div>
                <label className={`text-xs ${text2} block mb-1`}>비용 타입</label>
                <select value={form.cost_type} onChange={e => setForm({ ...form, cost_type: e.target.value })}
                  className={`w-full border rounded-lg px-3 py-2 text-sm ${input}`}>
                  <option value="sellerpoint">셀러포인트</option>
                  <option value="sellercash">셀러캐시</option>
                </select>
              </div>
            </div>
            <div className="px-5 py-3 border-t flex justify-end gap-2" style={{ borderColor: dark ? '#2a2b35' : '#e5e7eb' }}>
              <button onClick={() => setShowAdd(false)} className={`px-4 py-2 rounded-lg text-sm ${dark ? 'bg-[#2a2b35] text-gray-300' : 'bg-gray-200 text-gray-700'}`}>취소</button>
              <button onClick={handleAdd} className="px-4 py-2 rounded-lg text-sm bg-blue-600 text-white hover:bg-blue-700">추가</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
