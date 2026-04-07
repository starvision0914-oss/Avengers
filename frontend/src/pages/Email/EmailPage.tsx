import { useEffect, useState } from 'react';
import { getEmailAccounts, getEmailMessages, getEmailMessage, syncEmail, sendEmail, createEmailAccount } from '../../api/emails';
import { Mail, RefreshCw, Send, Plus, Star, Settings } from 'lucide-react';
import toast from 'react-hot-toast';
import type { EmailAccount, EmailMsg } from '../../types';

export default function EmailPage() {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [messages, setMessages] = useState<EmailMsg[]>([]);
  const [selected, setSelected] = useState<EmailMsg | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [showCompose, setShowCompose] = useState(false);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [composeForm, setComposeForm] = useState({ account_id: '', to: '', cc: '', subject: '', body: '' });
  const [accountForm, setAccountForm] = useState({
    email_address: '', display_name: '', provider: 'naver',
    imap_host: 'imap.naver.com', imap_port: 993,
    smtp_host: 'smtp.naver.com', smtp_port: 587, smtp_use_tls: true,
    username: '', password: ''
  });

  const PROVIDER_DEFAULTS: Record<string, { imap_host: string; smtp_host: string }> = {
    naver: { imap_host: 'imap.naver.com', smtp_host: 'smtp.naver.com' },
    gmail: { imap_host: 'imap.gmail.com', smtp_host: 'smtp.gmail.com' },
    daum: { imap_host: 'imap.daum.net', smtp_host: 'smtp.daum.net' },
  };

  const load = () => {
    getEmailAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || []));
    getEmailMessages().then(d => setMessages(Array.isArray(d) ? d : d.results || []));
  };
  useEffect(() => { load(); }, []);

  const handleSync = async () => {
    if (accounts.length === 0) { toast.error('이메일 계정을 먼저 추가하세요.'); return; }
    setSyncing(true);
    for (const acc of accounts) {
      try { await syncEmail(acc.id); } catch { toast.error(`${acc.email_address} 동기화 실패`); }
    }
    setSyncing(false);
    toast.success('동기화 완료');
    load();
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await sendEmail({
        account_id: Number(composeForm.account_id),
        to: composeForm.to.split(',').map(s => s.trim()),
        cc: composeForm.cc ? composeForm.cc.split(',').map(s => s.trim()) : [],
        subject: composeForm.subject,
        body: composeForm.body,
      });
      toast.success('전송 완료');
      setShowCompose(false);
    } catch { toast.error('전송 실패'); }
  };

  const handleAccountSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createEmailAccount(accountForm);
      toast.success('계정 추가 완료');
      setShowAccountForm(false);
      load();
    } catch { toast.error('추가 실패'); }
  };

  const handleSelect = async (msg: EmailMsg) => {
    const detail = await getEmailMessage(msg.id);
    setSelected(detail);
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] bg-white rounded-lg shadow overflow-hidden">
      {/* Email List */}
      <div className="w-96 border-r flex flex-col">
        <div className="p-3 border-b flex items-center justify-between">
          <h2 className="font-semibold">이메일</h2>
          <div className="flex gap-2">
            <button onClick={() => setShowAccountForm(true)} className="text-gray-500 hover:text-blue-600"><Settings size={18} /></button>
            <button onClick={handleSync} disabled={syncing} className="text-gray-500 hover:text-blue-600"><RefreshCw size={18} className={syncing ? 'animate-spin' : ''} /></button>
            <button onClick={() => setShowCompose(true)} className="text-blue-600"><Send size={18} /></button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {messages.length > 0 ? messages.map(m => (
            <div key={m.id} onClick={() => handleSelect(m)}
              className={`px-4 py-3 border-b cursor-pointer hover:bg-gray-50 ${selected?.id === m.id ? 'bg-blue-50' : ''} ${!m.is_read ? 'font-semibold' : ''}`}>
              <div className="flex items-center justify-between">
                <p className="text-sm truncate flex-1">{m.from_name || m.from_addr}</p>
                <span className="text-xs text-gray-400 ml-2">{m.date ? new Date(m.date).toLocaleDateString('ko-KR') : ''}</span>
              </div>
              <p className="text-sm truncate">{m.subject}</p>
              <p className="text-xs text-gray-400 truncate">{m.snippet}</p>
            </div>
          )) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Mail size={40} className="mb-2" />
              <p>이메일이 없습니다</p>
              <p className="text-xs mt-1">계정을 추가하고 동기화하세요</p>
            </div>
          )}
        </div>
      </div>

      {/* Email Detail */}
      <div className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <div>
            <h2 className="text-xl font-bold mb-2">{selected.subject}</h2>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
              <span>{selected.from_name || selected.from_addr}</span>
              <span>&middot;</span>
              <span>{selected.date ? new Date(selected.date).toLocaleString('ko-KR') : ''}</span>
            </div>
            {selected.body_html ? (
              <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: selected.body_html }} />
            ) : (
              <pre className="whitespace-pre-wrap text-sm">{selected.body_text}</pre>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">이메일을 선택하세요</div>
        )}
      </div>

      {/* Compose Modal */}
      {showCompose && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSend} className="bg-white rounded-lg p-6 w-[500px]">
            <h2 className="text-lg font-bold mb-4">메일 쓰기</h2>
            <div className="space-y-3">
              <select value={composeForm.account_id} onChange={e => setComposeForm({...composeForm, account_id: e.target.value})} className="w-full border rounded px-3 py-2" required>
                <option value="">보내는 계정</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.email_address}</option>)}
              </select>
              <input value={composeForm.to} onChange={e => setComposeForm({...composeForm, to: e.target.value})} placeholder="받는 사람 (쉼표로 구분)" className="w-full border rounded px-3 py-2" required />
              <input value={composeForm.cc} onChange={e => setComposeForm({...composeForm, cc: e.target.value})} placeholder="참조 (CC)" className="w-full border rounded px-3 py-2" />
              <input value={composeForm.subject} onChange={e => setComposeForm({...composeForm, subject: e.target.value})} placeholder="제목" className="w-full border rounded px-3 py-2" required />
              <textarea value={composeForm.body} onChange={e => setComposeForm({...composeForm, body: e.target.value})} placeholder="내용" className="w-full border rounded px-3 py-2" rows={8} />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowCompose(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">보내기</button>
            </div>
          </form>
        </div>
      )}

      {/* Account Form Modal */}
      {showAccountForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleAccountSubmit} className="bg-white rounded-lg p-6 w-[450px] max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">이메일 계정 추가</h2>
            <div className="space-y-3">
              <select value={accountForm.provider} onChange={e => {
                const p = e.target.value;
                const d = PROVIDER_DEFAULTS[p] || { imap_host: '', smtp_host: '' };
                setAccountForm({...accountForm, provider: p, imap_host: d.imap_host, smtp_host: d.smtp_host });
              }} className="w-full border rounded px-3 py-2">
                <option value="naver">네이버</option>
                <option value="gmail">Gmail</option>
                <option value="daum">다음</option>
                <option value="custom">직접설정</option>
              </select>
              <input value={accountForm.email_address} onChange={e => setAccountForm({...accountForm, email_address: e.target.value})} placeholder="이메일 주소" className="w-full border rounded px-3 py-2" required />
              <input value={accountForm.display_name} onChange={e => setAccountForm({...accountForm, display_name: e.target.value})} placeholder="표시 이름" className="w-full border rounded px-3 py-2" />
              <input value={accountForm.username} onChange={e => setAccountForm({...accountForm, username: e.target.value})} placeholder="로그인 ID" className="w-full border rounded px-3 py-2" required />
              <input type="password" value={accountForm.password} onChange={e => setAccountForm({...accountForm, password: e.target.value})} placeholder="비밀번호" className="w-full border rounded px-3 py-2" required />
              <div className="grid grid-cols-2 gap-3">
                <input value={accountForm.imap_host} onChange={e => setAccountForm({...accountForm, imap_host: e.target.value})} placeholder="IMAP 서버" className="w-full border rounded px-3 py-2" />
                <input type="number" value={accountForm.imap_port} onChange={e => setAccountForm({...accountForm, imap_port: +e.target.value})} placeholder="IMAP 포트" className="w-full border rounded px-3 py-2" />
                <input value={accountForm.smtp_host} onChange={e => setAccountForm({...accountForm, smtp_host: e.target.value})} placeholder="SMTP 서버" className="w-full border rounded px-3 py-2" />
                <input type="number" value={accountForm.smtp_port} onChange={e => setAccountForm({...accountForm, smtp_port: +e.target.value})} placeholder="SMTP 포트" className="w-full border rounded px-3 py-2" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowAccountForm(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">추가</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
