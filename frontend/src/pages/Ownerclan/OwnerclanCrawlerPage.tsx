import { useState, useEffect, useCallback } from 'react';
import { PlayCircle, Package, Wallet, Truck, CalendarClock, Tag } from 'lucide-react';
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

  return (
    <div className="p-5 max-w-[900px] mx-auto space-y-4">
      <div className="bg-white border border-[#e0e0e0] rounded-lg p-5">
        <div className="flex items-center gap-2 mb-2">
          <Package size={20} className="text-[#2563eb]" />
          <h1 className="text-[18px] font-bold text-[#222]">오너클랜 상품 자동수집</h1>
        </div>
        <p className="text-[13px] text-[#666] leading-relaxed mb-4">
          오너클랜 정식 API로 전체 상품을 조회해, <b>예비상품에 아직 없는 새 상품만</b> 자동으로 추가합니다.
          이미 등록된 상품은 건드리지 않습니다.
        </p>
        <button onClick={handleStart} disabled={busy}
          className="flex items-center gap-1.5 px-4 py-2 text-[14px] font-semibold text-white rounded-lg disabled:opacity-50"
          style={{ background: busy ? '#aaa' : '#2563eb' }}>
          <PlayCircle size={15} className={busy ? 'animate-spin' : ''} />
          {busy ? '수집 중…' : '새 상품 가져오기'}
        </button>
        {msg && <div className="mt-2 text-[13px] text-[#2563eb] font-semibold">{msg}</div>}
      </div>

      {accounts.length > 0 && (
        <div className="bg-white border border-[#e0e0e0] rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[13px] font-bold text-[#333]">계정 정보 (마이페이지)</div>
            <button onClick={handleInfoRefresh}
              className="px-3 py-1 text-[12px] font-semibold text-white rounded bg-[#16a34a] hover:bg-[#15803d]">
              계정정보 새로고침
            </button>
          </div>
          {infoMsg && <div className="text-[12px] text-[#16a34a] font-semibold mb-2">{infoMsg}</div>}
          {accounts.map(a => (
            <div key={a.login_id} className="border border-[#eef0f3] rounded-lg p-3 mb-2">
              <div className="text-[13px] font-bold text-[#222] mb-2">
                {a.login_id}
                <span className="text-[11px] text-[#999] font-normal ml-2">
                  상품수집: {a.last_synced_at ? new Date(a.last_synced_at).toLocaleString('ko-KR') : '없음'} (신규{a.last_new_count}건)
                  {' · '}계정정보: {a.info_synced_at ? new Date(a.info_synced_at).toLocaleString('ko-KR') : '없음'}
                </span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[12.5px]">
                <div className="flex items-start gap-1.5">
                  <Wallet size={14} className="text-[#d97706] mt-0.5" />
                  <div>
                    <div className="text-[#888]">오너클랜머니</div>
                    <div className="font-bold text-[#222]">{a.balance || '-'}</div>
                  </div>
                </div>
                <div className="flex items-start gap-1.5">
                  <Truck size={14} className="text-[#2563eb] mt-0.5" />
                  <div>
                    <div className="text-[#888]">주문/배송현황</div>
                    <div className="text-[#333]">
                      {Object.entries(a.order_stats || {}).map(([k, v]) => (
                        <span key={k} className="mr-2">{k} <b>{v}</b></span>
                      ))}
                      {(!a.order_stats || Object.keys(a.order_stats).length === 0) && '-'}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-1.5">
                  <CalendarClock size={14} className="text-[#7c3aed] mt-0.5" />
                  <div>
                    <div className="text-[#888]">구독서비스</div>
                    <div className="text-[#333]">
                      {(a.subscription_info?.raw || []).map((l, i) => <div key={i}>{l}</div>)}
                      {(!a.subscription_info?.raw || a.subscription_info.raw.length === 0) && '-'}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-1.5">
                  <Tag size={14} className="text-[#dc2626] mt-0.5" />
                  <div>
                    <div className="text-[#888]">최저가 선점권</div>
                    <div className="text-[#333]">
                      {Object.entries(a.lowest_price_quota || {}).map(([k, v]) => (
                        <div key={k}>{k}: <b>{v}</b>개</div>
                      ))}
                      {(!a.lowest_price_quota || Object.keys(a.lowest_price_quota).length === 0) && '-'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white border border-[#e0e0e0] rounded-lg p-5">
        <div className="text-[13px] font-bold text-[#333] mb-2">진행 로그</div>
        <pre className="text-[11.5px] text-[#444] bg-[#f8fafc] rounded p-3 overflow-auto max-h-[400px] whitespace-pre-wrap">
          {log || '아직 실행 기록이 없습니다.'}
        </pre>
      </div>
    </div>
  );
}
