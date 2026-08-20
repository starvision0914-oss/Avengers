import { useState, useEffect, useCallback, type ReactNode, type MouseEvent as ReactMouseEvent } from 'react';
import { PlayCircle, Package, BarChart3, RefreshCw, Download, TrendingUp } from 'lucide-react';
import api from '../../api/client';

interface WeeklyPopularFile {
  filename: string;
  size: number;
  saved_at: number;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n}B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)}KB`;
  return `${(n / 1024 / 1024).toFixed(1)}MB`;
}

interface AccountInfo {
  login_id: string;
  last_synced_at: string | null;
  last_new_count: number;
  balance: string;
  order_stats: Record<string, string>;
  subscription_info: { raw?: string[] };
  lowest_price_quota: Record<string, string>;
  info_synced_at: string | null;
}

const SUBSCRIPTION_LABEL_NOISE = new Set(['창업교육센터 교육']);
const SUBSCRIPTION_STATUS_WORDS = ['해지예정', '이용중', '해지'];
const SUBSCRIPTION_STATUS_COLOR: Record<string, string> = {
  이용중: '#16a34a',
  해지예정: '#d97706',
  해지: '#999',
};

// raw 라인 중 헤더/라벨 잡음을 걷어내고, 가장 최근(맨 앞) 항목의 상태만 뽑아낸다.
function latestSubscription(raw?: string[]): { period: string; status: string } | null {
  if (!raw || raw.length === 0) return null;
  const lines = raw
    .map(l => l.trim())
    .filter(l => l && !l.includes('종류') && !SUBSCRIPTION_LABEL_NOISE.has(l));
  for (let i = 0; i < lines.length; i++) {
    if (SUBSCRIPTION_STATUS_WORDS.includes(lines[i])) {
      const period = lines[i - 1]?.includes('~') ? lines[i - 1] : '';
      return { period, status: lines[i] };
    }
  }
  return null;
}

function parseNum(v?: string): number {
  if (!v) return 0;
  const n = parseInt(String(v).replace(/[^0-9-]/g, ''), 10);
  return isNaN(n) ? 0 : n;
}

function Sep() {
  return <span className="text-[#ddd] hidden md:inline">|</span>;
}

// 주문/배송현황: 백엔드 원본 키를 이 순서·라벨 그대로 각각 별도 열로 펼친다 ('반품/교환 완료'는 제외).
const ORDER_STATS_KEYS = ['배송중', '결제완료', '배송완료', '배송준비', '주문취소', '취소요청', '반품/교환 요청', '반품/교환 진행'];

// 최저가 선점권: 백엔드 원본 키 → 표시 라벨, 각각 별도 열.
const LOWEST_PRICE_COLUMNS: { key: string; label: string }[] = [
  { key: '누적 보유량', label: '최저가 보유량' },
  { key: '이번달 선점권', label: '선점권' },
  { key: '사용 가능 잔여 보유량', label: '잔여량' },
];

// 라벨 글자수에 맞춰 기본 폭을 "생략 없이 전부 보이도록" 넉넉하게 잡는다. (15px 폰트 기준)
const ORDER_STATS_WIDTH: Record<string, number> = {
  '반품/교환 요청': 145, '반품/교환 진행': 145,
};
const LOWEST_PRICE_WIDTH: Record<string, number> = {
  '누적 보유량': 140,
};

const COLUMNS = [
  { key: 'idx', label: '#', width: 40, align: 'center' as const, color: '#aaa' },
  { key: 'account', label: '계정', width: 120, align: 'left' as const, color: '#555' },
  { key: 'balance', label: '오너클랜머니', width: 140, align: 'right' as const, color: '#d97706' },
  ...ORDER_STATS_KEYS.map(k => ({ key: `os_${k}`, label: k, width: ORDER_STATS_WIDTH[k] || 95, align: 'right' as const, color: '#2563eb' })),
  ...LOWEST_PRICE_COLUMNS.map(c => ({ key: `lp_${c.key}`, label: c.label, width: LOWEST_PRICE_WIDTH[c.key] || 95, align: 'right' as const, color: '#dc2626' })),
  { key: 'sub', label: '구독서비스', width: 150, align: 'left' as const, color: '#7c3aed' },
];

function ResizableTh({ children, width, align, color, onResize }: {
  children: ReactNode; width: number; align: 'left' | 'right' | 'center'; color?: string;
  onResize: (newWidth: number) => void;
}) {
  const onMouseDown = (e: ReactMouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = width; // 드래그 시작 시점의 현재(이미 조절됐을 수 있는) 폭 — 계속 이어서 움직이도록 여기서 기준을 잡는다.
    const onMove = (ev: MouseEvent) => onResize(Math.max(36, startWidth + (ev.clientX - startX)));
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };
  return (
    <th
      className="relative border border-[#dde1e6] bg-[#f3f4f6] px-3 py-2 font-semibold overflow-hidden"
      style={{ width, color: color || '#555' }}
    >
      <span className={`block truncate ${align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'}`}>
        {children}
      </span>
      <div
        onMouseDown={onMouseDown}
        className="absolute top-0 right-0 h-full w-1.5 cursor-col-resize hover:bg-[#93c5fd] active:bg-[#60a5fa]"
        title="드래그해서 폭 조절"
      />
    </th>
  );
}

export default function OwnerclanCrawlerPage() {
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState('');
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [msg, setMsg] = useState('');

  const load = useCallback(() => {
    api.get('/ownerclan/api-crawl/').then(r => {
      setBusy(r.data.busy);
      setLog(r.data.log || '');
      setAccounts(r.data.accounts || []);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const handleStart = async () => {
    setMsg('');
    try {
      await api.post('/ownerclan/api-crawl/');
      setMsg('수집 시작됨 — 새 상품만 골라서 예비상품에 자동 추가됩니다.');
    } catch (e: any) {
      setMsg(e?.response?.data?.error || '시작 실패');
    }
    load();
  };

  const [weeklyFiles, setWeeklyFiles] = useState<WeeklyPopularFile[]>([]);
  const [weeklyBusy, setWeeklyBusy] = useState(false);
  const [weeklyMsg, setWeeklyMsg] = useState('');
  const [weeklyHistoryOpen, setWeeklyHistoryOpen] = useState(false);   // 이력은 기본 접힘, 최종 다운로드 시각만 메인에 표시

  const loadWeekly = useCallback(() => {
    api.get('/ownerclan/weekly-popular/').then(r => {
      setWeeklyFiles(r.data.files || []);
      setWeeklyBusy(r.data.busy);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    loadWeekly();
    const t = setInterval(loadWeekly, 10000);
    return () => clearInterval(t);
  }, [loadWeekly]);

  const handleWeeklyRun = async () => {
    setWeeklyMsg('');
    try {
      await api.post('/ownerclan/weekly-popular/');
      setWeeklyMsg('다운로드 시작됨 — 약 20~30초 소요');
      setTimeout(loadWeekly, 25000);
    } catch (e: any) {
      setWeeklyMsg(e?.response?.data?.error || '시작 실패');
    }
  };

  const handleWeeklyDownload = async (filename: string) => {
    try {
      const res = await api.get('/ownerclan/weekly-popular/download/', {
        params: { filename },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('다운로드 실패');
    }
  };

  const [infoMsg, setInfoMsg] = useState('');
  const handleInfoRefresh = async () => {
    setInfoMsg('');
    try {
      await api.post('/ownerclan/account-info-crawl/');
      setInfoMsg('계정정보 새로고침 시작됨 (약 15초 소요) — 잠시 후 자동 갱신됩니다.');
      setTimeout(load, 16000);
    } catch (e: any) {
      setInfoMsg(e?.response?.data?.error || '시작 실패');
    }
  };

  const exportExcel = () => {
    if (!accounts.length) { alert('내보낼 데이터가 없습니다.'); return; }
    const head = ['계정', '오너클랜머니', ...ORDER_STATS_KEYS, ...LOWEST_PRICE_COLUMNS.map(c => c.label), '구독상태', '구독기간'];
    const body = accounts.map(a => {
      const sub = latestSubscription(a.subscription_info?.raw);
      return [
        a.login_id,
        a.balance || '',
        ...ORDER_STATS_KEYS.map(k => a.order_stats?.[k] ?? ''),
        ...LOWEST_PRICE_COLUMNS.map(c => a.lowest_price_quota?.[c.key] ?? ''),
        sub?.status || '',
        sub?.period || '',
      ];
    });
    const csv = '﻿' + [head, ...body]
      .map(row => row.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
    link.href = url;
    link.download = `오너클랜_계정정보_${today}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const [colWidths, setColWidths] = useState<number[]>(COLUMNS.map(c => c.width));
  const resizeCol = (i: number, deltaX: number) => {
    setColWidths(prev => prev.map((w, j) => (j === i ? Math.max(36, COLUMNS[i].width + deltaX) : w)));
  };

  const sortedAccounts = [...accounts].sort((a, b) => parseNum(b.balance) - parseNum(a.balance));

  const totalBalance = accounts.reduce((sum, a) => sum + parseNum(a.balance), 0);
  const orderTotals: Record<string, number> = {};
  for (const k of ORDER_STATS_KEYS) {
    orderTotals[k] = accounts.reduce((sum, a) => sum + parseNum(a.order_stats?.[k]), 0);
  }
  const lowestTotals: Record<string, number> = {};
  for (const c of LOWEST_PRICE_COLUMNS) {
    lowestTotals[c.key] = accounts.reduce((sum, a) => sum + parseNum(a.lowest_price_quota?.[c.key]), 0);
  }
  const lastInfoSync = accounts.reduce<string | null>((latest, a) => {
    if (!a.info_synced_at) return latest;
    return !latest || a.info_synced_at > latest ? a.info_synced_at : latest;
  }, null);

  return (
    <div className="min-h-screen bg-[#f5f6fa] min-w-0 w-full max-w-full overflow-x-hidden">

      {/* ── 상단 고정 바 ── */}
      <div className="bg-white border-b border-[#e0e0e0] px-4 md:px-6 py-2 sticky top-0 z-30">
        <div className="max-w-[1900px] mx-auto flex items-center gap-2">
          <Package size={16} className="text-[#2563eb]" />
          <h1 className="text-[15px] font-bold text-[#222]">오너클랜 대시보드</h1>
          {lastInfoSync && (
            <span className="text-[13px] text-[#999] ml-1">
              최근 정보동기화 <b className="text-[#2563eb]">{new Date(lastInfoSync).toLocaleString('ko-KR')}</b>
            </span>
          )}
        </div>
      </div>

      <div className="max-w-[1900px] mx-auto px-4 md:px-6 py-3 space-y-3 min-w-0">

        {/* ── 컨트롤 바 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[15px]">
          <span className="font-bold text-[#333]">오너클랜</span>
          <span className="text-[#888]">계정 <b className="text-[#333]">{accounts.length}개</b></span>
          <span className="ml-auto flex items-center gap-2">
            <button onClick={exportExcel} disabled={!accounts.length}
              className="flex items-center gap-1 px-2.5 py-1 text-[14px] font-semibold bg-[#15803d] text-white rounded hover:bg-[#166534] disabled:opacity-50 disabled:cursor-not-allowed">
              <Download size={12} /> 엑셀 다운로드
            </button>
            <button onClick={handleInfoRefresh}
              className="flex items-center gap-1 px-2.5 py-1 text-[14px] font-semibold text-white rounded bg-[#16a34a] hover:bg-[#15803d]">
              <RefreshCw size={12} /> 계정정보 새로고침
            </button>
            <button onClick={handleStart} disabled={busy}
              className="flex items-center gap-1.5 px-3 py-1 text-[14px] font-semibold text-white rounded disabled:opacity-50"
              style={{ background: busy ? '#aaa' : '#2563eb' }}>
              <PlayCircle size={13} className={busy ? 'animate-spin' : ''} />
              {busy ? '수집 중…' : '새 상품 가져오기'}
            </button>
          </span>
        </div>
        {(msg || infoMsg) && (
          <div className="text-[13px] font-semibold px-1 space-x-3">
            {msg && <span className="text-[#2563eb]">{msg}</span>}
            {infoMsg && <span className="text-[#16a34a]">{infoMsg}</span>}
          </div>
        )}

        {/* ── KPI 요약 바 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-4 md:px-5 py-2.5 text-[15px]">
            <span>
              <span className="text-[#888] mr-1">오너클랜머니 합계:</span>
              <span className="font-bold text-[#d97706]">{totalBalance.toLocaleString()}원</span>
            </span>
            <Sep />
            {ORDER_STATS_KEYS.map(k => (
              <span key={k}>
                <span className="text-[#888] mr-1">{k}:</span>
                <span className="font-bold text-[#2563eb]">{orderTotals[k] ?? 0}</span>
              </span>
            ))}
            <Sep />
            {LOWEST_PRICE_COLUMNS.map(c => (
              <span key={c.key}>
                <span className="text-[#888] mr-1">{c.label}:</span>
                <span className="font-bold text-[#dc2626]">{lowestTotals[c.key] ?? 0}개</span>
              </span>
            ))}
          </div>
        </div>

        {/* ── 주간 인기 상품(db저장창고) ── */}
        <div className="bg-white border border-[#e0e0e0] rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-[#f0f0f0] flex items-center gap-2">
            <TrendingUp size={15} className="text-[#dc2626]" />
            <span className="text-[15px] font-bold text-[#222]">주간 인기 상품 (db저장창고)</span>
            <span className="text-[13px] text-[#999]">
              매일 09:00 자동 저장 · 계정 무관 사이트 전체 랭킹
              {weeklyFiles[0] && <> · 최종 다운로드: <span className="font-semibold text-[#333]">{new Date(weeklyFiles[0].saved_at * 1000).toLocaleString('ko-KR')}</span></>}
            </span>
            <span className="ml-auto flex items-center gap-2">
              {weeklyMsg && <span className="text-[13px] font-semibold text-[#2563eb]">{weeklyMsg}</span>}
              <button onClick={() => setWeeklyHistoryOpen(o => !o)}
                className="flex items-center gap-1 px-3 py-1 text-[13px] font-semibold text-[#555] bg-[#f3f4f6] rounded hover:bg-[#e5e7eb]">
                {weeklyHistoryOpen ? '이력 접기' : `이력 보기 (${weeklyFiles.length})`}
              </button>
              <button onClick={handleWeeklyRun} disabled={weeklyBusy}
                className="flex items-center gap-1.5 px-3 py-1 text-[14px] font-semibold text-white rounded disabled:opacity-50"
                style={{ background: weeklyBusy ? '#aaa' : '#dc2626' }}>
                <PlayCircle size={13} className={weeklyBusy ? 'animate-spin' : ''} />
                {weeklyBusy ? '다운로드 중…' : '지금 다운로드'}
              </button>
            </span>
          </div>
          {weeklyHistoryOpen && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[15px]">
              <thead>
                <tr>
                  <th className="border border-[#dde1e6] bg-[#f3f4f6] px-3 py-2 text-left font-semibold text-[#555]">파일명</th>
                  <th className="border border-[#dde1e6] bg-[#f3f4f6] px-3 py-2 text-right font-semibold text-[#555] w-28">크기</th>
                  <th className="border border-[#dde1e6] bg-[#f3f4f6] px-3 py-2 text-left font-semibold text-[#555] w-48">저장 시각</th>
                  <th className="border border-[#dde1e6] bg-[#f3f4f6] px-3 py-2 text-center font-semibold text-[#555] w-24">다운로드</th>
                </tr>
              </thead>
              <tbody>
                {weeklyFiles.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="border border-[#e5e7eb] px-4 py-10 text-center text-[#aaa]">
                      아직 저장된 파일이 없습니다
                    </td>
                  </tr>
                ) : (
                  weeklyFiles.map((f, idx) => (
                    <tr key={f.filename} className={idx % 2 === 1 ? 'bg-[#fafbfc]' : 'bg-white'}>
                      <td className="border border-[#e5e7eb] px-3 py-2 font-semibold text-[#333]">{f.filename}</td>
                      <td className="border border-[#e5e7eb] px-3 py-2 text-right tabular-nums text-[#555]">{formatBytes(f.size)}</td>
                      <td className="border border-[#e5e7eb] px-3 py-2 text-[#555]">{new Date(f.saved_at * 1000).toLocaleString('ko-KR')}</td>
                      <td className="border border-[#e5e7eb] px-3 py-2 text-center">
                        <button onClick={() => handleWeeklyDownload(f.filename)}
                          className="inline-flex items-center gap-1 px-2 py-0.5 text-[13px] font-semibold text-white bg-[#2563eb] rounded hover:bg-[#1d4ed8]">
                          <Download size={11} /> 받기
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          )}
        </div>

        {/* ── 계정별 현황 테이블 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-[#f0f0f0] flex items-center gap-2">
            <BarChart3 size={15} className="text-[#2563eb]" />
            <span className="text-[15px] font-bold text-[#222]">계정별 현황</span>
          </div>
          <div className="overflow-x-auto">
            <table className="border-collapse text-[15px]" style={{ tableLayout: 'fixed', width: colWidths.reduce((a, b) => a + b, 0) }}>
              <colgroup>
                {colWidths.map((w, i) => <col key={COLUMNS[i].key} style={{ width: w }} />)}
              </colgroup>
              <thead>
                <tr>
                  {COLUMNS.map((c, i) => (
                    <ResizableTh key={c.key} width={colWidths[i]} align={c.align} color={c.color}
                      onResize={dx => resizeCol(i, dx)}>
                      {c.label}
                    </ResizableTh>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedAccounts.length === 0 ? (
                  <tr>
                    <td colSpan={COLUMNS.length} className="border border-[#e5e7eb] px-4 py-10 text-center text-[#aaa]">
                      데이터 없음 — 계정정보 새로고침 후 표시됩니다
                    </td>
                  </tr>
                ) : (
                  sortedAccounts.map((a, idx) => {
                    const sub = latestSubscription(a.subscription_info?.raw);
                    return (
                      <tr key={a.login_id} className={idx % 2 === 1 ? 'bg-[#fafbfc]' : 'bg-white'}>
                        <td className="border border-[#e5e7eb] px-3 py-2 text-center text-[#bbb] font-medium align-top">{idx + 1}</td>
                        <td className="border border-[#e5e7eb] px-3 py-2 font-semibold text-[#333] align-top truncate">{a.login_id}</td>
                        <td className="border border-[#e5e7eb] px-3 py-2 text-right font-bold text-[#222] align-top tabular-nums">{a.balance || '-'}</td>
                        {ORDER_STATS_KEYS.map(k => (
                          <td key={k} className="border border-[#e5e7eb] px-3 py-2 text-right align-top tabular-nums text-[#333]">
                            {a.order_stats?.[k] ?? <span className="text-[#ccc]">-</span>}
                          </td>
                        ))}
                        {LOWEST_PRICE_COLUMNS.map(c => (
                          <td key={c.key} className="border border-[#e5e7eb] px-3 py-2 text-right align-top tabular-nums text-[#333]">
                            {a.lowest_price_quota?.[c.key] ?? <span className="text-[#ccc]">-</span>}
                          </td>
                        ))}
                        <td className="border border-[#e5e7eb] px-3 py-2 align-top">
                          {sub ? (
                            <div>
                              <span className="font-bold" style={{ color: SUBSCRIPTION_STATUS_COLOR[sub.status] || '#555' }}>
                                {sub.status}
                              </span>
                              {sub.period && <div className="text-[14px] text-[#999] mt-0.5">{sub.period}</div>}
                            </div>
                          ) : (
                            <span className="text-[#ccc]">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
                {sortedAccounts.length > 0 && (
                  <tr className="font-bold text-[#333] bg-[#eef1f5]">
                    <td className="border border-[#e5e7eb] px-3 py-2"></td>
                    <td className="border border-[#e5e7eb] px-3 py-2">합계 ({sortedAccounts.length}개)</td>
                    <td className="border border-[#e5e7eb] px-3 py-2 text-right text-[#d97706] tabular-nums">{totalBalance.toLocaleString()}원</td>
                    {ORDER_STATS_KEYS.map(k => (
                      <td key={k} className="border border-[#e5e7eb] px-3 py-2 text-right tabular-nums text-[#2563eb]">{orderTotals[k] ?? 0}</td>
                    ))}
                    {LOWEST_PRICE_COLUMNS.map(c => (
                      <td key={c.key} className="border border-[#e5e7eb] px-3 py-2 text-right tabular-nums text-[#dc2626]">{lowestTotals[c.key] ?? 0}</td>
                    ))}
                    <td className="border border-[#e5e7eb] px-3 py-2"></td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── 진행 로그 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded-xl p-5">
          <div className="text-[14px] font-bold text-[#333] mb-2">진행 로그</div>
          <pre className="text-[12px] text-[#444] bg-[#f8fafc] rounded p-3 overflow-auto max-h-[400px] whitespace-pre-wrap">
            {log || '아직 실행 기록이 없습니다.'}
          </pre>
        </div>
      </div>
    </div>
  );
}
