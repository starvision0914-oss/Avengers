import { useEffect, useState } from 'react';
import { getTelegramConfig, updateTelegramConfig, createTelegramConfig, getTelegramRecipients, createTelegramRecipient, deleteTelegramRecipient, sendTelegram } from '../../api/crawler';
import { Send, Plus, Trash2, Settings, Info } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TelegramPage() {
  const [config, setConfig] = useState<any>(null);
  const [recipients, setRecipients] = useState<any[]>([]);
  const [form, setForm] = useState({ bot_token: '', mode: 'off' });
  const [recipientForm, setRecipientForm] = useState({ chat_id: '', name: '' });
  const [testMsg, setTestMsg] = useState('');
  const [showGuide, setShowGuide] = useState(false);

  const load = () => {
    getTelegramConfig().then(d => {
      const list = Array.isArray(d) ? d : d.results || [];
      if (list.length > 0) {
        setConfig(list[0]);
        setForm({ bot_token: list[0].bot_token || '', mode: list[0].mode || 'off' });
      }
    });
    getTelegramRecipients().then(d => setRecipients(Array.isArray(d) ? d : d.results || []));
  };
  useEffect(() => { load(); }, []);

  const saveConfig = async () => {
    try {
      if (config) {
        await updateTelegramConfig(config.id, form);
      } else {
        await createTelegramConfig(form);
      }
      toast.success('설정 저장됨');
      load();
    } catch { toast.error('저장 실패'); }
  };

  const addRecipient = async () => {
    if (!recipientForm.chat_id) return;
    await createTelegramRecipient(recipientForm);
    setRecipientForm({ chat_id: '', name: '' });
    toast.success('수신자 추가됨');
    load();
  };

  const handleSend = async () => {
    if (!testMsg) return;
    const result = await sendTelegram(testMsg);
    toast.success(`${result.sent}명에게 전송 완료`);
    setTestMsg('');
  };

  return (
    <div className="max-w-[900px] mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">텔레그램 설정</h1>
        <button onClick={() => setShowGuide(!showGuide)} className="flex items-center gap-1 text-sm text-blue-600">
          <Info size={16} /> 연동 가이드
        </button>
      </div>

      {showGuide && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-5 text-sm space-y-3">
          <h3 className="font-bold text-blue-800">텔레그램 봇 연동 방법</h3>
          <ol className="list-decimal pl-5 space-y-2 text-blue-900">
            <li>텔레그램에서 <strong>@BotFather</strong>를 검색하여 대화를 시작합니다.</li>
            <li><code>/newbot</code> 명령어를 입력하고 봇 이름과 username을 설정합니다.</li>
            <li>BotFather가 제공하는 <strong>봇 토큰</strong>을 아래 설정에 입력합니다.</li>
            <li>생성된 봇과 대화를 시작합니다 (봇을 검색해서 /start 클릭).</li>
            <li>Chat ID 확인: 브라우저에서 <code>https://api.telegram.org/bot{'{'}&gt;{'}'}/getUpdates</code> 접속</li>
            <li>응답의 <code>message.chat.id</code> 값이 Chat ID입니다.</li>
            <li>아래 수신자 목록에 Chat ID를 추가합니다.</li>
          </ol>
          <p className="text-blue-700">그룹 채팅에서 사용하려면: 봇을 그룹에 초대 → 그룹에서 아무 메시지 전송 → getUpdates에서 음수 Chat ID 확인</p>
        </div>
      )}

      {/* 봇 설정 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2"><Settings size={18} /> 봇 설정</h2>
        <div className="space-y-3">
          <div>
            <label className="text-sm text-gray-600">봇 토큰</label>
            <input value={form.bot_token} onChange={e => setForm({...form, bot_token: e.target.value})}
              placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz" className="w-full border rounded px-3 py-2 font-mono text-sm" />
          </div>
          <div>
            <label className="text-sm text-gray-600">알림 모드</label>
            <div className="flex gap-2 mt-1">
              {[['off','OFF'],['change','변동감지'],['15m','15분'],['1h','1시간']].map(([k,v]) => (
                <button key={k} onClick={() => setForm({...form, mode: k})}
                  className={`px-4 py-2 rounded text-sm ${form.mode === k ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>{v}</button>
              ))}
            </div>
          </div>
          <button onClick={saveConfig} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">저장</button>
        </div>
      </div>

      {/* 수신자 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-semibold mb-4">수신자 목록</h2>
        <div className="flex gap-2 mb-4">
          <input value={recipientForm.chat_id} onChange={e => setRecipientForm({...recipientForm, chat_id: e.target.value})}
            placeholder="Chat ID" className="border rounded px-3 py-2 text-sm w-40" />
          <input value={recipientForm.name} onChange={e => setRecipientForm({...recipientForm, name: e.target.value})}
            placeholder="이름" className="border rounded px-3 py-2 text-sm w-32" />
          <button onClick={addRecipient} className="flex items-center gap-1 px-3 py-2 bg-green-600 text-white rounded text-sm"><Plus size={14} /> 추가</button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50"><tr>
            <th className="px-3 py-2 text-left">Chat ID</th>
            <th className="px-3 py-2 text-left">이름</th>
            <th className="px-3 py-2 text-center">상태</th>
            <th className="px-3 py-2 text-center">삭제</th>
          </tr></thead>
          <tbody>
            {recipients.map((r: any) => (
              <tr key={r.id} className="border-t">
                <td className="px-3 py-2 font-mono">{r.chat_id}</td>
                <td className="px-3 py-2">{r.name}</td>
                <td className="px-3 py-2 text-center"><span className={`px-2 py-0.5 rounded text-xs ${r.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{r.is_active ? '활성' : '비활성'}</span></td>
                <td className="px-3 py-2 text-center"><button onClick={() => { deleteTelegramRecipient(r.id); load(); }} className="text-red-500"><Trash2 size={14} /></button></td>
              </tr>
            ))}
            {recipients.length === 0 && <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">수신자가 없습니다.</td></tr>}
          </tbody>
        </table>
      </div>

      {/* 테스트 전송 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-semibold mb-4">테스트 전송</h2>
        <div className="flex gap-2">
          <input value={testMsg} onChange={e => setTestMsg(e.target.value)} placeholder="테스트 메시지" className="flex-1 border rounded px-3 py-2" />
          <button onClick={handleSend} className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm"><Send size={14} /> 전송</button>
        </div>
      </div>
    </div>
  );
}
