import { useEffect, useState, useCallback } from 'react';
import { Leaf, RefreshCw, Tag, Plus, Trash2, Search, AlertCircle, Package, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { speedgoApi, type SpeedgoItem, type SpeedgoStats } from '../../api/speedgo';

const STATUS_COLORS: Record<string, string> = {
  '새로담김': 'bg-blue-100 text-blue-800',
  '카테고리매칭': 'bg-purple-100 text-purple-800',
  '등록준비': 'bg-amber-100 text-amber-800',
  '등록완료': 'bg-green-100 text-green-800',
  '운영중': 'bg-emerald-100 text-emerald-800',
  '보류': 'bg-gray-100 text-gray-700',
  '삭제': 'bg-red-100 text-red-800',
};

export default function SpeedGoPage() {
  const [stats, setStats] = useState<SpeedgoStats>({
    total: 0, matched_categories: 0, unmatched_categories: 0, by_status: {},
  });
  const [items, setItems] = useState<SpeedgoItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [onlyUnmatched, setOnlyUnmatched] = useState(false);

  const [matching, setMatching] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [addName, setAddName] = useState('');
  const [addPrice, setAddPrice] = useState('');
  const [collectOpen, setCollectOpen] = useState(false);
  const [collectId, setCollectId] = useState('');
  const [collectPw, setCollectPw] = useState('');
  const [log, setLog] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    try {
      const s = await speedgoApi.stats();
      setStats(s);
      const l = await speedgoApi.list({ page, per_page: 50, search: search || undefined, only_unmatched: onlyUnmatched });
      setItems(l.items);
      setTotal(l.total);
    } catch (e: any) {
      toast.error(`로드 실패: ${e.message || e}`);
    }
  }, [page, search, onlyUnmatched]);
  useEffect(() => { refresh(); }, [refresh]);

  const onMatchCategories = async () => {
    setMatching(true);
    setLog(prev => [...prev, '== 네이버 카테고리 매칭 시작 ==',
      `대상: ${onlyUnmatched ? '미매칭만' : '전체'}, ${stats.unmatched_categories}개 미매칭`,
    ].slice(-300));
    try {
      const r = await speedgoApi.matchCategories(true);
      setLog(prev => [...prev, ...r.log, `완료: ${r.matched}/${r.total} 성공`].slice(-300));
      toast.success(`매칭 ${r.matched}/${r.total} 성공`);
      await refresh();
    } catch (e: any) {
      toast.error(`매칭 실패: ${e.message || e}`);
      setLog(prev => [...prev, `오류: ${e.message || e}`].slice(-300));
    } finally {
      setMatching(false);
    }
  };

  const onAddManual = async () => {
    if (!addName.trim()) { toast.error('상품명 필수'); return; }
    try {
      const r = await speedgoApi.addManual(addName.trim(), addPrice ? Number(addPrice) : 0);
      toast.success(r.created ? `상품 추가: #${r.id}` : `상품 갱신: #${r.id}`);
      setAddOpen(false); setAddName(''); setAddPrice('');
      await refresh();
    } catch (e: any) {
      toast.error(`추가 실패: ${e.message || e}`);
    }
  };

  const onCollectMybox = async () => {
    if (!collectId.trim() || !collectPw.trim()) {
      toast.error('도매매 ID/비밀번호 필수'); return;
    }
    setCollecting(true);
    setLog(prev => [...prev, '== 도매매 마이박스 수집 시작 ==', `계정: ${collectId}`].slice(-300));
    try {
      const r: any = await speedgoApi.collectMybox(collectId.trim(), collectPw);
      setLog(prev => [...prev, ...(r.log || []), `완료: 신규 ${r.saved}건`].slice(-300));
      if (r.error) toast.error(r.error);
      else toast.success(`수집 완료 — 신규 ${r.saved}건`);
      setCollectOpen(false);
      await refresh();
    } catch (e: any) {
      toast.error(`수집 실패: ${e.message || e}`);
    } finally {
      setCollecting(false);
    }
  };

  const [running, setRunning] = useState(false);
  const [runLogs, setRunLogs] = useState<string[]>([]);
  const [sessionConnected, setSessionConnected] = useState(false);

  useEffect(() => {
    speedgoApi.runStatus().then(s => setSessionConnected(s.connected)).catch(() => {});
  }, []);

  const onRunAutomation = async (steps?: string[]) => {
    setRunning(true);
    setRunLogs(['스피드고 자동화 시작...']);
    try {
      await speedgoApi.run(steps);
      toast.success('스피드고 자동화 실행 중');
      const poll = setInterval(async () => {
        try {
          const s = await speedgoApi.runStatus();
          setRunLogs(s.logs.map(l => `[${new Date(l.created_at).toLocaleTimeString('ko-KR')}] ${l.message}`).reverse());
          if (s.logs.some(l => l.message.includes('전체 완료'))) {
            clearInterval(poll);
            setRunning(false);
            toast.success('스피드고 자동화 완료');
          }
        } catch { }
      }, 5000);
      setTimeout(() => { clearInterval(poll); setRunning(false); }, 600000);
    } catch (e: any) {
      toast.error(`실행 실패: ${e.message}`);
      setRunning(false);
    }
  };

  const onDelete = async (id: number) => {
    if (!confirm(`#${id} 삭제할까요?`)) return;
    try {
      await speedgoApi.delete(id);
      toast.success(`#${id} 삭제됨`);
      await refresh();
    } catch (e: any) {
      toast.error(`삭제 실패: ${e.message || e}`);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* 스피드고 자동화 패널 */}
      <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 8, padding: 20, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <span style={{ fontSize: 20, fontWeight: 700 }}>📦 스피드고 자동화</span>
          <span style={{ fontSize: 13, padding: '3px 10px', borderRadius: 10, background: sessionConnected ? '#e6ffe6' : '#fee', color: sessionConnected ? '#00a651' : '#dc2626', fontWeight: 600 }}>
            {sessionConnected ? '● 세션 연결됨' : '○ 세션 없음'}
          </span>
          <button
            onClick={() => onRunAutomation()}
            disabled={running}
            style={{ padding: '8px 20px', fontSize: 15, fontWeight: 700, borderRadius: 6, border: 'none', cursor: running ? 'not-allowed' : 'pointer', background: running ? '#ccc' : '#e67700', color: '#fff' }}>
            {running ? '실행 중...' : '전체 실행 (7단계)'}
          </button>
          {sessionConnected && (
            <button onClick={async () => { await speedgoApi.closeSession(); setSessionConnected(false); toast.success('세션 종료'); }}
              style={{ padding: '6px 12px', fontSize: 13, borderRadius: 4, border: '1px solid #dc2626', color: '#dc2626', background: '#fff', cursor: 'pointer' }}>
              세션 종료
            </button>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {['주문수집', '배송상태갱신', '품절상품업데이트', '재입고상품업데이트', '가격변동상품업데이트', '마켓문의수집', '지재권및리콜신고상품삭제'].map(step => (
            <button key={step} onClick={() => onRunAutomation([step])} disabled={running}
              style={{ padding: '5px 12px', fontSize: 13, borderRadius: 4, border: '1px solid #ddd', background: running ? '#f5f5f5' : '#fff', cursor: running ? 'not-allowed' : 'pointer' }}>
              {step}
            </button>
          ))}
        </div>
        {runLogs.length > 0 && (
          <div style={{ background: '#1e1e1e', color: '#ddd', padding: 12, borderRadius: 6, maxHeight: 200, overflow: 'auto', fontSize: 13, fontFamily: 'monospace' }}>
            {runLogs.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 mb-6">
        <Leaf className="w-8 h-8 text-emerald-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">스피드고 — 도매매 파이프라인</h1>
          <p className="text-sm text-gray-500">도매매 마이박스 → 네이버 카테고리 자동 매칭 → 마켓별 등록 (MVP)</p>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">전체 상품</span>
            <Package className="w-5 h-5 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold">{stats.total.toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">카테고리 매칭됨</span>
            <Tag className="w-5 h-5 text-purple-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-purple-700">{stats.matched_categories.toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">미매칭</span>
            <AlertCircle className="w-5 h-5 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-700">{stats.unmatched_categories.toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">상태별</span>
          </div>
          <div className="mt-1 text-xs text-gray-600 leading-5">
            {Object.entries(stats.by_status).filter(([_, v]) => v > 0).map(([k, v]) => (
              <span key={k} className="inline-block mr-2">{k}: <strong>{v}</strong></span>
            ))}
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button onClick={() => setCollectOpen(true)} disabled={collecting}
          className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white font-semibold rounded-lg shadow hover:bg-emerald-700 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${collecting ? 'animate-spin' : ''}`} />
          1. 도매매 마이박스 수집
        </button>
        <button onClick={onMatchCategories} disabled={matching || stats.total === 0}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white font-semibold rounded-lg shadow hover:bg-purple-700 disabled:opacity-50">
          <Tag className={`w-4 h-4 ${matching ? 'animate-spin' : ''}`} />
          {matching ? '매칭 중...' : `2. 네이버 카테고리 매칭 (미매칭 ${stats.unmatched_categories})`}
        </button>
        <button onClick={() => setAddOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white font-semibold rounded-lg shadow hover:bg-blue-700">
          <Plus className="w-4 h-4" /> 수동 상품 추가
        </button>
      </div>

      {/* 검색 / 필터 */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-400" />
          <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput); setPage(1); } }}
            placeholder="상품명 검색..."
            className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={onlyUnmatched} onChange={e => { setOnlyUnmatched(e.target.checked); setPage(1); }} />
          미매칭만
        </label>
        <span className="text-sm text-gray-500">총 {total.toLocaleString()}건</span>
      </div>

      {/* 상품 리스트 */}
      <div className="bg-white rounded-lg shadow border border-gray-200 mb-6 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">ID</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">이미지</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">상품명 (원본)</th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-gray-600">도매가</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">네이버 카테고리</th>
              <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">상태</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">
                상품이 없습니다 — "1. 도매매 마이박스 수집" 또는 "수동 상품 추가"를 시작하세요.
              </td></tr>
            ) : items.map(it => (
              <tr key={it.id} className="hover:bg-emerald-50">
                <td className="px-3 py-2 text-xs font-mono text-gray-700">#{it.id}</td>
                <td className="px-3 py-2">
                  {it.main_image_url ? (
                    <img src={it.main_image_url} alt="" className="w-12 h-12 object-cover rounded" />
                  ) : (
                    <div className="w-12 h-12 bg-gray-100 rounded flex items-center justify-center text-gray-300 text-xs">no img</div>
                  )}
                </td>
                <td className="px-3 py-2 text-sm text-gray-900">
                  <div className="font-medium">{it.original_name}</div>
                  <div className="text-xs text-gray-400">도매매 #{it.domemea_no}</div>
                </td>
                <td className="px-3 py-2 text-right font-mono text-sm">
                  {it.wholesale_price > 0 ? `${it.wholesale_price.toLocaleString()}원` : '-'}
                </td>
                <td className="px-3 py-2 text-xs">
                  {it.naver_category_path ? (
                    <span className="inline-block px-2 py-1 bg-purple-50 text-purple-700 rounded">
                      {it.naver_category_path}
                    </span>
                  ) : (
                    <span className="text-gray-300">미매칭</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={`inline-block px-2 py-0.5 text-xs font-semibold rounded ${STATUS_COLORS[it.status] || 'bg-gray-100 text-gray-700'}`}>
                    {it.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => onDelete(it.id)} className="text-gray-400 hover:text-red-600 p-1" title="삭제">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 실행 로그 */}
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">실행 로그</h3>
          <button onClick={() => setLog([])} className="text-xs text-gray-400 hover:text-gray-700">지우기</button>
        </div>
        <div className="p-3 bg-gray-50 max-h-72 overflow-y-auto font-mono text-xs text-gray-700">
          {log.length === 0
            ? <div className="text-gray-400 text-center py-8">로그가 비어있습니다</div>
            : log.map((l, i) => <div key={i} className="py-0.5">{l}</div>)
          }
        </div>
      </div>

      {/* 수동 추가 모달 */}
      {addOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">수동 상품 추가</h3>
              <button onClick={() => setAddOpen(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">상품명</label>
                <input value={addName} onChange={e => setAddName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="예: 여성 가을 니트 원피스" autoFocus />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">도매가 (선택)</label>
                <input type="number" value={addPrice} onChange={e => setAddPrice(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="15000" />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setAddOpen(false)} className="px-4 py-2 text-sm bg-gray-100 rounded">취소</button>
              <button onClick={onAddManual} className="px-4 py-2 text-sm bg-emerald-600 text-white font-semibold rounded">추가</button>
            </div>
          </div>
        </div>
      )}

      {/* 도매매 수집 모달 */}
      {collectOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">도매매 마이박스 수집</h3>
              <button onClick={() => setCollectOpen(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <p className="text-xs text-amber-700 bg-amber-50 p-2 rounded mb-3">
              도매매 셀러 계정으로 Selenium 로그인 → 마이박스 페이지에서 상품 일괄 수집합니다.
              (DOM selector 는 도매매 페이지 구조에 맞춰 조정 필요)
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">도매매 아이디</label>
                <input value={collectId} onChange={e => setCollectId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded" autoComplete="off" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">비밀번호</label>
                <input type="password" value={collectPw} onChange={e => setCollectPw(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded" autoComplete="new-password" />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setCollectOpen(false)} className="px-4 py-2 text-sm bg-gray-100 rounded">취소</button>
              <button onClick={onCollectMybox} disabled={collecting}
                className="px-4 py-2 text-sm bg-emerald-600 text-white font-semibold rounded disabled:opacity-50">
                {collecting ? '수집 중...' : '수집 시작'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
