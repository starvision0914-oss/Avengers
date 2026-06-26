import { useState } from 'react';
import { X, Save, Plus, Trash2, Eye, EyeOff, Lock, Unlock, Key } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { updateAccount, createAccount, deleteAccount, type SmartStoreAccount } from '../../api/smartstore';

interface Props {
  accounts: SmartStoreAccount[];
  onClose: () => void;
  onSaved?: () => void;
}

type FormState = {
  login_id: string; login_pw: string; store_name: string; store_slug: string;
  display_name: string; memo: string; commerce_api_key: string; commerce_secret_key: string;
};

const EMPTY_FORM: FormState = {
  login_id: '', login_pw: '', store_name: '', store_slug: '',
  display_name: '', memo: '', commerce_api_key: '', commerce_secret_key: '',
};

export default function AccountSettingsModal({ accounts, onClose, onSaved }: Props) {
  const { dark } = useTheme();
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [showPw, setShowPw] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

  const bg = dark ? 'bg-[#0f1117]' : 'bg-white';
  const card = dark ? 'bg-[#1a1d27] border-[#2d3144]' : 'bg-white border-gray-200';
  const inp = dark ? 'bg-[#2d3144] border-[#3d4464] text-gray-100 placeholder-gray-500' : 'bg-gray-50 border-gray-300 text-gray-800';
  const text2 = dark ? 'text-gray-400' : 'text-gray-500';

  const startEdit = (a: SmartStoreAccount) => {
    setEditId(a.id);
    setForm({
      login_id: a.login_id, login_pw: '',
      store_name: a.store_name, store_slug: a.store_slug,
      display_name: a.display_name, memo: a.memo,
      commerce_api_key: '', commerce_secret_key: '',
    });
    setShowAdd(false);
  };

  const save = async () => {
    setSaving(true);
    try {
      if (editId) {
        const payload: Record<string, string> = {};
        if (form.login_pw) payload.login_pw = form.login_pw;
        if (form.store_name) payload.store_name = form.store_name;
        payload.store_slug = form.store_slug;
        payload.display_name = form.display_name;
        payload.memo = form.memo;
        if (form.commerce_api_key) payload.commerce_api_key = form.commerce_api_key;
        if (form.commerce_secret_key) payload.commerce_secret_key = form.commerce_secret_key;
        await updateAccount(editId, payload);
        setEditId(null);
      } else {
        await createAccount(form);
        setShowAdd(false);
      }
      onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: number) => {
    if (!confirm('이 계정을 비활성화하시겠습니까?')) return;
    await deleteAccount(id);
    onClose();
  };

  const F = (label: string, key: keyof FormState, opts?: { type?: string; placeholder?: string; readOnly?: boolean }) => (
    <div>
      <label className={`text-xs ${text2} mb-1 block`}>{label}</label>
      <input
        type={opts?.type || 'text'}
        className={`w-full px-3 py-2 rounded-lg border text-sm ${inp}`}
        value={form[key]}
        readOnly={opts?.readOnly}
        placeholder={opts?.placeholder}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className={`${bg} rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col`}>
        <div className={`flex items-center justify-between px-5 py-4 border-b ${dark ? 'border-[#2d3144]' : 'border-gray-200'}`}>
          <h2 className="font-bold text-lg">스마트스토어 계정 설정</h2>
          <button onClick={onClose} className={text2}><X size={20} /></button>
        </div>

        <div className="overflow-y-auto flex-1 p-4 space-y-2">
          {accounts.map(a => (
            <div key={a.id} className={`${card} border rounded-xl`}>
              {editId === a.id ? (
                <div className="p-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    {F('로그인 ID', 'login_id', { readOnly: true })}
                    <div>
                      <label className={`text-xs ${text2} mb-1 block`}>비밀번호 (빈칸=유지)</label>
                      <div className="relative">
                        <input
                          type={showPw ? 'text' : 'password'}
                          className={`w-full px-3 py-2 pr-9 rounded-lg border text-sm ${inp}`}
                          value={form.login_pw}
                          onChange={e => setForm(f => ({ ...f, login_pw: e.target.value }))}
                          placeholder="새 비밀번호"
                        />
                        <button type="button" onClick={() => setShowPw(v => !v)} className={`absolute right-2 top-2.5 ${text2}`}>
                          {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                      </div>
                    </div>
                    {F('스토어명', 'store_name')}
                    {F('표시명', 'display_name')}
                    {F('스토어 URL ID', 'store_slug', { placeholder: '복수스토어 계정에만' })}
                    {F('메모', 'memo')}
                  </div>

                  {/* 네이버 커머스 API 키 */}
                  <div className={`p-3 rounded-lg space-y-2 ${dark ? 'bg-[#13151f]' : 'bg-blue-50'}`}>
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400 mb-1">
                      <Key size={12} /> 네이버 커머스 API (상품 동기화)
                    </div>
                    {F('Client ID (빈칸=유지)', 'commerce_api_key', { placeholder: 'Client ID' })}
                    <div>
                      <label className={`text-xs ${text2} mb-1 block`}>Client Secret (빈칸=유지)</label>
                      <div className="relative">
                        <input
                          type={showApiKey ? 'text' : 'password'}
                          className={`w-full px-3 py-2 pr-9 rounded-lg border text-sm ${inp}`}
                          value={form.commerce_secret_key}
                          onChange={e => setForm(f => ({ ...f, commerce_secret_key: e.target.value }))}
                          placeholder="Client Secret"
                        />
                        <button type="button" onClick={() => setShowApiKey(v => !v)} className={`absolute right-2 top-2.5 ${text2}`}>
                          {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2 justify-end">
                    <button onClick={() => setEditId(null)} className={`px-4 py-1.5 rounded-lg text-sm ${dark ? 'bg-[#2d3144] text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
                      취소
                    </button>
                    <button onClick={save} disabled={saving} className="px-4 py-1.5 rounded-lg text-sm bg-[#03C75A] text-white flex items-center gap-1">
                      <Save size={13} /> {saving ? '저장 중...' : '저장'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${dark ? 'bg-[#2d3144] text-[#03C75A]' : 'bg-green-50 text-[#03C75A]'}`}>
                      {(a.display_name || a.store_name)[0]}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{a.display_name || a.store_name}</div>
                      <div className={`text-xs ${text2}`}>{a.login_id}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {a.has_pw ? <Unlock size={14} className="text-[#03C75A]" />
                              : <Lock size={14} className="text-red-400" />}
                    {a.has_api_key
                      ? <span className="text-xs text-blue-400 flex items-center gap-0.5"><Key size={11} />API</span>
                      : <span className={`text-xs ${text2} flex items-center gap-0.5`}><Key size={11} />-</span>}
                    <button onClick={() => startEdit(a)} className={`text-xs px-3 py-1 rounded-lg ${dark ? 'bg-[#2d3144] text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
                      수정
                    </button>
                    <button onClick={() => del(a.id)} className="text-xs px-2 py-1 rounded-lg text-red-400 hover:bg-red-400/10">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* 계정 추가 */}
          {showAdd ? (
            <div className={`${card} border rounded-xl p-4 space-y-3`}>
              <h3 className="text-sm font-semibold">새 계정 추가</h3>
              <div className="grid grid-cols-2 gap-3">
                {(['login_id', 'login_pw', 'store_name', 'display_name', 'store_slug', 'memo'] as const).map(f => (
                  <div key={f}>
                    <label className={`text-xs ${text2} mb-1 block`}>
                      {{ login_id: '로그인ID', login_pw: '비밀번호', store_name: '스토어명', display_name: '표시명', store_slug: '스토어URL ID', memo: '메모' }[f]}
                    </label>
                    <input
                      type={f === 'login_pw' ? 'password' : 'text'}
                      className={`w-full px-3 py-2 rounded-lg border text-sm ${inp}`}
                      value={form[f]}
                      onChange={e => setForm(prev => ({ ...prev, [f]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
              <div className={`p-3 rounded-lg space-y-2 ${dark ? 'bg-[#13151f]' : 'bg-blue-50'}`}>
                <div className="text-xs font-semibold text-blue-400 mb-1 flex items-center gap-1"><Key size={12} /> 네이버 커머스 API (선택)</div>
                {F('Client ID', 'commerce_api_key')}
                {F('Client Secret', 'commerce_secret_key', { type: 'password' })}
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowAdd(false)} className={`px-4 py-1.5 rounded-lg text-sm ${dark ? 'bg-[#2d3144]' : 'bg-gray-100'}`}>취소</button>
                <button onClick={save} disabled={saving} className="px-4 py-1.5 bg-[#03C75A] text-white text-sm rounded-lg">저장</button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => { setShowAdd(true); setEditId(null); setForm(EMPTY_FORM); }}
              className={`w-full py-3 border-2 border-dashed rounded-xl text-sm ${dark ? 'border-[#2d3144] text-gray-500 hover:border-[#03C75A]' : 'border-gray-200 text-gray-400 hover:border-green-400'} flex items-center justify-center gap-2 transition-colors`}
            >
              <Plus size={16} /> 계정 추가
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
