import { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
  LohasJob,
  getJob,
  listCategories,
  parseCategoriesFromLogs,
  runBulkEdit,
  startRestock,
  stopJob,
} from '../../api/lohas';

type TabKey = 'restock' | 'bulk';

const statusColor: Record<string, string> = {
  pending: 'bg-gray-200 text-gray-700',
  running: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  stopped: 'bg-yellow-100 text-yellow-700',
};

function useJobPoller(jobId: string | null): LohasJob | null {
  const [job, setJob] = useState<LohasJob | null>(null);
  const sinceRef = useRef(0);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      sinceRef.current = 0;
      return;
    }
    let stop = false;
    sinceRef.current = 0;
    setJob(null);

    const tick = async () => {
      if (stop) return;
      try {
        const data = await getJob(jobId, sinceRef.current);
        const logsSoFar = data.logs || [];
        sinceRef.current += logsSoFar.length;
        setJob((prev) => {
          const prevLogs = prev?.logs || [];
          return { ...data, logs: [...prevLogs, ...logsSoFar] };
        });
        if (data.status === 'running' || data.status === 'pending') {
          setTimeout(tick, 1200);
        }
      } catch {
        if (!stop) setTimeout(tick, 2500);
      }
    };
    tick();
    return () => {
      stop = true;
    };
  }, [jobId]);

  return job;
}

function LogPanel({ job }: { job: LohasJob | null }) {
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [job?.logs?.length]);

  if (!job) return null;
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-500">Job {job.id}</span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded ${statusColor[job.status] || ''}`}>
          {job.status}
        </span>
        {job.returncode !== null && (
          <span className="text-xs text-gray-400">rc={job.returncode}</span>
        )}
      </div>
      <div
        ref={logRef}
        className="bg-gray-900 text-green-300 font-mono text-xs rounded p-3 h-64 overflow-y-auto whitespace-pre-wrap"
      >
        {(job.logs || []).join('\n')}
      </div>
    </div>
  );
}

function RestockTab() {
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [codes, setCodes] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJobPoller(jobId);

  const running = job?.status === 'running' || job?.status === 'pending';

  const onStart = async () => {
    if (!user || !password || !codes.trim()) {
      toast.error('아이디/비번/상품코드를 모두 입력하세요');
      return;
    }
    try {
      const j = await startRestock(user, password, codes);
      setJobId(j.id);
      toast.success('재입고 작업 시작');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '작업 시작 실패');
    }
  };

  const onStop = async () => {
    if (!jobId) return;
    try {
      await stopJob(jobId);
      toast.success('중지 요청됨');
    } catch {
      toast.error('중지 실패');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h2 className="text-lg font-semibold mb-3">재입고 상품추가</h2>
      <p className="text-xs text-gray-500 mb-4">
        로하스 아이디/비번과 상품 코드를 입력하면 서버에서 헤드리스 크롬으로 자동 실행됩니다.
      </p>
      <div className="grid grid-cols-2 gap-3 mb-3">
        <input
          className="border rounded px-3 py-2 text-sm"
          placeholder="아이디"
          value={user}
          onChange={(e) => setUser(e.target.value)}
          disabled={running}
        />
        <input
          className="border rounded px-3 py-2 text-sm"
          placeholder="비밀번호"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={running}
        />
      </div>
      <textarea
        className="border rounded px-3 py-2 text-sm w-full font-mono"
        rows={6}
        placeholder="상품 코드를 한 줄에 하나씩 입력"
        value={codes}
        onChange={(e) => setCodes(e.target.value)}
        disabled={running}
      />
      <div className="flex gap-2 mt-3">
        <button
          onClick={onStart}
          disabled={running}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-semibold disabled:opacity-50"
        >
          ▶ 실행
        </button>
        <button
          onClick={onStop}
          disabled={!running}
          className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded text-sm font-semibold disabled:opacity-50"
        >
          🛑 중지
        </button>
      </div>
      <LogPanel job={job} />
    </div>
  );
}

function BulkEditTab() {
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<'1.0' | '2.0'>('1.0');

  const [listJobId, setListJobId] = useState<string | null>(null);
  const [runJobId, setRunJobId] = useState<string | null>(null);

  const listJob = useJobPoller(listJobId);
  const runJob = useJobPoller(runJobId);

  useEffect(() => {
    if (listJob?.status === 'success') {
      const cats = parseCategoriesFromLogs(listJob.logs || []);
      if (cats) {
        setCategories(cats);
        toast.success(`분류 ${cats.length}개 불러옴`);
      }
    }
  }, [listJob?.status]);

  const running = runJob?.status === 'running' || runJob?.status === 'pending';
  const listing = listJob?.status === 'running' || listJob?.status === 'pending';

  const onFetch = async () => {
    if (!user || !password) {
      toast.error('아이디/비번을 입력하세요');
      return;
    }
    try {
      const j = await listCategories(user, password);
      setListJobId(j.id);
      setCategories([]);
      setSelected(new Set());
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '분류 불러오기 실패');
    }
  };

  const toggle = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const onRun = async () => {
    if (selected.size === 0) {
      toast.error('분류를 하나 이상 선택하세요');
      return;
    }
    try {
      const j = await runBulkEdit(user, password, mode, Array.from(selected));
      setRunJobId(j.id);
      toast.success(`${mode} 실행 시작`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '실행 실패');
    }
  };

  const onStop = async () => {
    if (!runJobId) return;
    try {
      await stopJob(runJobId);
      toast.success('중지 요청됨');
    } catch {
      toast.error('중지 실패');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h2 className="text-lg font-semibold mb-3">간편 일괄 수정 (메인 탭)</h2>
      <p className="text-xs text-gray-500 mb-4">
        로그인 후 분류 목록을 불러오고, 선택한 분류에 대해 1.0 또는 2.0 작업을 실행합니다.
        (지마켓/11번가 업로드 탭은 추후 구현 예정)
      </p>
      <div className="grid grid-cols-2 gap-3 mb-3">
        <input
          className="border rounded px-3 py-2 text-sm"
          placeholder="아이디"
          value={user}
          onChange={(e) => setUser(e.target.value)}
        />
        <input
          className="border rounded px-3 py-2 text-sm"
          placeholder="비밀번호"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <button
        onClick={onFetch}
        disabled={listing || running}
        className="bg-gray-700 hover:bg-gray-800 text-white px-4 py-2 rounded text-sm font-semibold disabled:opacity-50 mb-4"
      >
        🔄 로그인 후 분류 불러오기
      </button>

      {categories.length > 0 && (
        <div className="border rounded p-3 mb-4 max-h-64 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold">분류 선택 ({selected.size}/{categories.length})</span>
            <div className="flex gap-1">
              <button
                className="text-xs text-blue-600 hover:underline"
                onClick={() => setSelected(new Set(categories))}
              >
                전체
              </button>
              <button
                className="text-xs text-gray-500 hover:underline"
                onClick={() => setSelected(new Set())}
              >
                해제
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-1">
            {categories.map((c) => (
              <label
                key={c}
                className="flex items-center gap-2 text-sm hover:bg-gray-50 px-2 py-1 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.has(c)}
                  onChange={() => toggle(c)}
                />
                <span className="truncate">{c}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-3 mb-3">
        <div className="flex gap-2">
          <label className="flex items-center gap-1 text-sm">
            <input
              type="radio"
              name="mode"
              checked={mode === '1.0'}
              onChange={() => setMode('1.0')}
            />
            1.0
          </label>
          <label className="flex items-center gap-1 text-sm">
            <input
              type="radio"
              name="mode"
              checked={mode === '2.0'}
              onChange={() => setMode('2.0')}
            />
            2.0
          </label>
        </div>
        <button
          onClick={onRun}
          disabled={running || categories.length === 0}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-semibold disabled:opacity-50"
        >
          ▶ {mode} 실행
        </button>
        <button
          onClick={onStop}
          disabled={!running}
          className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded text-sm font-semibold disabled:opacity-50"
        >
          🛑 중지
        </button>
      </div>

      {listJob && (
        <div>
          <p className="text-xs text-gray-500 mb-1">분류 불러오기 로그</p>
          <LogPanel job={listJob} />
        </div>
      )}
      {runJob && (
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-1">실행 로그</p>
          <LogPanel job={runJob} />
        </div>
      )}
    </div>
  );
}

export default function LohasPage() {
  const [tab, setTab] = useState<TabKey>('restock');
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">로하스</h1>
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setTab('restock')}
          className={`px-4 py-2 rounded text-sm font-semibold ${
            tab === 'restock' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
          }`}
        >
          재입고 상품추가
        </button>
        <button
          onClick={() => setTab('bulk')}
          className={`px-4 py-2 rounded text-sm font-semibold ${
            tab === 'bulk' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
          }`}
        >
          간편 일괄 수정
        </button>
      </div>
      {tab === 'restock' ? <RestockTab /> : <BulkEditTab />}
    </div>
  );
}
