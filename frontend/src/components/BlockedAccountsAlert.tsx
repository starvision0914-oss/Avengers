import { useEffect, useState } from 'react';
import { AlertTriangle, ExternalLink, X, RefreshCw, Unlock } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';
import { useTheme } from '../hooks/useTheme';

interface BlockedAccount {
  id: number;
  platform: string;
  login_id: string;
  fail_count: number;
  crawling_status: string;
}

const SITE_URLS: Record<string, { label: string; login: string; color: string }> = {
  gmarket: {
    label: '지마켓',
    login: 'https://signin.esmplus.com/login',
    color: '#6cc24a',
  },
  '11st': {
    label: '11번가',
    login: 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall',
    color: '#ff5a2e',
  },
};

export default function BlockedAccountsAlert() {
  const { dark } = useTheme();
  const [blocked, setBlocked] = useState<BlockedAccount[]>([]);
  const [dismissed, setDismissed] = useState(false);
  const [unblocking, setUnblocking] = useState<number | null>(null);

  const load = () => {
    api.get('/cpc/crawler/accounts/', { params: { page_size: 200 } })
      .then(r => {
        const data = r.data?.results || r.data || [];
        const list = (Array.isArray(data) ? data : []).filter(
          (a: any) => a.fail_count >= 30 || a.crawling_status === '차단됨'
        );
        setBlocked(list);
      })
      .catch(() => {});
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);

  const handleUnblock = async (a: BlockedAccount) => {
    setUnblocking(a.id);
    try {
      await api.patch(`/cpc/crawler/accounts/${a.id}/`, {
        fail_count: 0,
        crawling_status: '정상',
      });
      toast.success(`${a.login_id} 차단 해제 완료`);
      load();
    } catch {
      toast.error('차단 해제 실패');
    } finally {
      setUnblocking(null);
    }
  };

  if (blocked.length === 0 || dismissed) return null;

  const bg = dark ? 'bg-red-950/80 border-red-800' : 'bg-red-50 border-red-300';
  const text = dark ? 'text-red-200' : 'text-red-900';
  const subtext = dark ? 'text-red-300' : 'text-red-700';

  return (
    <div className={`rounded-xl border-2 ${bg} p-4 mb-4 animate-pulse`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle size={20} className="text-red-500" />
          <h3 className={`font-bold ${text}`}>
            차단된 계정 {blocked.length}개 발견
          </h3>
        </div>
        <button onClick={() => setDismissed(true)} className={`${subtext} hover:text-red-500`}>
          <X size={16} />
        </button>
      </div>

      <p className={`text-xs ${subtext} mb-3`}>
        로그인 30회 이상 실패하여 차단된 계정입니다. 해당 사이트에서 비밀번호 변경 또는 보안 해제 후 [차단 해제] 버튼을 눌러주세요.
      </p>

      <div className="space-y-2">
        {blocked.map(a => {
          const site = SITE_URLS[a.platform];
          return (
            <div key={a.id} className={`flex items-center justify-between p-2.5 rounded-lg ${dark ? 'bg-[#1a1b23]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold text-white" style={{ backgroundColor: site?.color || '#888' }}>
                  {site?.label || a.platform}
                </span>
                <span className={`font-mono font-bold text-sm ${dark ? 'text-white' : 'text-gray-900'}`}>{a.login_id}</span>
                <span className="text-[10px] text-red-500">fail={a.fail_count}</span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={site?.login || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded text-[11px] font-semibold bg-blue-600 text-white hover:bg-blue-700"
                >
                  <ExternalLink size={12} /> 사이트 이동
                </a>
                <button
                  onClick={() => handleUnblock(a)}
                  disabled={unblocking === a.id}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded text-[11px] font-semibold bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-400"
                >
                  {unblocking === a.id ? <RefreshCw size={12} className="animate-spin" /> : <Unlock size={12} />}
                  차단 해제
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
