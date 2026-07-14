import { useState, useEffect, useCallback, type ReactNode, type MouseEvent as ReactMouseEvent } from 'react';
import { PlayCircle, Package, BarChart3, RefreshCw, Download } from 'lucide-react';
import api from '../../api/client';

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

// 계정별 dict 배열을 키 등장 순서를 유지한 채 합산한다.
function sumEntries(list: (Record<string, string> | undefined)[]): [string, string][] {
  const totals: Record<string, number> = {};
  const order: string[] = [];
  for (const rec of list) {
    for (const [k, v] of Object.entries(rec || {})) {
      if (!(k in totals)) { totals[k] = 0; order.push(k); }
      totals[k] += parseNum(v);
    }
  }
  return order.map(k => [k, String(totals[k])]);
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

const COLUMNS = [
  { key: 'idx', label: '#', width: 48, align: 'center' as const, color: '#aaa' },
  { key: 'account', label: '계정', width: 150, align: 'left' as const, color: '#555' },
  { key: 'balance', label: '오너클랜머니', width: 140, align: 'right' as const, color: '#d97706' },
  ...ORDER_STATS_KEYS.map(k => ({ key: `os_${k}`, label: k, width: 90, align: 'right' as const, color: '#2563eb' })),
  ...LOWEST_PRICE_COLUMNS.map(c => ({ key: `lp_${c.key}`, label: c.label, width: 100, align: 'right' as const, color: '#dc2626' })),
  { key: 'sub', label: '구독서비스', width: 190, align: 'left' as const, color: '#7c3aed' },
];

function ResizableTh({ children, width, align, color, onResize }: {
  children: ReactNode; width: number; align: 'left' | 'right' | 'center'; color?: string;
  onResize: (deltaX: number) => void;
}) {
  const onMouseDown = (e: ReactMouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const onMove = (ev: MouseEvent) => onResize(ev.clientX - startX);
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };
  return (
    <th
      className={`relative border border-[#dde1e6] bg-[#f3f4f6] px-3 py-2 font-semibold whitespace-nowrap ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
      }`}
      style={{ width, color: color || '#555' }}
    >
      {children}
      <div
        onMouseDown={onMouseDown}
        className="absolute top-0 right-0 h-full w-1.5 cursor-col-resize hover:bg-[#93c5fd] active:bg-[#60a5fa]"
        title="드래그해서 폭 조절"
      />
    </th>
  );
}

function StatList({ entries, unit, layout = 'col' }: { entries: [string, string][]; unit: string; layout?: 'col' | 'row' }) {
  if (entries.length === 0) return <span className="text-[#ccc]">-</span>;
  if (layout === 'row') {
    return (
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[#333]">
        {entries.map(([k, v]) => (
          <span key={k} className="whitespace-nowrap">
            <span className="text-[#888]">{k}</span> <span className="font-bold text-[#222]">{v}{unit}</span>
          </span>
        ))}
      </div>
    );
  }
  return (
    <div className="text-[#333] space-y-1">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-baseline justify-between gap-2">
          <span className="text-[#888] truncate">{k}</span>
          <span className="font-bold text-[#222] shrink-0">{v}{unit}</span>
        </div>
      ))}
    </div>
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
    const orderKeys = filterOrderStats(sumEntries(accounts.map(a => a.order_stats))).map(([k]) => k);
    const lowestKeys = mapLowestPriceLabel(sumEntries(accounts.map(a => a.lowest_price_quota))).map(([k]) => k);
    const head = ['계정', '오너클랜머니', ...orderKeys, ...lowestKeys, '구독상태', '구독기간'];
    const body = accounts.map(a => {
      const os = Object.fromEntries(Object.entries(a.order_stats || {}));
      const lp = Object.fromEntries(mapLowestPriceLabel(Object.entries(a.lowest_price_quota || {})));
      const sub = latestSubscription(a.subscription_info?.raw);
      return [
        a.login_id,
        a.balance || '',
        ...orderKeys.map(k => os[k] ?? ''),
        ...lowestKeys.map(k => lp[k] ?? ''),
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
  const totalOrderStats = sumEntries(accounts.map(a => a.order_stats));
  const totalLowestPrice = sumEntries(accounts.map(a => a.lowest_price_quota));
  const lastInfoSync = accounts.reduce<string | null>((latest, a) => {
    if (!a.info_synced_at) return latest;
    return !latest || a.info_synced_at > latest ? a.info_synced_at : latest;
  }, null);

  return (
    <div className="min-h-screen bg-[#f5f6fa]">

      {/* ── 상단 고정 바 ── */}
      <div className="bg-white border-b border-[#e0e0e0] px-4 md:px-6 py-2 sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto flex items-center gap-2">
          <Package size={16} className="text-[#2563eb]" />
          <h1 className="text-[15px] font-bold text-[#222]">오너클랜 대시보드</h1>
          {lastInfoSync && (
            <span className="text-[13px] text-[#999] ml-1">
              최근 정보동기화 <b className="text-[#2563eb]">{new Date(lastInfoSync).toLocaleString('ko-KR')}</b>
            </span>
          )}
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-3 space-y-3">

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
            {filterOrderStats(totalOrderStats).map(([k, v]) => (
              <span key={k}>
                <span className="text-[#888] mr-1">{k}:</span>
                <span className="font-bold text-[#2563eb]">{v}</span>
              </span>
            ))}
            <Sep />
            {mapLowestPriceLabel(totalLowestPrice).map(([k, v]) => (
              <span key={k}>
                <span className="text-[#888] mr-1">{k}:</span>
                <span className="font-bold text-[#dc2626]">{v}개</span>
              </span>
            ))}
          </div>
        </div>

        {/* ── 계정별 현황 테이블 ── */}
        <div className="bg-white border border-[#e0e0e0] rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-[#f0f0f0] flex items-center gap-2">
            <BarChart3 size={15} className="text-[#2563eb]" />
            <span className="text-[15px] font-bold text-[#222]">계정별 현황</span>
          </div>
          <div className="overflow-x-auto">
            <table className="border-collapse text-[17px]" style={{ tableLayout: 'fixed', width: colWidths.reduce((a, b) => a + b, 0) }}>
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
                    <td colSpan={6} className="border border-[#e5e7eb] px-4 py-10 text-center text-[#aaa]">
                      데이터 없음 — 계정정보 새로고침 후 표시됩니다
                    </td>
                  </tr>
                ) : (
                  sortedAccounts.map((a, idx) => {
                    const sub = latestSubscription(a.subscription_info?.raw);
                    return (
                      <tr key={a.login_id} className={idx % 2 === 1 ? 'bg-[#fafbfc]' : 'bg-white'}>
                        <td className="border border-[#e5e7eb] px-3 py-2 text-center text-[#bbb] font-medium align-top">{idx + 1}</td>
                        <td className="border border-[#e5e7eb] px-3 py-2 font-semibold text-[#333] align-top">{a.login_id}</td>
                        <td className="border border-[#e5e7eb] px-3 py-2 text-right font-bold text-[#222] align-top tabular-nums">{a.balance || '-'}</td>
                        <td className="border border-[#e5e7eb] px-3 py-2 align-top">
                          <StatList entries={filterOrderStats(Object.entries(a.order_stats || {}))} unit="" layout="row" />
                        </td>
                        <td className="border border-[#e5e7eb] px-3 py-2 align-top">
                          <StatList entries={mapLowestPriceLabel(Object.entries(a.lowest_price_quota || {}))} unit="개" />
                        </td>
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
                    <td className="border border-[#e5e7eb] px-3 py-2">
                      <StatList entries={filterOrderStats(totalOrderStats)} unit="" layout="row" />
                    </td>
                    <td className="border border-[#e5e7eb] px-3 py-2">
                      <StatList entries={mapLowestPriceLabel(totalLowestPrice)} unit="개" />
                    </td>
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
