import { useState, useEffect } from 'react';
import { X, Send, Phone, MessageSquare } from 'lucide-react';
import toast from 'react-hot-toast';
import { createOutboxSms, getSmsDevices } from '../api/sms';

interface Props {
  open: boolean;
  onClose: () => void;
  defaultPhone?: string;
  defaultMessage?: string;
  onSent?: () => void;
}

export default function SmsSendModal({ open, onClose, defaultPhone = '', defaultMessage = '', onSent }: Props) {
  const [phone, setPhone] = useState(defaultPhone);
  const [message, setMessage] = useState(defaultMessage);
  const [senderPhone, setSenderPhone] = useState('');
  const [devices, setDevices] = useState<any[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!open) return;
    setPhone(defaultPhone);
    setMessage(defaultMessage);
    getSmsDevices().then((list: any[]) => {
      setDevices(list || []);
      const online = (list || []).find((d: any) => d.is_online);
      if (online) setSenderPhone(online.phone_number);
      else if (list && list.length > 0) setSenderPhone(list[0].phone_number);
    }).catch(() => setDevices([]));
  }, [open, defaultPhone, defaultMessage]);

  if (!open) return null;

  const bytes = new Blob([message]).size;
  const msgType = bytes > 80 ? 'LMS' : 'SMS';
  const canSend = phone.trim() && message.trim() && !sending;

  const handleSend = async () => {
    const cleanPhone = phone.replace(/[^0-9]/g, '');
    if (cleanPhone.length < 9) {
      toast.error('전화번호 형식이 올바르지 않습니다');
      return;
    }
    setSending(true);
    try {
      await createOutboxSms({
        phone_number: cleanPhone,
        message: message.trim(),
        sender_phone: senderPhone || undefined,
      });
      toast.success('발송 요청이 등록되었습니다 (5초 내 발송)');
      setMessage('');
      onSent?.();
      onClose();
    } catch (e: any) {
      toast.error('발송 실패: ' + (e?.response?.data?.error || e.message));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-[480px] max-w-[92vw]" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h2 className="text-base font-bold flex items-center gap-2">
            <MessageSquare size={18} className="text-blue-600" />
            문자 발송
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {devices.length === 0 && (
            <div className="bg-amber-50 border border-amber-300 rounded p-3 text-xs text-amber-800">
              ⚠️ 연결된 smsApp 디바이스가 없습니다. 핸드폰에 smsApp을 설치하고 서버 IP를 등록해주세요.
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-gray-600 mb-1 block">발신 디바이스</label>
            <select
              value={senderPhone}
              onChange={e => setSenderPhone(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
              disabled={devices.length === 0}
            >
              {devices.length === 0 && <option value="">디바이스 없음</option>}
              {devices.map((d: any) => (
                <option key={d.id} value={d.phone_number}>
                  {d.phone_number} {d.is_online ? '🟢 온라인' : '🔴 오프라인'}{d.app_version ? ` (v${d.app_version})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600 mb-1 block flex items-center gap-1">
              <Phone size={12} /> 받는 사람 (전화번호)
            </label>
            <input
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="01012345678"
              className="w-full border rounded px-3 py-2 text-sm font-mono"
              autoFocus
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-gray-600">메시지</label>
              <span className="text-[10px] text-gray-500">
                {bytes}바이트 · <span className={msgType === 'LMS' ? 'text-orange-600 font-bold' : 'text-blue-600 font-bold'}>{msgType}</span>
              </span>
            </div>
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="발송할 메시지를 입력하세요"
              rows={5}
              className="w-full border rounded px-3 py-2 text-sm resize-none"
            />
            <p className="text-[10px] text-gray-400 mt-1">80바이트 초과 시 LMS로 발송됩니다 (한글 약 40자)</p>
          </div>
        </div>

        <div className="px-5 py-3 border-t bg-gray-50 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded"
          >
            취소
          </button>
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 flex items-center gap-1.5"
          >
            <Send size={14} />
            {sending ? '발송 중...' : '발송'}
          </button>
        </div>
      </div>
    </div>
  );
}
