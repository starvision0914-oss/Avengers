import { useEffect, useState, useRef } from 'react';
import { getLatestSms, getSmsPhones, addSmsPhone, removeSmsPhone } from '../api/crawler';
import { MessageSquare, X, Settings, Phone, Plus, Trash2, Send, Copy, Reply } from 'lucide-react';
import SmsSendModal from './SmsSendModal';

function cleanPhone(p?: string) {
  return (p || '').replace(/[\u2068\u2069]/g, '').trim();
}

function maskPhone(p: string) {
  const d = (p || '').replace(/\D/g, '');
  if (d.length === 11) return `${d.slice(0,3)}-${d.slice(3,7)}-${d.slice(7)}`;
  if (d.length === 10) return `${d.slice(0,3)}-${d.slice(3,6)}-${d.slice(6)}`;
  return p;
}

export default function SmsWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [badge, setBadge] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [phones, setPhones] = useState<any[]>([]);
  const [phoneForm, setPhoneForm] = useState({ phone_number: '', name: '' });
  const [copied, setCopied] = useState<number | null>(null);
  const [sendOpen, setSendOpen] = useState(false);
  const [sendDefaults, setSendDefaults] = useState<{phone:string; message:string}>({phone:'', message:''});
  const [lastFetchAt, setLastFetchAt] = useState<string>('-');
  const [fetchError, setFetchError] = useState<string>('');
  const lastIdRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchSms = () => {
    getLatestSms({ limit: '100' }).then((data: any[]) => {
      const list = Array.isArray(data) ? data : [];
      setMessages(list);
      setFetchError('');
      const now = new Date();
      setLastFetchAt(`${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`);
      if (list.length > 0) {
        const maxId = Math.max(...list.map(m => m.id));
        if (maxId > lastIdRef.current) {
          if (lastIdRef.current > 0 && !open) {
            setBadge(prev => prev + (maxId - lastIdRef.current));
            try {
              if (!audioRef.current) {
                audioRef.current = new Audio('data:audio/wav;base64,UklGRl9vT19teleWQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgA');
              }
              audioRef.current.play().catch(() => {});
            } catch {}
          }
          lastIdRef.current = maxId;
        }
      }
    }).catch((err: any) => {
      const code = err?.response?.status;
      const msg = code ? `HTTP ${code}` : (err?.message || '네트워크 오류');
      setFetchError(msg);
      // eslint-disable-next-line no-console
      console.error('[SmsWidget] fetchSms 실패:', err);
    });
  };

  useEffect(() => {
    fetchSms();
    const interval = setInterval(fetchSms, 3000);  // 3초 폴링
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (open) {
      setBadge(0);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [open, messages.length]);

  const loadPhones = () => getSmsPhones().then(setPhones).catch(() => {});
  useEffect(() => { if (showSettings) loadPhones(); }, [showSettings]);

  const handleAddPhone = async () => {
    if (!phoneForm.phone_number) return;
    await addSmsPhone(phoneForm);
    setPhoneForm({ phone_number: '', name: '' });
    loadPhones();
  };

  const handleCopy = (msg: any) => {
    const match = msg.message.match(/인증번호\s*\[?\s*(\d{4,8})\s*\]?/);
    const text = match ? match[1] : msg.message;
    navigator.clipboard.writeText(text);
    setCopied(msg.id);
    setTimeout(() => setCopied(null), 1500);
  };

  const handleReply = (msg: any) => {
    // 발신자에게 답장 모달 열기
    setSendDefaults({ phone: cleanPhone(msg.csphone) || cleanPhone(msg.phone), message: '' });
    setSendOpen(true);
  };

  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;

  return (
    <>
      {/* 최소화 아이콘 - 우측 하단 */}
      {!open && (
        <button onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-[56px] h-[56px] bg-[#1a1a2e] rounded-full flex items-center justify-center shadow-2xl hover:shadow-xl transition-all hover:scale-110 border-2 border-[#4cc9f0]">
          <MessageSquare size={24} className="text-[#4cc9f0]" />
          {badge > 0 && (
            <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[11px] font-bold rounded-full min-w-[22px] h-[22px] flex items-center justify-center px-1 animate-bounce">
              {badge > 99 ? '99+' : badge}
            </span>
          )}
          {messages.length > 0 && badge === 0 && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-[#4cc9f0] rounded-full" />
          )}
        </button>
      )}

      {/* 스마트폰 UI - 우측 하단 */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[240px] h-[500px] bg-[#1a1a2e] rounded-[28px] shadow-2xl flex flex-col overflow-hidden border-2 border-[#2a2a4a]" style={{ animation: 'slideUp 0.3s ease-out' }}>
          {/* Notch + status bar */}
          <div className="flex items-center justify-between px-4 pt-2 pb-1 text-[10px] text-[#c8c8e0]">
            <span>{timeStr}</span>
            <div className="w-16 h-[18px] bg-black rounded-b-xl" />
            <div className="flex items-center gap-1">
              <span>●●●</span>
              <span>🔋</span>
            </div>
          </div>

          {/* Title */}
          <div className="px-3 py-1.5 border-b border-[#2a2a4a]">
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-semibold text-[#e0e0e0]">수신 문자</span>
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-[#4cc9f0] font-bold">{messages.length}건</span>
                <button onClick={() => { fetchSms(); }} className="p-1 hover:bg-[#2a2a4a] rounded" title="새로고침">
                  <span className="text-[10px] text-[#888]">🔄</span>
                </button>
                <button onClick={() => setShowSettings(true)} className="p-1 hover:bg-[#2a2a4a] rounded">
                  <Settings size={12} className="text-[#888]" />
                </button>
                <button onClick={() => setOpen(false)} className="p-1 hover:bg-[#2a2a4a] rounded">
                  <X size={12} className="text-[#888]" />
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between mt-0.5">
              <span className="text-[8px] text-[#666]">갱신 {lastFetchAt} · 3초 자동</span>
              {fetchError && (
                <span className="text-[8px] text-red-400 font-bold">❌ {fetchError}</span>
              )}
            </div>
          </div>

          {/* Message list */}
          <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1.5">
            {messages.length > 0 ? messages.map(msg => {
              const isNew = (Date.now() - new Date(msg.received_at).getTime()) < 60000;
              const isCopied = copied === msg.id;
              const sender = cleanPhone(msg.csphone) || cleanPhone(msg.phone) || '알수없음';
              return (
                <div key={msg.id}
                  className={`rounded-lg px-2.5 py-2 transition-all text-[10px]
                    ${isCopied ? 'bg-[#00a651]/20 border border-[#00a651]' :
                      isNew ? 'bg-[#16213e] border border-[#4cc9f0] animate-pulse' :
                      'bg-[#16213e] border border-[#2a2a4a]'}`}>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-[#4cc9f0] font-medium">{maskPhone(sender)}</span>
                    <div className="flex items-center gap-1">
                      <span className="text-[#444] text-[8px]">#{msg.id}</span>
                      {isNew && <span className="bg-red-500 text-white text-[8px] px-1 rounded font-bold">NEW</span>}
                      {isCopied && <span className="text-[#00a651] text-[8px]">복사됨!</span>}
                      <span className="text-[#666]">{new Date(msg.received_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                  <p className="text-[#e0e0e0] leading-tight break-all mb-1.5">{msg.message}</p>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => handleCopy(msg)}
                      className="flex-1 bg-[#2a2a4a] hover:bg-[#3a3a5a] text-[#4cc9f0] py-1 rounded text-[9px] font-bold flex items-center justify-center gap-1"
                    >
                      <Copy size={9} /> 복사
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReply(msg)}
                      className="flex-1 bg-[#4cc9f0] hover:bg-[#3aa8d0] text-[#1a1a2e] py-1 rounded text-[9px] font-bold flex items-center justify-center gap-1"
                    >
                      <Reply size={9} /> 답장
                    </button>
                  </div>
                </div>
              );
            }) : (
              <div className="flex flex-col items-center justify-center h-full text-[#666] text-[11px] gap-2">
                <div>수신된 문자가 없습니다</div>
                {fetchError ? (
                  <div className="text-red-400 text-[10px] text-center px-3">
                    API 오류: {fetchError}<br/>
                    <span className="text-[8px]">F12 콘솔 확인</span>
                  </div>
                ) : (
                  <div className="text-[#444] text-[9px]">갱신 {lastFetchAt}</div>
                )}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* 발송 버튼 (위젯 하단) */}
          <div className="px-2 pb-1">
            <button
              onClick={() => { setSendDefaults({phone:'', message:''}); setSendOpen(true); }}
              className="w-full bg-[#4cc9f0] hover:bg-[#3aa8d0] text-[#1a1a2e] font-bold py-1.5 rounded text-[10px] flex items-center justify-center gap-1"
            >
              <Send size={11} /> 새 문자 발송
            </button>
          </div>

          {/* Home indicator */}
          <div className="flex justify-center py-2">
            <div className="w-20 h-[3px] bg-[#444] rounded-full" />
          </div>
        </div>
      )}

      {/* Phone settings modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl p-6 w-[400px] shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2"><Phone size={18} /> SMS 수신 설정</h2>
              <button onClick={() => setShowSettings(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>

            {/* Add phone */}
            <div className="flex gap-2 mb-4">
              <input value={phoneForm.phone_number} onChange={e => setPhoneForm({...phoneForm, phone_number: e.target.value})}
                placeholder="전화번호 (01012345678)" className="flex-1 border rounded px-3 py-2 text-sm" />
              <input value={phoneForm.name} onChange={e => setPhoneForm({...phoneForm, name: e.target.value})}
                placeholder="이름" className="w-24 border rounded px-3 py-2 text-sm" />
              <button onClick={handleAddPhone} className="px-3 py-2 bg-blue-600 text-white rounded text-sm"><Plus size={14} /></button>
            </div>

            {/* Phone list */}
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left">전화번호</th>
                    <th className="px-3 py-2 text-left">이름</th>
                    <th className="px-3 py-2 text-center">삭제</th>
                  </tr>
                </thead>
                <tbody>
                  {phones.map((p: any) => (
                    <tr key={p.id} className="border-t">
                      <td className="px-3 py-2 font-mono">{maskPhone(p.phone_number)}</td>
                      <td className="px-3 py-2">{p.name}</td>
                      <td className="px-3 py-2 text-center">
                        <button onClick={async () => { await removeSmsPhone(p.id); loadPhones(); }} className="text-red-500 hover:text-red-700"><Trash2 size={14} /></button>
                      </td>
                    </tr>
                  ))}
                  {phones.length === 0 && (
                    <tr><td colSpan={3} className="px-3 py-6 text-center text-gray-400">등록된 번호가 없습니다</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-gray-400 mt-3">
              안드로이드 Tasker/Automate 앱으로 문자 수신 시 자동으로 API를 호출하도록 설정하세요.
              <br/>API: POST http://{typeof window !== 'undefined' ? window.location.hostname : '192.168.1.16'}:8010/api/cpc/sms/receive/
            </p>
          </div>
        </div>
      )}

      {/* 발송 모달 (위젯에서 답장 / 새 발송) */}
      <SmsSendModal
        open={sendOpen}
        onClose={() => setSendOpen(false)}
        defaultPhone={sendDefaults.phone}
        defaultMessage={sendDefaults.message}
        onSent={fetchSms}
      />
    </>
  );
}
