import { useEffect, useState } from 'react';
import { X, Bot, Key, Users, Save, Send, ChevronDown, ChevronRight, AlertTriangle, Copy, Check, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/client';

interface Props {
  open: boolean;
  onClose: () => void;
}

interface TgConfig {
  id?: number;
  bot_token?: string;
  mode?: string;
}

interface TgRecipient {
  id?: number;
  chat_id: string;
  name?: string;
  is_active?: boolean;
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success('복사됨');
        setTimeout(() => setCopied(false), 1500);
      }}
      className="ml-2 inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? '복사됨' : '복사'}
    </button>
  );
}

const steps = [
  {
    icon: Bot,
    title: '1단계 — 텔레그램 설치 + 봇 만들기',
    body: (
      <div className="space-y-3 text-sm">
        <p>처음이시면 핸드폰에 텔레그램 앱부터 설치하세요.</p>
        <ol className="list-decimal pl-5 space-y-2 text-gray-700">
          <li>
            앱스토어/플레이스토어에서 <b>"Telegram"</b> 검색 → 설치 → 핸드폰 번호로 가입
          </li>
          <li>
            텔레그램 앱 안에서 상단 검색창에 <b className="text-blue-600">@BotFather</b> 입력
            <CopyBtn text="@BotFather" />
            <p className="text-xs text-gray-500 mt-1">파란 체크 표시(공식 인증) 있는 BotFather 선택</p>
          </li>
          <li>
            BotFather 채팅방에서 <code className="bg-gray-100 px-1.5 py-0.5 rounded text-blue-600">/newbot</code> 입력 → 전송
            <CopyBtn text="/newbot" />
          </li>
          <li>
            <b>봇 이름 입력</b>: 아무거나 (예: <code className="bg-gray-100 px-1 rounded">내문자알림</code>)
          </li>
          <li>
            <b>봇 사용자명 입력</b>: 영문 + 숫자, 끝이 반드시 <code className="bg-gray-100 px-1 rounded">_bot</code> 또는 <code className="bg-gray-100 px-1 rounded">Bot</code>
            <p className="text-xs text-gray-500 mt-1">예: <code>my_sms_alert_bot</code> (이미 있으면 다른 이름 시도)</p>
          </li>
        </ol>
        <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-800">
          ✅ 성공하면 BotFather가 답장으로 <b>긴 토큰</b>을 줍니다.<br/>
          예: <code className="text-[10px]">7891234567:AAEhBP3a4XYZxxxxx_zzzzzAa1Bb2Cc3Dd</code>
        </div>
      </div>
    ),
  },
  {
    icon: Key,
    title: '2단계 — 봇 토큰 복사해서 아래 입력',
    body: (
      <div className="space-y-3 text-sm">
        <p>BotFather가 보내준 토큰을 통째로 복사하세요.</p>
        <div className="bg-gray-900 text-green-400 font-mono text-xs p-3 rounded">
          예시: <span className="text-yellow-300">7891234567:AAEhBP3a4XYZxxxxx_zzzzzAa1Bb2Cc3Dd</span>
        </div>
        <ul className="list-disc pl-5 space-y-1 text-gray-700 text-xs">
          <li>토큰은 <b>비밀번호와 같습니다</b>. 다른 사람한테 보여주지 마세요.</li>
          <li>만약 노출됐다면 BotFather에서 <code>/revoke</code>로 재발급</li>
        </ul>
        <p className="text-blue-600 font-semibold">→ 아래 "봇 토큰" 칸에 붙여넣고 저장 버튼 누르세요.</p>
      </div>
    ),
  },
  {
    icon: Users,
    title: '3단계 — 내 챗 ID 알아내기',
    body: (
      <div className="space-y-3 text-sm">
        <p>봇이 메시지를 보낼 <b>"받는 사람"</b>이 누구인지 알아야 합니다. 이게 바로 챗 ID입니다.</p>
        <ol className="list-decimal pl-5 space-y-2 text-gray-700">
          <li>
            텔레그램에서 방금 만든 봇 검색 (사용자명 그대로)
            <p className="text-xs text-gray-500 mt-0.5">예: <code>@my_sms_alert_bot</code></p>
          </li>
          <li>
            봇 채팅방 열기 → 아래 <b>[시작]</b> 또는 <code>/start</code> 한 번 누르기
            <CopyBtn text="/start" />
            <p className="text-xs text-gray-500 mt-0.5">⚠️ 이걸 안 하면 봇이 사용자에게 메시지를 못 보냅니다!</p>
          </li>
          <li>
            텔레그램에서 다른 봇 검색: <b className="text-blue-600">@userinfobot</b>
            <CopyBtn text="@userinfobot" />
          </li>
          <li>
            userinfobot 채팅방 열기 → <code>/start</code> 누르기 → 답장에 <b>Id: 숫자</b>가 보임
            <p className="text-xs text-gray-500 mt-0.5">예: <code>Id: 5421983245</code> ← 이 숫자가 챗 ID</p>
          </li>
          <li>
            그 숫자를 복사해서 아래 <b>"챗 ID 추가"</b> 칸에 붙여넣고 추가 버튼 누르기
          </li>
        </ol>
        <div className="bg-yellow-50 border border-yellow-300 rounded p-3 text-xs text-yellow-800 flex gap-2">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <div>
            <b>여러 명이 같이 받고 싶으면</b>: 각자 봇한테 <code>/start</code> 누르고, 각자 @userinfobot으로 자기 챗 ID 알아낸 후, 모든 챗 ID를 추가하세요.
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: Save,
    title: '4단계 — 모드 선택 + 저장',
    body: (
      <div className="space-y-3 text-sm">
        <p>아래에서 <b>모드</b>를 선택하고 저장합니다.</p>
        <div className="grid grid-cols-2 gap-2">
          <div className="border rounded p-2">
            <div className="font-bold text-blue-700">변동감지</div>
            <p className="text-xs text-gray-600">새 문자가 올 때마다 즉시 전송 (추천)</p>
          </div>
          <div className="border rounded p-2">
            <div className="font-bold text-gray-500">OFF</div>
            <p className="text-xs text-gray-600">텔레그램 전송 안 함 (일시 중지)</p>
          </div>
        </div>
        <p className="text-blue-600 font-semibold">→ "변동감지" 선택 후 저장하면 끝!</p>
      </div>
    ),
  },
  {
    icon: Send,
    title: '5단계 — 테스트 전송',
    body: (
      <div className="space-y-3 text-sm">
        <p>저장 후 <b>"테스트 전송"</b> 버튼을 눌러서 텔레그램에 메시지가 도착하는지 확인합니다.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700">
          <li>아래 "테스트 전송" 버튼 누르기</li>
          <li>1~2초 안에 텔레그램에 알림 옴 → 성공! ✅</li>
          <li>안 오면: 봇한테 <code>/start</code> 안 누른 경우가 가장 흔함 (3단계 2번 다시)</li>
        </ol>
        <div className="bg-green-50 border border-green-300 rounded p-3 text-xs text-green-800">
          ✅ 테스트 성공하면 이제부터 핸드폰으로 들어오는 모든 SMS가 자동으로 텔레그램에도 도착합니다.
        </div>
      </div>
    ),
  },
];

export default function TelegramSetupGuide({ open, onClose }: Props) {
  const [openIdx, setOpenIdx] = useState(0);
  const [config, setConfig] = useState<TgConfig>({});
  const [recipients, setRecipients] = useState<TgRecipient[]>([]);
  const [tokenInput, setTokenInput] = useState('');
  const [modeInput, setModeInput] = useState('change');
  const [chatIdInput, setChatIdInput] = useState('');
  const [chatNameInput, setChatNameInput] = useState('');
  const [busy, setBusy] = useState(false);

  const loadAll = async () => {
    try {
      const cfgRes = await api.get('/cpc/telegram/config/');
      const list = cfgRes.data?.results || cfgRes.data || [];
      const cfg = list[0] || {};
      setConfig(cfg);
      setTokenInput(cfg.bot_token || '');
      setModeInput(cfg.mode || 'change');
    } catch {}
    try {
      const rcpRes = await api.get('/cpc/telegram/recipients/');
      const list = rcpRes.data?.results || rcpRes.data || [];
      setRecipients(list);
    } catch {}
  };

  useEffect(() => {
    if (open) loadAll();
  }, [open]);

  if (!open) return null;

  const saveConfig = async () => {
    if (!tokenInput.trim()) {
      toast.error('봇 토큰을 입력하세요');
      return;
    }
    setBusy(true);
    try {
      if (config.id) {
        await api.put(`/cpc/telegram/config/${config.id}/`, { bot_token: tokenInput.trim(), mode: modeInput });
      } else {
        await api.post('/cpc/telegram/config/', { bot_token: tokenInput.trim(), mode: modeInput });
      }
      toast.success('저장 완료');
      loadAll();
    } catch (e: any) {
      toast.error('저장 실패: ' + (e?.response?.data?.detail || e.message));
    } finally {
      setBusy(false);
    }
  };

  const addRecipient = async () => {
    if (!chatIdInput.trim()) {
      toast.error('챗 ID를 입력하세요');
      return;
    }
    try {
      await api.post('/cpc/telegram/recipients/', {
        chat_id: chatIdInput.trim(),
        name: chatNameInput.trim() || '사용자',
        is_active: true,
        auto_send: true,
      });
      toast.success('추가 완료');
      setChatIdInput('');
      setChatNameInput('');
      loadAll();
    } catch (e: any) {
      toast.error('추가 실패: ' + (e?.response?.data?.detail || e.message));
    }
  };

  const removeRecipient = async (id: number) => {
    if (!confirm('이 챗 ID를 삭제할까요?')) return;
    try {
      await api.delete(`/cpc/telegram/recipients/${id}/`);
      toast.success('삭제 완료');
      loadAll();
    } catch (e: any) {
      toast.error('삭제 실패');
    }
  };

  const sendTest = async () => {
    setBusy(true);
    try {
      const res = await api.post('/cpc/telegram/send/', {
        message: '🧪 <b>Avengers 텔레그램 테스트</b>\n\n이 메시지가 보이면 설정이 완료된 것입니다.\n이제부터 새 SMS가 도착하면 자동으로 알림이 옵니다.',
      });
      toast.success(`${res.data?.sent || 0}명에게 전송됨`);
    } catch (e: any) {
      toast.error('전송 실패: ' + (e?.response?.data?.error || e.message));
    } finally {
      setBusy(false);
    }
  };

  const isConfigured = !!(config.bot_token && recipients.length > 0 && config.mode !== 'off');

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-t-xl">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Bot size={22} /> 텔레그램 봇 설정 (초보자용 가이드)
            </h2>
            <p className="text-xs text-blue-100 mt-0.5">SMS가 오면 자동으로 텔레그램에 알림을 보내드립니다</p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white">
            <X size={22} />
          </button>
        </div>

        {/* Status badge */}
        <div className={`px-6 py-2 text-xs font-semibold ${isConfigured ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'} border-b`}>
          현재 상태:{' '}
          {isConfigured
            ? `✅ 설정 완료 (${recipients.length}명 등록, 모드: ${config.mode})`
            : '⚠️ 미설정 — 아래 가이드를 따라 설정해주세요'}
        </div>

        {/* Body scroll */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* 단계 가이드 */}
          <section>
            <h3 className="font-bold text-gray-800 mb-3">📖 따라하기 가이드</h3>
            <div className="space-y-2">
              {steps.map((step, idx) => {
                const Icon = step.icon;
                const isOpen = openIdx === idx;
                return (
                  <div key={idx} className="border rounded-lg overflow-hidden">
                    <button
                      onClick={() => setOpenIdx(isOpen ? -1 : idx)}
                      className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
                    >
                      <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                        <Icon size={18} className="text-blue-600" />
                      </div>
                      <span className="flex-1 font-semibold text-sm text-gray-800">{step.title}</span>
                      {isOpen ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
                    </button>
                    {isOpen && <div className="px-4 py-4 pl-16 bg-white">{step.body}</div>}
                  </div>
                );
              })}
            </div>
          </section>

          {/* 봇 토큰 입력 */}
          <section className="bg-gray-50 border rounded-lg p-4">
            <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
              <Key size={16} className="text-blue-600" />
              봇 토큰 + 모드 설정
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600 block mb-1">봇 토큰 (BotFather가 준 긴 문자열)</label>
                <input
                  type="text"
                  value={tokenInput}
                  onChange={e => setTokenInput(e.target.value)}
                  placeholder="7891234567:AAE..."
                  className="w-full border rounded px-3 py-2 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600 block mb-1">모드</label>
                <select
                  value={modeInput}
                  onChange={e => setModeInput(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="off">OFF (전송 안 함)</option>
                  <option value="change">변동감지 (새 SMS 즉시 전송) ✅ 추천</option>
                  <option value="15m">15분 (사용 안 함)</option>
                  <option value="1h">1시간 (사용 안 함)</option>
                </select>
              </div>
              <button
                onClick={saveConfig}
                disabled={busy}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white px-4 py-2 rounded text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Save size={16} /> {busy ? '저장 중...' : '봇 토큰 저장'}
              </button>
            </div>
          </section>

          {/* 챗 ID 관리 */}
          <section className="bg-gray-50 border rounded-lg p-4">
            <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
              <Users size={16} className="text-blue-600" />
              받는 사람 (챗 ID) 관리
            </h3>

            {/* 추가 폼 */}
            <div className="flex gap-2 mb-3">
              <input
                value={chatIdInput}
                onChange={e => setChatIdInput(e.target.value)}
                placeholder="챗 ID (숫자)"
                className="flex-1 border rounded px-3 py-2 text-sm font-mono"
              />
              <input
                value={chatNameInput}
                onChange={e => setChatNameInput(e.target.value)}
                placeholder="이름 (선택)"
                className="w-32 border rounded px-3 py-2 text-sm"
              />
              <button onClick={addRecipient} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-semibold">
                추가
              </button>
            </div>

            {/* 목록 */}
            <div className="border rounded bg-white overflow-hidden">
              {recipients.length === 0 ? (
                <div className="text-center text-gray-400 text-xs py-6">
                  등록된 챗 ID 없음 — 위 가이드 3단계 참고하세요
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs text-gray-500">
                    <tr>
                      <th className="px-3 py-2 text-left">이름</th>
                      <th className="px-3 py-2 text-left">챗 ID</th>
                      <th className="px-3 py-2 text-center">활성</th>
                      <th className="px-3 py-2 text-center">삭제</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recipients.map(r => (
                      <tr key={r.id} className="border-t">
                        <td className="px-3 py-2">{r.name || '-'}</td>
                        <td className="px-3 py-2 font-mono text-xs">{r.chat_id}</td>
                        <td className="px-3 py-2 text-center">{r.is_active ? '✅' : '❌'}</td>
                        <td className="px-3 py-2 text-center">
                          <button onClick={() => removeRecipient(r.id!)} className="text-red-500 hover:text-red-700 text-xs">
                            삭제
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          {/* 테스트 */}
          <section className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-bold text-blue-800 mb-2 flex items-center gap-2">
              <Send size={16} /> 테스트 전송
            </h3>
            <p className="text-xs text-blue-700 mb-3">
              위 설정이 완료되었으면 아래 버튼을 눌러 텔레그램에 테스트 메시지를 보내보세요.
            </p>
            <button
              onClick={sendTest}
              disabled={busy || !isConfigured}
              className="w-full bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-300 text-white px-4 py-2.5 rounded text-sm font-bold flex items-center justify-center gap-2"
            >
              <Send size={16} /> 테스트 메시지 전송
            </button>
          </section>

          {/* 도움말 */}
          <section className="text-xs text-gray-500 bg-gray-50 border rounded p-3">
            <p className="font-semibold text-gray-700 mb-1">📚 참고 링크</p>
            <ul className="space-y-1">
              <li>
                <a href="https://core.telegram.org/bots/features#botfather" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center gap-1">
                  BotFather 공식 문서 <ExternalLink size={10} />
                </a>
              </li>
              <li>
                <a href="https://telegram.org/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center gap-1">
                  텔레그램 공식 사이트 <ExternalLink size={10} />
                </a>
              </li>
            </ul>
          </section>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t bg-gray-50 flex justify-end rounded-b-xl">
          <button onClick={onClose} className="px-4 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded font-semibold">
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
