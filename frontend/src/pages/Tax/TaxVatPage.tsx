import { Fragment, useEffect, useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Download, PlayCircle } from 'lucide-react';
import {
  getTaxVatSummary, getTaxVatCrawlStatus, startTaxVatCrawl,
  type TaxVatSummary, type TaxVatAccount, type TaxVatCrawlStatus,
} from '../../api/tax';
import { formatKRW } from '../../utils/format';

const MONTHS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
const PLATFORMS = [
  { key: 'all', label: '통합' },
  { key: '11st', label: '11번가' },
  { key: 'gmarket', label: '지마켓' },
  { key: 'auction', label: '옥션' },
  { key: 'smartstore', label: '스마트스토어' },
  { key: 'coupang', label: '쿠팡' },
  { key: 'lotteon', label: '롯데온' },
] as const;

type PlatformKey = (typeof PLATFORMS)[number]['key'];

export default function TaxVatPage() {
  const [year, setYear] = useState(2026);
  const [platform, setPlatform] = useState<PlatformKey>('all');
  const [data, setData] = useState<TaxVatSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [crawlStatus, setCrawlStatus] = useState<TaxVatCrawlStatus>({});
  const [crawlMsg, setCrawlMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await getTaxVatSummary(year, platform)); } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [year, platform]);

  const loadCrawlStatus = useCallback(async () => {
    try { setCrawlStatus(await getTaxVatCrawlStatus()); } catch { /* noop */ }
  }, []);

  const toggleExpand = (group: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group); else next.add(group);
      return next;
    });
  };

  useEffect(() => {
    load();
    loadCrawlStatus();
    const t = setInterval(() => { load(); loadCrawlStatus(); }, 30000);
    return () => clearInterval(t);
  }, [load, loadCrawlStatus]);

  const isBusy = (p: string) => p === 'all'
    ? Object.values(crawlStatus).some(s => s.busy)
    : !!crawlStatus[p]?.busy;

  const handleCrawl = async () => {
    setCrawlMsg('');
    try {
      const r = await startTaxVatCrawl(platform, year);
      if (r.status === 'busy') setCrawlMsg(r.error || '이미 실행 중입니다.');
      else setCrawlMsg(`크롤링 시작됨 (${(r.platforms || [platform]).map(p => PLATFORMS.find(x => x.key === p)?.label || p).join(', ')})`);
    } catch (e: any) {
      setCrawlMsg(e?.response?.data?.error || '크롤링 시작 실패');
    }
    loadCrawlStatus();
  };

  const handleExportExcel = () => {
    if (!data || data.accounts.length === 0) { alert('다운로드할 데이터가 없습니다.'); return; }
    const head = ['No', '그룹', '플랫폼', '로그인ID', '셀러명', ...months.map(m => `${m}월`), '합계'];
    const rows: (string | number)[][] = [];
    data.accounts.forEach((a, i) => {
      rows.push([i + 1, a.group, '', '', `(합계 ${a.member_count}개)`, ...months.map(m => a.months[m] ?? 0), a.total]);
      a.members.forEach(m => {
        rows.push(['', '', m.platform_label, m.login_id, m.seller_name, ...months.map(mo => m.months[mo] ?? 0), m.total]);
      });
    });
    rows.push(['', `합계 (${data.accounts.length}개)`, '', '', '', ...months.map(m => data.monthly_totals[m] || 0), data.grand_total]);
    const csv = '﻿' + [head, ...rows]
      .map(row => row.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const label = PLATFORMS.find(p => p.key === platform)?.label || platform;
    a.href = url; a.download = `부가세현황_${label}_${year}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const months = data ? MONTHS.filter(m => data.monthly_totals[m] !== undefined) : [];
  const pct = data && data.progress.target ? Math.round(data.progress.collected / data.progress.target * 100) : 0;

  return (
    <div className="min-h-screen bg-[#f5f5f5] p-5">
      <div className="max-w-[1500px] mx-auto">

        {/* 헤더 */}
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <h1 className="text-[20px] font-bold text-[#222]">부가세(VAT) 현황</h1>

          {/* 플랫폼 탭 */}
          <div className="flex border border-[#ddd] rounded overflow-hidden text-[12px]">
            {PLATFORMS.map(p => (
              <button
                key={p.key}
                onClick={() => { setPlatform(p.key); setData(null); setExpanded(new Set()); }}
                className={`px-4 py-1.5 font-semibold transition-colors flex items-center gap-1 ${
                  platform === p.key
                    ? 'bg-[#e67700] text-white'
                    : 'bg-white text-[#555] hover:bg-[#f5f5f5]'
                }`}
              >
                {p.label}
                {isBusy(p.key) && <span className="w-1.5 h-1.5 rounded-full bg-[#0284c7] animate-pulse" title="크롤링 중" />}
              </button>
            ))}
          </div>

          <select value={year} onChange={e => { setYear(Number(e.target.value)); setData(null); setExpanded(new Set()); }}
            className="border border-[#ccc] rounded px-2 py-1 text-[12px]">
            {[2026, 2025, 2024].map(y => <option key={y} value={y}>{y}년</option>)}
          </select>
          <button onClick={load} className="px-3 py-1 text-[12px] font-semibold bg-[#444] text-white rounded">새로고침</button>
          <button onClick={handleCrawl} disabled={isBusy(platform)}
            className="flex items-center gap-1 px-3 py-1 text-[12px] font-semibold text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: isBusy(platform) ? '#aaa' : '#0284c7' }}>
            <PlayCircle size={13} className={isBusy(platform) ? 'animate-spin' : ''} />
            {isBusy(platform) ? '크롤링 중…' : '크롤링'}
          </button>
          <button onClick={handleExportExcel}
            className="flex items-center gap-1 px-3 py-1 text-[12px] font-semibold bg-[#15803d] text-white rounded">
            <Download size={13} /> 엑셀 다운로드
          </button>
          {loading && <span className="text-[12px] text-[#999] animate-pulse">불러오는 중…</span>}
          {crawlMsg && <span className="text-[12px] text-[#0284c7] font-semibold">{crawlMsg}</span>}
        </div>

        {/* 수집 진행률 */}
        {data && (
          <div className="bg-white border border-[#e0e0e0] rounded p-4 mb-4">
            <div className="flex items-center justify-between mb-2 text-[12px]">
              <span className="font-bold text-[#333]">수집 진행률</span>
              <span className="text-[#666]">
                {data.progress.collected} / {data.progress.target} 계정 ({pct}%)
                {data.progress.last_collected_at && (
                  <span className="ml-3 text-[#999]">
                    최근 수집 {new Date(data.progress.last_collected_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </span>
            </div>
            <div className="w-full h-3 bg-[#eee] rounded overflow-hidden">
              <div className="h-full bg-[#00a651]" style={{ width: `${pct}%` }} />
            </div>
            <div className="flex gap-6 mt-3 text-[12px]">
              <span>총 {platform === 'gmarket' || platform === 'auction' || platform === 'coupang' || platform === 'lotteon' ? '총매출' : '과세매출'} <b className="text-[#0369a1]">{formatKRW(data.grand_total)}</b></span>
              <span>매출세액(÷11) <b className="text-[#dc2626]">{formatKRW(data.vat_payable)}</b></span>
              <span>수집 계정 <b>{data.accounts.length}</b></span>
            </div>
          </div>
        )}

        {/* 계정별 월별 테이블 */}
        <div className="bg-white border border-[#e0e0e0] rounded overflow-x-auto">
          <table className="w-full text-[12px]" style={{ borderCollapse: 'collapse', fontVariantNumeric: 'tabular-nums' }}>
            <thead>
              <tr style={{ background: '#fffbf0', borderBottom: '2px solid #ddd' }}>
                <th className="px-3 py-2 text-center" style={{ width: 44 }}>No</th>
                <th className="px-3 py-2 text-left">셀러</th>
                {months.map(m => <th key={m} className="px-3 py-2 text-right">{m}월</th>)}
                <th className="px-3 py-2 text-right font-bold">합계</th>
              </tr>
            </thead>
            <tbody>
              {data?.accounts.map((a, i) => {
                const isOpen = expanded.has(a.group);
                return (
                <Fragment key={a.group}>
                  <tr onClick={() => toggleExpand(a.group)}
                      style={{ background: isOpen ? '#fff8ec' : i % 2 ? '#fafafa' : '#fff', borderBottom: '1px solid #eee', cursor: 'pointer' }}>
                    <td className="px-3 py-1.5 text-center text-[#888]">{i + 1}</td>
                    <td className="px-3 py-1.5">
                      <span className="inline-flex items-center gap-1">
                        {isOpen ? <ChevronDown size={12} className="text-[#999]" /> : <ChevronRight size={12} className="text-[#999]" />}
                        <b>{a.group}</b>
                      </span>
                      <span className="text-[11px] text-[#888] ml-1">({a.rep_login_id})</span>
                      {a.member_count > 1 && <span className="text-[11px] text-[#aaa] ml-1">외 {a.member_count - 1}개</span>}
                    </td>
                    {months.map(m => {
                      const v = a.months[m] ?? 0;
                      return (
                        <td key={m} className="px-3 py-1.5 text-right"
                            style={{ color: v < 0 ? '#dc2626' : v > 0 ? '#333' : '#bbb' }}>
                          {v ? formatKRW(v) : '-'}
                        </td>
                      );
                    })}
                    <td className="px-3 py-1.5 text-right font-bold text-[#0369a1]">{formatKRW(a.total)}</td>
                  </tr>
                  {isOpen && <TaxGroupDetail account={a} months={months} />}
                </Fragment>
                );
              })}
              {(!data || data.accounts.length === 0) && (
                <tr>
                  <td colSpan={months.length + 3} className="px-3 py-8 text-center text-[#999]">
                    {loading ? '수집 중...' : platform === 'gmarket'
                      ? '수집된 데이터가 없습니다. crawl_gmarket_vat 를 먼저 실행해 주세요.'
                      : platform === 'auction'
                      ? '수집된 데이터가 없습니다. "지마켓" 크롤링 버튼을 누르면 옥션도 함께 수집됩니다.'
                      : platform === 'smartstore'
                      ? '수집된 데이터가 없습니다. crawl_smartstore_vat 를 먼저 실행해 주세요.'
                      : platform === 'coupang'
                      ? '수집된 데이터가 없습니다. crawl_coupang_vat 를 먼저 실행해 주세요.'
                      : platform === 'lotteon'
                      ? '수집된 데이터가 없습니다. crawl_lotteon_vat 를 먼저 실행해 주세요.'
                      : platform === 'all'
                      ? '수집된 데이터가 없습니다. 각 플랫폼 탭에서 먼저 수집을 진행해 주세요.'
                      : '수집된 데이터가 없습니다 (크롤 진행 중일 수 있습니다)'}
                  </td>
                </tr>
              )}
            </tbody>
            {data && data.accounts.length > 0 && (
              <tfoot>
                <tr style={{ background: '#eef3ff', fontWeight: 700, borderTop: '2px solid #ccd' }}>
                  <td className="px-3 py-2 text-center" colSpan={2}>합계 ({data.accounts.length}개)</td>
                  {months.map(m => (
                    <td key={m} className="px-3 py-2 text-right">{formatKRW(data.monthly_totals[m] || 0)}</td>
                  ))}
                  <td className="px-3 py-2 text-right text-[#0369a1]">{formatKRW(data.grand_total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>

        {expanded.size > 0 && (
          <p className="text-[11px] text-[#aaa] mt-1">※ 셀러 행을 클릭하면 접힙니다. 통합 뷰에서는 플랫폼별 소계와 계정별 세부내역을 함께 보여줍니다.</p>
        )}

        <p className="text-[12px] text-[#999] mt-2">
          {platform === 'all'
            ? '※ 11번가·지마켓·옥션·스마트스토어·쿠팡·롯데온 전체를 셀러명 앞 3글자 기준으로 교차 매칭해 합산한 통합 뷰입니다 (예: "스타드림"+"스타드림딜" → "스타드"). 30초마다 자동 갱신.'
            : platform === '11st'
            ? '※ 11번가 셀러오피스 부가세신고내역(공식 과세매출) 기준. 30초마다 자동 갱신.'
            : platform === 'gmarket'
            ? '※ 지마켓 ESM Plus 부가세자료(총매출) 기준. crawl_gmarket_vat 명령으로 수집. 30초마다 자동 갱신.'
            : platform === 'auction'
            ? '※ ESM Plus 부가세자료 중 옥션 탭(총매출) 기준. 지마켓 크롤 안에서 탭 전환으로 함께 수집됨(별도 명령 없음). 30초마다 자동 갱신.'
            : platform === 'coupang'
            ? '※ 쿠팡 Wing 부가세신고 매출자료(판매자윙+로켓그로스 합산) 기준. crawl_coupang_vat 명령으로 수집. 30초마다 자동 갱신.'
            : platform === 'lotteon'
            ? '※ 롯데온 판매자센터 정산관리 > 부가세신고자료조회(총매출) 기준. 과세/면세 구분 없음. crawl_lotteon_vat 명령으로 수집. 30초마다 자동 갱신.'
            : '※ 스마트스토어센터 정산관리 > 부가세신고내역(과세매출) 기준. crawl_smartstore_vat 명령으로 수집. 30초마다 자동 갱신.'}
        </p>
      </div>
    </div>
  );
}

// ── 셀러 그룹 세부내역 (클릭 시 펼침) — 플랫폼별 소계 + 계정별 월별 내역 ──
function TaxGroupDetail({ account, months }: { account: TaxVatAccount; months: string[] }) {
  const byPlatform = new Map<string, { label: string; total: number; count: number }>();
  for (const m of account.members) {
    const cur = byPlatform.get(m.platform) || { label: m.platform_label, total: 0, count: 0 };
    cur.total += m.total;
    cur.count += 1;
    byPlatform.set(m.platform, cur);
  }
  const platformRows = Array.from(byPlatform.values()).sort((a, b) => b.total - a.total);
  const showPlatformSubtotal = platformRows.length > 1;

  return (
    <tr>
      <td colSpan={months.length + 3} className="p-0" style={{ background: '#fffdf7', borderBottom: '2px solid #f0d9a8' }}>
        <div className="px-3 py-2">
          {/* 플랫폼별 소계 — 통합 뷰처럼 여러 플랫폼이 섞인 경우에만 표시 */}
          {showPlatformSubtotal && (
            <div className="flex flex-wrap gap-2 mb-2">
              {platformRows.map(p => (
                <span key={p.label} className="px-2 py-1 bg-white border border-[#e0d0a8] rounded text-[11px]">
                  <b className="text-[#7c4a03]">{p.label}</b> {formatKRW(p.total)}원
                  <span className="text-[#aaa] ml-1">({p.count}개)</span>
                </span>
              ))}
            </div>
          )}

          {/* 계정별 세부내역 테이블 — 상단 그룹행과 동일한 월 컬럼으로 정렬해 합계 눈으로 검증 가능 */}
          <table className="w-full text-[11px]" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr className="text-[#999]">
                <th className="px-2 py-1 text-left" style={{ width: 44 }}></th>
                <th className="px-2 py-1 text-left font-semibold">계정</th>
                {months.map(m => <th key={m} className="px-2 py-1 text-right font-semibold">{m}월</th>)}
                <th className="px-2 py-1 text-right font-semibold">합계</th>
              </tr>
            </thead>
            <tbody>
              {account.members.map(m => (
                <tr key={`${m.platform}-${m.login_id}`} className="border-t border-[#f0e6cc]">
                  <td className="px-2 py-1"></td>
                  <td className="px-2 py-1">
                    <span className="px-1.5 py-0.5 bg-[#f5ead0] text-[#7c4a03] rounded text-[10px] font-semibold mr-1">{m.platform_label}</span>
                    <span className="text-[#555]">{m.seller_name || m.login_id}</span>
                    <span className="text-[10px] text-[#aaa] ml-1">({m.login_id})</span>
                  </td>
                  {months.map(mo => {
                    const v = m.months[mo] ?? 0;
                    return (
                      <td key={mo} className="px-2 py-1 text-right" style={{ color: v < 0 ? '#dc2626' : v > 0 ? '#333' : '#ccc' }}>
                        {v ? formatKRW(v) : '-'}
                      </td>
                    );
                  })}
                  <td className="px-2 py-1 text-right font-bold text-[#0369a1]">{formatKRW(m.total)}</td>
                </tr>
              ))}
              <tr className="border-t border-[#e0d0a8]" style={{ fontWeight: 700 }}>
                <td className="px-2 py-1"></td>
                <td className="px-2 py-1 text-[#555]">소계 ({account.members.length}개)</td>
                {months.map(mo => (
                  <td key={mo} className="px-2 py-1 text-right">{formatKRW(account.months[mo] ?? 0)}</td>
                ))}
                <td className="px-2 py-1 text-right text-[#0369a1]">{formatKRW(account.total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </td>
    </tr>
  );
}
