import { useEffect, useState } from 'react';
import { Inbox, Send, History, Smartphone, BookOpen, RefreshCw, Plus, Circle, Bot, Bell } from 'lucide-react';
import {
  getLatestSmsList,
  getOutboxHistory,
  getSmsDevices,
} from '../../api/sms';
import SmsSendModal from '../../components/SmsSendModal';
import PhoneSetupGuide from '../../components/PhoneSetupGuide';
import TelegramSetupGuide from '../../components/TelegramSetupGuide';
import NotificationPermissionGuide from '../../components/NotificationPermissionGuide';

type Tab = 'inbox' | 'send' | 'history' | 'devices' | 'guide';

const tabs: { id: Tab; label: string; icon: any }[] = [
  { id: 'inbox', label: '수신함', icon: Inbox },
  { id: 'send', label: '발송', icon: Send },
  { id: 'history', label: '발송 내역', icon: History },
  { id: 'devices', label: '디바이스', icon: Smartphone },
  { id: 'guide', label: '셋업 가이드', icon: BookOpen },
];

function maskPhone(p: string) {
  const d = (p || '').replace(/\D/g, '');
  if (d.length === 11) return `${d.slice(0, 3)}-${d.slice(3, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `${d.slice(0, 3)}-${d.slice(3, 6)}-${d.slice(6)}`;
  return p;
}

function formatDate(s?: string | null) {
  if (!s) return '-';
  const d = new Date(s);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

export default function SmsManagePage() {
  const [tab, setTab] = useState<Tab>('inbox');
  const [inbox, setInbox] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  const [showSendModal, setShowSendModal] = useState(false);
  const [showTelegramGuide, setShowTelegramGuide] = useState(false);
  const [showNotifGuide, setShowNotifGuide] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const [a, b, c] = await Promise.all([
        getLatestSmsList({ limit: 100 }),
        getOutboxHistory({ limit: 100 }),
        getSmsDevices(),
      ]);
      setInbox(a || []);
      setHistory(b || []);
      setDevices(c || []);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  const onlineCount = devices.filter(d => d.is_online).length;
  const pendingCount = history.filter(h => h.status === 'pending').length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">문자 관리</h1>
          <p className="text-sm text-gray-500 mt-1">smsApp 게이트웨이를 통한 SMS/MMS 송수신</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded"
            title="새로고침"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => setShowNotifGuide(true)}
            className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded text-sm font-semibold flex items-center gap-1.5"
            title="폰 알림 켜는 방법 (도움말)"
          >
            <Bell size={14} /> 알림 켜는법
          </button>
          <button
            onClick={() => setShowTelegramGuide(true)}
            className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-semibold flex items-center gap-1.5"
            title="텔레그램 봇 설정 (도움말)"
          >
            <Bot size={14} /> 텔레그램 설정
          </button>
          <button
            onClick={() => setShowSendModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-semibold flex items-center gap-1.5"
          >
            <Plus size={14} /> 문자 발송
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="수신 (총)" value={inbox.length} color="blue" icon={Inbox} />
        <StatCard label="발송 (총)" value={history.length} color="green" icon={Send} />
        <StatCard label="발송 대기" value={pendingCount} color="orange" icon={History} />
        <StatCard label="온라인 디바이스" value={`${onlineCount}/${devices.length}`} color="purple" icon={Smartphone} />
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="flex border-b">
          {tabs.map(t => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? 'border-blue-600 text-blue-600 bg-blue-50/30'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                <Icon size={16} />
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="p-5">
          {tab === 'inbox' && <InboxTab items={inbox} />}
          {tab === 'send' && <SendTab onOpen={() => setShowSendModal(true)} />}
          {tab === 'history' && <HistoryTab items={history} />}
          {tab === 'devices' && <DevicesTab items={devices} />}
          {tab === 'guide' && <PhoneSetupGuide />}
        </div>
      </div>

      <SmsSendModal open={showSendModal} onClose={() => setShowSendModal(false)} onSent={refresh} />
      <TelegramSetupGuide open={showTelegramGuide} onClose={() => setShowTelegramGuide(false)} />
      <NotificationPermissionGuide open={showNotifGuide} onClose={() => setShowNotifGuide(false)} />
    </div>
  );
}

function StatCard({ label, value, color, icon: Icon }: any) {
  const colors: any = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
        <Icon size={20} />
      </div>
      <div>
        <div className="text-xs text-gray-500">{label}</div>
        <div className="text-xl font-bold text-gray-800">{value}</div>
      </div>
    </div>
  );
}

function InboxTab({ items }: { items: any[] }) {
  if (items.length === 0) {
    return <div className="text-center text-gray-400 py-12 text-sm">수신된 문자가 없습니다</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500">
          <tr>
            <th className="px-3 py-2 text-left">수신 시각</th>
            <th className="px-3 py-2 text-left">발신자</th>
            <th className="px-3 py-2 text-left">내 번호</th>
            <th className="px-3 py-2 text-left">메시지</th>
          </tr>
        </thead>
        <tbody>
          {items.map((m: any) => (
            <tr key={m.id} className="border-t hover:bg-gray-50">
              <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{formatDate(m.received_at)}</td>
              <td className="px-3 py-2 font-mono text-xs text-blue-700">{maskPhone(m.csphone) || '-'}</td>
              <td className="px-3 py-2 font-mono text-xs">{maskPhone(m.phone)}</td>
              <td className="px-3 py-2 text-gray-800">{m.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SendTab({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="text-center py-12">
      <Send size={48} className="mx-auto text-blue-500 mb-3" />
      <h3 className="font-semibold text-gray-800 mb-2">문자 발송하기</h3>
      <p className="text-sm text-gray-500 mb-4">
        수신자 번호와 메시지를 입력하여 등록된 smsApp 디바이스에서 SMS/LMS를 발송합니다.
      </p>
      <button
        onClick={onOpen}
        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded text-sm font-semibold inline-flex items-center gap-2"
      >
        <Plus size={16} /> 발송 창 열기
      </button>
    </div>
  );
}

function HistoryTab({ items }: { items: any[] }) {
  if (items.length === 0) {
    return <div className="text-center text-gray-400 py-12 text-sm">발송 내역이 없습니다</div>;
  }
  const badgeColor = (s: string) =>
    s === 'sent' ? 'bg-green-100 text-green-700' :
    s === 'failed' ? 'bg-red-100 text-red-700' :
    'bg-amber-100 text-amber-700';
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500">
          <tr>
            <th className="px-3 py-2 text-left">요청 시각</th>
            <th className="px-3 py-2 text-left">발송 시각</th>
            <th className="px-3 py-2 text-left">받는 사람</th>
            <th className="px-3 py-2 text-left">발신 디바이스</th>
            <th className="px-3 py-2 text-left">메시지</th>
            <th className="px-3 py-2 text-center">상태</th>
          </tr>
        </thead>
        <tbody>
          {items.map((o: any) => (
            <tr key={o.id} className="border-t hover:bg-gray-50">
              <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{formatDate(o.created_at)}</td>
              <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{formatDate(o.sent_at)}</td>
              <td className="px-3 py-2 font-mono text-xs">{maskPhone(o.phone_number)}</td>
              <td className="px-3 py-2 font-mono text-xs text-gray-500">{maskPhone(o.sender_phone) || '-'}</td>
              <td className="px-3 py-2 text-gray-800 max-w-xs truncate">{o.message}</td>
              <td className="px-3 py-2 text-center">
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${badgeColor(o.status)}`}>
                  {o.status}
                </span>
                {o.error_message && (
                  <div className="text-[10px] text-red-500 mt-0.5" title={o.error_message}>
                    {o.error_message.slice(0, 30)}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DevicesTab({ items }: { items: any[] }) {
  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <Smartphone size={48} className="mx-auto text-gray-300 mb-3" />
        <p className="text-sm text-gray-500 mb-1">등록된 디바이스가 없습니다</p>
        <p className="text-xs text-gray-400">"셋업 가이드" 탭을 참고해 핸드폰에 smsApp을 설치해주세요.</p>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {items.map((d: any) => (
        <div key={d.id} className="border rounded-lg p-4 hover:shadow-sm transition-shadow">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${d.is_online ? 'bg-green-100' : 'bg-gray-100'}`}>
                <Smartphone size={22} className={d.is_online ? 'text-green-600' : 'text-gray-400'} />
              </div>
              <div>
                <div className="font-mono font-bold text-gray-800">{maskPhone(d.phone_number)}</div>
                <div className="text-xs text-gray-500">v{d.app_version || '?'}</div>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <Circle size={8} className={d.is_online ? 'text-green-500 fill-green-500' : 'text-gray-300 fill-gray-300'} />
              <span className={`text-xs font-semibold ${d.is_online ? 'text-green-600' : 'text-gray-400'}`}>
                {d.is_online ? '온라인' : '오프라인'}
              </span>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            마지막 응답: {formatDate(d.last_seen_at)}
          </div>
        </div>
      ))}
    </div>
  );
}
