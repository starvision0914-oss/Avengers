import { useEffect, useState, useRef } from 'react';
import { getLatestSms, getSmsPhones, addSmsPhone, removeSmsPhone } from '../api/crawler';
import { MessageSquare, X, Settings, Phone, Plus, Trash2 } from 'lucide-react';

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
  const lastIdRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchSms = () => {
    getLatestSms().then((data: any[]) => {
      setMessages(data);
      if (data.length > 0) {
        const maxId = Math.max(...data.map(m => m.id));
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
    }).catch(() => {});
  };

  useEffect(() => {
    fetchSms();
    const interval = setInterval(fetchSms, 5000);
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
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#2a2a4a]">
            <span className="text-[12px] font-semibold text-[#e0e0e0]">수신 문자</span>
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-[#4cc9f0]">{messages.length}건</span>
              <button onClick={() => setShowSettings(true)} className="p-1 hover:bg-[#2a2a4a] rounded">
                <Settings size={12} className="text-[#888]" />
              </button>
              <button onClick={() => setOpen(false)} className="p-1 hover:bg-[#2a2a4a] rounded">
                <X size={12} className="text-[#888]" />
              </button>
            </div>
          </div>

          {/* Message list */}
          <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1.5">
            {messages.length > 0 ? messages.map(msg => {
              const isNew = (Date.now() - new Date(msg.received_at).getTime()) < 60000;
              const isCopied = copied === msg.id;
              return (
                <div key={msg.id}
                  onDoubleClick={() => handleCopy(msg)}
                  className={`rounded-lg px-2.5 py-2 cursor-pointer transition-all text-[10px]
                    ${isCopied ? 'bg-[#00a651]/20 border border-[#00a651]' :
                      isNew ? 'bg-[#16213e] border border-[#4cc9f0] animate-pulse' :
                      'bg-[#16213e] border border-[#2a2a4a]'}`}>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-[#4cc9f0] font-medium">{maskPhone(msg.csphone || msg.phone)}</span>
                    <div className="flex items-center gap-1">
                      {isNew && <span className="bg-red-500 text-white text-[8px] px-1 rounded font-bold">NEW</span>}
                      {isCopied && <span className="text-[#00a651] text-[8px]">복사됨!</span>}
                      <span className="text-[#666]">{new Date(msg.received_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                  <p className="text-[#e0e0e0] leading-tight break-all">{msg.message}</p>
                </div>
              );
            }) : (
              <div className="flex items-center justify-center h-full text-[#666] text-[11px]">수신된 문자가 없습니다</div>
            )}
            <div ref={bottomRef} />
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
              <br/>API: POST http://192.168.219.155:8010/api/cpc/sms/receive/
            </p>
          </div>
        </div>
      )}
    </>
  );
}
