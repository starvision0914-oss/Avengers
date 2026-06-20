import { useState, useMemo, useRef, useCallback } from 'react';
import type { St11SellerRow, St11TotalsSummary, St11Unmatched } from '../../types/st11';
import { formatKRW } from '../../utils/format';

interface Props {
  sellers: St11SellerRow[];
  totals: St11TotalsSummary;
  selectedSeller: string | null;
  onSelectSeller: (id: string | null) => void;
  onCostClick: (sellerId: string, alias: string, kind?: string) => void;
  blockedIds?: Set<string>;
  onDismissBlocked?: (sellerId: string) => void;
  unmatched?: St11Unmatched;
}

const GRADE_COLORS: Record<number, { bg: string; text: string }> = {
  1: { bg: '#fef2f2', text: '#dc2626' },
  2: { bg: '#fff3e0', text: '#e67700' },
  3: { bg: '#e7f5ff', text: '#1a73e8' },
  4: { bg: '#f0fdf4', text: '#16a34a' },
  5: { bg: '#f0fdf4', text: '#00a651' },
};

function GradeBadge({ grade }: { grade?: number | null }) {
  if (grade == null) return <span style={{ color: '#999' }}>-</span>;
  const c = GRADE_COLORS[grade] || { bg: '#f5f5f5', text: '#111' };
  return <span style={{ background: c.bg, color: c.text, padding: '2px 8px', borderRadius: 4, fontWeight: 700, fontSize: 13 }}>{grade}등급</span>;
}

function OfficeBadge({ value }: { value?: string }) {
  if (!value) return <span style={{ color: '#999' }}>-</span>;
  const rate = value.split(' ')[0];   // "우수 97.3%" → 첫 단어로 색 결정
  const color = rate === '우수' ? '#00a651' : rate === '경고' ? '#dc2626' : rate === '주의' ? '#e67700' : '#111';
  return <span style={{ color, fontWeight: 700, fontSize: 12 }}>{value}</span>;
}

// 배송/상품/CS 평가 등급 정렬용 랭크 (우수 > 양호 > 주의 > 경고 > 미평가/없음)
const OFFICE_RANK: Record<string, number> = { '우수': 4, '양호': 3, '주의': 2, '경고': 1, '미평가': 0 };
function officeRank(v?: string): number { return v ? (OFFICE_RANK[v.split(' ')[0]] ?? -1) : -1; }

type SortKey = 'seller_alias' | 'grade' | 'cash' | 'point' | 'cpc_spend' | 'charge' | 'balance' | 'products' | 'available' | 'tx_count' | 'ship' | 'prod' | 'cs' | 'sales' | 'cost' | 'margin_rate' | 'net_margin_rate' | 'server_fee' | 'reward' | 'net_profit' | 'time';

// 구매마진율 = (매출 − 구매가) / 매출 × 100 (매출 대비 구매가 빼고 남는 비율)
function marginRate(s: St11SellerRow): number { return (s.sales || 0) > 0 ? ((s.sales! - (s.cost || 0)) / s.sales!) * 100 : 0; }
// 순수익마진율 = 순수익 / 매출 × 100 (광고비 등 다 뺀 순수익의 매출 대비 비율)
function netMarginRate(s: St11SellerRow): number { return (s.sales || 0) > 0 ? ((s.net_profit || 0) / s.sales!) * 100 : 0; }

function getVal(s: St11SellerRow, key: SortKey): number | string {
  switch (key) {
    case 'seller_alias': return s.seller_alias || s.seller_id;
    case 'grade': return s.grade ?? 99;
    case 'cash': return s.cash ?? 0;
    case 'point': return s.point ?? 0;
    case 'cpc_spend': return s.cpc_spend ?? 0;
    case 'sales': return s.sales ?? 0;
    case 'cost': return s.cost ?? 0;
    case 'margin_rate': return marginRate(s);
    case 'net_margin_rate': return netMarginRate(s);
    case 'server_fee': return s.server_fee ?? 0;
    case 'reward': return s.reward ?? 0;
    case 'net_profit': return s.net_profit ?? 0;
    case 'time': { const t = s.cookie_saved_at || s.last_otp_at; return t ? new Date(t).getTime() : 0; }
    case 'charge': return (s.charge || 0) + ((s as any).settle || 0) + (s.reward || 0) - (s.server_fee || 0);
    case 'balance': return s.balance ?? 0;
    case 'products': return s.products ?? 0;
    case 'available': return s.available ?? 0;
    case 'tx_count': return s.tx_count ?? 0;
    case 'ship': return officeRank(s.fulfillment);
    case 'prod': return officeRank(s.shipping);
    case 'cs': return officeRank(s.inquiry);
    default: return 0;
  }
}

interface ColDef { key: string; label: string; sortKey?: SortKey; align: 'left' | 'center' | 'right'; initWidth: number; minWidth: number; }

const INIT_COLS: ColDef[] = [
  { key: '#', label: '#', align: 'center', initWidth: 32, minWidth: 28 },
  { key: 'seller', label: '셀러', sortKey: 'seller_alias', align: 'left', initWidth: 200, minWidth: 100 },
  { key: 'grade', label: '등급', sortKey: 'grade', align: 'center', initWidth: 60, minWidth: 48 },
  { key: 'cash', label: '캐시', sortKey: 'cash', align: 'right', initWidth: 90, minWidth: 50 },
  { key: 'point', label: '포인트', sortKey: 'point', align: 'right', initWidth: 82, minWidth: 50 },
  { key: 'cpc', label: '광고비', sortKey: 'cpc_spend', align: 'right', initWidth: 110, minWidth: 60 },
  { key: 'sales', label: '매출', sortKey: 'sales', align: 'right', initWidth: 100, minWidth: 60 },
  { key: 'cost', label: '구매가', sortKey: 'cost', align: 'right', initWidth: 96, minWidth: 60 },
  { key: 'margin_rate', label: '구매마진율', sortKey: 'margin_rate', align: 'right', initWidth: 88, minWidth: 56 },
  { key: 'net_profit', label: '순수익', sortKey: 'net_profit', align: 'right', initWidth: 100, minWidth: 60 },
  { key: 'net_margin_rate', label: '순수익마진율', sortKey: 'net_margin_rate', align: 'right', initWidth: 96, minWidth: 60 },
  { key: 'charge', label: '충전/정산·서버료', sortKey: 'charge', align: 'right', initWidth: 140, minWidth: 80 },
  { key: 'products', label: '상품', sortKey: 'products', align: 'right', initWidth: 98, minWidth: 50 },
  { key: 'available', label: '등록', sortKey: 'available', align: 'right', initWidth: 52, minWidth: 36 },
  { key: 'ship', label: '이행', sortKey: 'ship', align: 'center', initWidth: 78, minWidth: 48 },
  { key: 'prod', label: '배송', sortKey: 'prod', align: 'center', initWidth: 78, minWidth: 48 },
  { key: 'cs', label: 'CS', sortKey: 'cs', align: 'center', initWidth: 78, minWidth: 48 },
  { key: 'time', label: '인증(로그인)', sortKey: 'time', align: 'left', initWidth: 110, minWidth: 64 },
];

export default function St11SummaryTable({ sellers, totals, selectedSeller, onSelectSeller, onCostClick, blockedIds, onDismissBlocked, unmatched }: Props) {
  const [hideEmpty, setHideEmpty] = useState(false);
  const [onlyZero, setOnlyZero] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [widths, setWidths] = useState(INIT_COLS.map(c => c.initWidth));
  const [pinned, setPinned] = useState<Set<number>>(new Set([1]));
  const dragRef = useRef<{ idx: number; startX: number; startW: number } | null>(null);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) { if (!sortAsc) { setSortKey(null); setSortAsc(true); return; } setSortAsc(false); }
    else { setSortKey(key); setSortAsc(true); }
  };
  const arrow = (key: SortKey) => sortKey === key ? (sortAsc ? ' ▲' : ' ▼') : '';

  const togglePin = useCallback((idx: number) => {
    setPinned(prev => { const n = new Set(prev); if (n.has(idx)) n.delete(idx); else n.add(idx); return n; });
  }, []);

  const onResizeStart = useCallback((e: React.MouseEvent, idx: number) => {
    e.preventDefault();
    e.stopPropagation();
    dragRef.current = { idx, startX: e.clientX, startW: widths[idx] };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const newW = Math.max(INIT_COLS[dragRef.current.idx].minWidth, dragRef.current.startW + (ev.clientX - dragRef.current.startX));
      setWidths(prev => prev.map((w, i) => i === dragRef.current!.idx ? newW : w));
    };
    const onUp = () => { dragRef.current = null; document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [widths]);

  const zeroCount = useMemo(() => sellers.filter(s => (s.cpc_spend || 0) === 0).length, [sellers]);
  const base = onlyZero
    ? sellers.filter(s => (s.cpc_spend || 0) === 0)
    : hideEmpty
      ? sellers.filter(s => s.cpc_spend > 0 || s.charge > 0 || (s.products || 0) > 0 || (s.cash || 0) > 0 || (s.point || 0) > 0)
      : sellers;
  const filtered = useMemo(() => {
    if (!sortKey) return base;
    return [...base].sort((a, b) => {
      const va = getVal(a, sortKey), vb = getVal(b, sortKey);
      if (typeof va === 'string' && typeof vb === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortAsc ? (va as number) - (vb as number) : (vb as number) - (va as number);
    });
  }, [base, sortKey, sortAsc]);

  const getLeft = (idx: number): number | undefined => {
    if (!pinned.has(idx)) return undefined;
    let left = 0;
    for (let i = 0; i < idx; i++) if (pinned.has(i)) left += widths[i];
    return left;
  };

  const stickyTh = (idx: number): React.CSSProperties => {
    const left = getLeft(idx);
    if (left === undefined) return {};
    return { position: 'sticky', left, zIndex: 12, background: '#eef3ff', boxShadow: '2px 0 4px rgba(0,0,0,0.08)' };
  };
  const stickyTd = (idx: number, rowBg: string): React.CSSProperties => {
    const left = getLeft(idx);
    if (left === undefined) return {};
    return { position: 'sticky', left, zIndex: 1, background: pinned.has(idx) ? '#f0f4ff' : rowBg, boxShadow: '2px 0 4px rgba(0,0,0,0.05)' };
  };
  const stickyFt = (idx: number): React.CSSProperties => {
    const left = getLeft(idx);
    if (left === undefined) return {};
    return { position: 'sticky', left, zIndex: 3, background: '#eef3ff', boxShadow: '2px 0 4px rgba(0,0,0,0.08)' };
  };

  const renderCell = (s: St11SellerRow, col: ColDef, i: number) => {
    const isCash = s.cost_type === 'sellercash';
    const totalMoney = (s.cash || 0) + (s.point || 0);
    const isLow = totalMoney > 0 && totalMoney < 50000;
    switch (col.key) {
      case '#': return <>{i + 1}</>;
      case 'seller': return <><span style={{ fontWeight: 600, color: s.no_api ? '#e67700' : undefined }} title={s.no_api ? 'api 없는 대기/정지 계정' : undefined}>{s.seller_alias}</span><span style={{ fontSize: 13, color: '#888', marginLeft: 4 }}>({s.seller_id})</span></>;
      case 'grade': return <GradeBadge grade={s.grade} />;
      case 'cash': return (s.cash || 0) !== 0 ? <span style={{ color: isLow ? '#dc2626' : '#0369a1', fontWeight: isLow ? 700 : 600 }}>{formatKRW(s.cash!)}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'point': return (s.point || 0) !== 0 ? <span style={{ color: isLow ? '#dc2626' : '#7c3aed', fontWeight: isLow ? 700 : 600 }}>{formatKRW(s.point!)}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'cpc': { const delta = (s as any).cpc_delta ?? 0; return <><span style={{ color: s.cpc_spend > 0 ? '#e67700' : '#999', fontWeight: s.cpc_spend > 0 ? 700 : 400, cursor: 'pointer' }} onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'cpc'); }}>{s.cpc_spend > 0 ? formatKRW(s.cpc_spend) : '-'}</span><span style={{ fontSize: 11, color: delta > 0 ? '#dc2626' : '#999', marginLeft: 3 }}>({delta > 0 ? '+' : ''}{formatKRW(delta)})</span></>; }
      case 'sales': return (s.sales || 0) > 0 ? <span style={{ color: '#0369a1', fontWeight: 600 }} title={`매출 ${(s.sales_count || 0).toLocaleString()}건`}>{formatKRW(s.sales!)}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'cost': return (s.cost || 0) > 0 ? <span style={{ color: '#92400e' }}>{formatKRW(s.cost!)}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'margin_rate': { if ((s.sales || 0) <= 0) return <span style={{ color: '#999' }}>-</span>; const r = marginRate(s); return <span style={{ color: r > 0 ? '#0369a1' : '#dc2626', fontWeight: 600 }}>{r.toFixed(1)}%</span>; }
      case 'net_margin_rate': { if ((s.sales || 0) <= 0) return <span style={{ color: '#999' }}>-</span>; const r = netMarginRate(s); return <span style={{ color: r > 0 ? '#15803d' : r < 0 ? '#dc2626' : '#666', fontWeight: 700 }}>{r.toFixed(1)}%</span>; }
      case 'server_fee': return (s.server_fee || 0) > 0 ? <span style={{ color: '#b45309', cursor: 'pointer', textDecoration: 'underline dotted' }} title="서버이용료 상세 보기" onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'server_fee'); }}>{formatKRW(s.server_fee!)}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'reward': return (s.reward || 0) > 0 ? <span style={{ color: '#15803d' }}>+{formatKRW(s.reward!)}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'net_profit': { const np = s.net_profit ?? 0; const hasData = (s.sales || 0) > 0 || (s.cpc_spend || 0) > 0; if (!hasData) return <span style={{ color: '#999' }}>-</span>; return <span style={{ color: np > 0 ? '#15803d' : np < 0 ? '#dc2626' : '#666', fontWeight: 700 }}>{formatKRW(np)}</span>; }
      case 'charge': {
        const combined = (s.charge || 0) + ((s as any).settle || 0) + (s.reward || 0);
        const fee = s.server_fee || 0;
        if (combined === 0 && fee === 0) return <span style={{ color: '#999' }}>-</span>;
        return <>
          {combined !== 0
            ? <span style={{ color: '#2e7d32', cursor: 'pointer', textDecoration: 'underline dotted' }} title="충전·정산·프로모션 상세 보기" onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'settle'); }}>{formatKRW(combined)}</span>
            : <span style={{ color: '#999' }}>0</span>}
          {fee > 0 && <span style={{ fontSize: 11, color: '#dc2626', marginLeft: 3, cursor: 'pointer' }} title="서버이용료 상세 보기" onClick={e => { e.stopPropagation(); onCostClick(s.seller_id, s.seller_alias, 'server_fee'); }}>−{formatKRW(fee)}</span>}
        </>;
      }
      case 'balance': return isCash ? (s.balance < 0 ? <span style={{ color: '#dc2626', fontWeight: 700 }}>{formatKRW(Math.abs(s.balance))}</span> : <span style={{ color: '#999' }}>-</span>) : (s.balance !== 0 ? <span style={{ color: s.balance > 0 ? '#0369a1' : '#dc2626', fontWeight: 600 }}>{formatKRW(s.balance)}</span> : <span style={{ color: '#999' }}>-</span>);
      case 'products': return (s.products || 0) > 0 ? <>{s.products!.toLocaleString()}<span style={{ fontSize: 12, color: '#888' }}>/{(s.product_limit || 0).toLocaleString()}</span></> : <span style={{ color: '#999' }}>-</span>;
      case 'available': return (s.available || 0) > 0 ? <span style={{ color: (s.available || 0) < 100 ? '#dc2626' : '#00a651', fontWeight: (s.available || 0) < 100 ? 700 : 400 }}>{s.available!.toLocaleString()}</span> : <span style={{ color: '#999' }}>-</span>;
      case 'ship': return <OfficeBadge value={s.fulfillment} />;
      case 'prod': return <OfficeBadge value={s.shipping} />;
      case 'cs': return <OfficeBadge value={s.inquiry} />;
      case 'time': { const t = s.cookie_saved_at || s.last_otp_at; const dt = t ? new Date(t) : null; if (!dt) return <span style={{ color: '#ccc' }}>-</span>; const hrs = (Date.now() - dt.getTime()) / 3600000; const otpTxt = s.last_otp_at ? new Date(s.last_otp_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '없음'; return <span title={`마지막 로그인(쿠키) ${Math.floor(hrs)}시간 전 · 매일 02시 자동 재인증(쿠키워밍). ${hrs > 30 ? '⚠️ 30h 초과 — 로그인 실패 의심' : '정상'}\\n(참고) OTP 마지막 요구: ${otpTxt} — OTP는 11번가가 요구할 때만 떠서 오래돼도 정상`} style={{ fontSize: 12, color: hrs > 30 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>{hrs > 30 ? '⚠️' : '🔑'}{dt.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>; }
      default: return null;
    }
  };

  const footerVal = (col: ColDef) => {
    switch (col.key) {
      case 'seller': return `합계 ${filtered.length}개`;
      case 'cash': return <span style={{ color: '#0369a1' }}>{formatKRW(totals.cash)}</span>;
      case 'point': return <span style={{ color: '#7c3aed' }}>{formatKRW(totals.point)}</span>;
      case 'cpc': return <span style={{ color: '#e67700' }}>{formatKRW(totals.cpc_spend)}</span>;
      case 'sales': return <span style={{ color: '#0369a1' }}>{formatKRW(totals.sales || 0)}</span>;
      case 'cost': return <span style={{ color: '#92400e' }}>{formatKRW(totals.cost || 0)}</span>;
      case 'margin_rate': { const ts = totals.sales || 0; if (ts <= 0) return '-'; const r = ((ts - (totals.cost || 0)) / ts) * 100; return <span style={{ color: r > 0 ? '#0369a1' : '#dc2626' }}>{r.toFixed(1)}%</span>; }
      case 'net_margin_rate': { const ts = totals.sales || 0; if (ts <= 0) return '-'; const r = ((totals.net_profit || 0) / ts) * 100; return <span style={{ color: r >= 0 ? '#15803d' : '#dc2626' }}>{r.toFixed(1)}%</span>; }
      case 'reward': return <span style={{ color: '#15803d' }}>{(totals.reward || 0) > 0 ? '+' + formatKRW(totals.reward) : '-'}</span>;
      case 'net_profit': { const np = totals.net_profit || 0; return <span style={{ color: np >= 0 ? '#15803d' : '#dc2626' }}>{formatKRW(np)}</span>; }
      case 'charge': {
        const c = filtered.reduce((a, s) => a + (s.charge || 0) + ((s as any).settle || 0) + (s.reward || 0), 0);
        const f = filtered.reduce((a, s) => a + (s.server_fee || 0), 0);
        return <><span style={{ color: '#2e7d32' }}>{formatKRW(c)}</span>{f > 0 && <span style={{ fontSize: 11, color: '#dc2626', marginLeft: 3 }}>−{formatKRW(f)}</span>}</>;
      }
      case 'balance': return <><span style={{ color: '#0369a1', fontSize: 13 }}>{formatKRW(filtered.filter(s => s.cost_type !== 'sellercash').reduce((a, s) => a + s.balance, 0))}</span><span style={{ color: '#888', margin: '0 2px', fontSize: 12 }}>/</span><span style={{ color: '#dc2626', fontSize: 13 }}>{formatKRW(Math.abs(filtered.filter(s => s.cost_type === 'sellercash').reduce((a, s) => a + s.balance, 0)))}</span></>;
      case 'products': return totals.products.toLocaleString();
      case 'available': return <span style={{ color: '#00a651' }}>{totals.available.toLocaleString()}</span>;
      default: return '';
    }
  };

  return (
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 6, overflowX: 'auto', position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, padding: '8px 16px', background: '#fffbf0', borderBottom: '1px solid #e0e0e0', fontSize: 15 }}>
        <span>전체 <b>{sellers.length}</b></span>
        <span>총CPC <b style={{ color: '#e67700' }}>{formatKRW(totals.cpc_spend)}</b></span>
        <span>총매출 <b style={{ color: '#0369a1' }}>{formatKRW(totals.sales || 0)}</b></span>
        <span>총순수익 <b style={{ color: (totals.net_profit || 0) >= 0 ? '#15803d' : '#dc2626' }}>{formatKRW(totals.net_profit || 0)}</b></span>
        <span>총충전 <b style={{ color: '#2e7d32' }}>{formatKRW(totals.charge)}</b></span>
        <span
          onClick={() => setOnlyZero(z => !z)}
          title="당일 광고비 0원 계정만 보기 (다시 누르면 해제)"
          style={{
            cursor: 'pointer', fontSize: 13, fontWeight: 700, borderRadius: 4, padding: '1px 9px',
            color: onlyZero ? '#fff' : '#b45309',
            background: onlyZero ? '#d97706' : '#fff7e6',
            border: '1px solid #f0c98a',
          }}>
          ⚠️ 광고비0 {zeroCount}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 13, color: '#888', cursor: 'pointer' }} onClick={() => setHideEmpty(h => !h)}>
          {hideEmpty ? `${filtered.length}개만` : '빈계정숨기기'}
        </span>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontVariantNumeric: 'tabular-nums', tableLayout: 'fixed' }}>
        <colgroup>{INIT_COLS.map((_, i) => <col key={i} style={{ width: widths[i] }} />)}</colgroup>
        <thead>
          <tr>
            {INIT_COLS.map((col, ci) => (
              <th key={col.key} style={{ fontSize: 15, fontWeight: 700, color: '#111', borderBottom: '2px solid #ddd', padding: '5px 6px', whiteSpace: 'nowrap', textAlign: col.align as any, position: 'relative', ...stickyTh(ci) }}>
                <span style={{ cursor: col.sortKey ? 'pointer' : 'default' }} onClick={() => col.sortKey && handleSort(col.sortKey)}>
                  {col.label}{col.sortKey ? arrow(col.sortKey) : ''}
                </span>
                <span
                  title="클릭: 고정/해제"
                  style={{ fontSize: 11, marginLeft: 2, cursor: 'pointer', opacity: pinned.has(ci) ? 1 : 0.3 }}
                  onClick={e => { e.stopPropagation(); togglePin(ci); }}>
                  📌
                </span>
                <div
                  style={{ position: 'absolute', right: -3, top: 0, bottom: 0, width: 7, cursor: 'col-resize', zIndex: 20 }}
                  onMouseDown={e => onResizeStart(e, ci)}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* 합계 행 — 맨 위 */}
          <tr style={{ background: '#eef3ff', fontWeight: 700, fontSize: 15, borderBottom: '2px solid #cdd6f0' }}>
            {INIT_COLS.map((col, ci) => (
              <td key={col.key} style={{ padding: '6px 6px', textAlign: col.align as any, whiteSpace: 'nowrap', ...stickyFt(ci) }}>{footerVal(col)}</td>
            ))}
          </tr>
          {filtered.map((s, i) => {
            const isSelected = selectedSeller === s.seller_id;
            const isBlocked = blockedIds?.has(s.seller_id);
            const totalMoney = (s.cash || 0) + (s.point || 0);
            const isLow = totalMoney > 0 && totalMoney < 50000;
            const isCpcZero = (s.cpc_spend || 0) === 0;
            const bg = isSelected ? '#fff3e0' : isBlocked ? '#fef2f2' : isLow ? '#fff0f0' : isCpcZero ? '#fffbe6' : i % 2 === 0 ? '#fff' : '#fafafa';
            return (
              <tr key={s.seller_id} onClick={() => onSelectSeller(isSelected ? null : s.seller_id)}
                style={{ background: bg, cursor: 'pointer' }}
                onMouseEnter={e => { e.currentTarget.style.background = '#fff8f0'; }}
                onMouseLeave={e => { e.currentTarget.style.background = bg; }}>
                {INIT_COLS.map((col, ci) => (
                  <td key={col.key} style={{ fontSize: 15, padding: '4px 6px', borderBottom: '1px solid #eee', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', textAlign: col.align as any, ...stickyTd(ci, bg) }}>
                    {renderCell(s, col, i)}
                  </td>
                ))}
              </tr>
            );
          })}
          {/* 기타(미매칭) — 5월 이전 등 크롤계정에 매칭 안 된 11번가 매출 */}
          {unmatched && unmatched.sales > 0 && (
            <tr style={{ background: '#fff7e6' }}
              title={`매칭 안 된 쇼핑몰: ${unmatched.shops.map(s => `${s.name}(${formatKRW(s.sales)})`).join(', ')}`}>
              {INIT_COLS.map((col, ci) => {
                let content: any = '';
                if (col.key === 'seller') content = <span style={{ fontWeight: 700, color: '#b45309' }}>🗂 기타·미매칭 <span style={{ fontSize: 12, fontWeight: 400, color: '#92400e' }}>({unmatched.shops.length}개 쇼핑몰)</span></span>;
                else if (col.key === 'sales') content = <span style={{ color: '#0369a1', fontWeight: 600 }}>{formatKRW(unmatched.sales)}</span>;
                else if (col.key === 'cost') content = <span style={{ color: '#92400e' }}>{formatKRW(unmatched.cost)}</span>;
                else if (col.key === 'net_profit') content = <span style={{ color: unmatched.net_profit >= 0 ? '#15803d' : '#dc2626', fontWeight: 700 }}>{formatKRW(unmatched.net_profit)}</span>;
                return (
                  <td key={col.key} style={{ fontSize: 15, padding: '4px 6px', borderBottom: '1px solid #eee', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', textAlign: col.align as any, ...stickyTd(ci, '#fff7e6') }}>
                    {content}
                  </td>
                );
              })}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
