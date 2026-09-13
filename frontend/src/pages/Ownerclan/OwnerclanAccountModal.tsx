import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../api/client';

interface OwnerclanApiAccountRow {
  id: number;
  login_id: string;
  is_active: boolean;
  balance: string;
  last_synced_at: string | null;
}

interface Props {
  onClose: () => void;
  onSaved?: () => void;
}

export default function OwnerclanAccountModal({ onClose, onSaved }: Props) {
  const [accounts, setAccounts] = useState<OwnerclanApiAccountRow[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [loginId, setLoginId] = useState('');
  const [loginPw, setLoginPw] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    api.get('/ownerclan/accounts/').then(r => setAccounts(r.data || [])).catch(() => toast.error('계정 로드 실패'));
  };
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!loginId.trim() || !loginPw) { toast.error('아이디/비밀번호를 입력하세요'); return; }
    setSaving(true);
    try {
      await api.post('/ownerclan/accounts/', { login_id: loginId.trim(), login_pw: loginPw });
      toast.success('계정 추가 완료');
      setLoginId(''); setLoginPw(''); setShowAdd(false);
      load(); onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.error || '추가 실패');
    } finally { setSaving(false); }
  };

  const toggleActive = async (a: OwnerclanApiAccountRow) => {
    try {
      await api.patch(`/ownerclan/accounts/${a.id}/`, { is_active: !a.is_active });
      load(); onSaved?.();
    } catch { toast.error('변경 실패'); }
  };

  const del = async (a: OwnerclanApiAccountRow) => {
    if (!confirm(`${a.login_id} 계정을 삭제할까요?`)) return;
    try {
      await api.delete(`/ownerclan/accounts/${a.id}/`);
      toast.success('삭제 완료');
      load(); onSaved?.();
    } catch { toast.error('삭제 실패'); }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e7eb]">
          <h2 className="font-bold text-[15px] text-[#222]">오너클랜 계정 관리</h2>
          <button onClick={onClose} className="text-[#888]"><X size={20} /></button>
        </div>

        <div className="overflow-y-auto flex-1 p-4 space-y-2">
          {accounts.map(a => (
            <div key={a.id} className="border border-[#e5e7eb] rounded-xl px-4 py-2.5 flex items-center justify-between">
              <div>
                <div className="text-[14px] font-semibold text-[#222]">{a.login_id}</div>
                <div className="text-[12px] text-[#888]">
                  {a.is_active ? '사용중' : '비활성'}{a.balance ? ` · 오너클랜머니 ${a.balance}` : ''}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => toggleActive(a)}
                  className={`text-[12px] px-2.5 py-1 rounded-lg font-semibold ${a.is_active ? 'bg-[#dcfce7] text-[#15803d]' : 'bg-[#f3f4f6] text-[#666]'}`}>
                  {a.is_active ? 'ON' : 'OFF'}
                </button>
                <button onClick={() => del(a)} className="text-red-500 hover:text-red-400"><Trash2 size={15} /></button>
              </div>
            </div>
          ))}
          {accounts.length === 0 && (
            <div className="text-center py-6 text-[13px] text-[#999]">등록된 계정이 없습니다</div>
          )}

          {showAdd ? (
            <div className="border border-[#e5e7eb] rounded-xl p-4 space-y-3">
              <div>
                <label className="text-[12px] text-[#888] mb-1 block">오너클랜 로그인 아이디</label>
                <input value={loginId} onChange={e => setLoginId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#d1d5db] text-[14px]" placeholder="ownerclan.com 판매사 아이디" />
              </div>
              <div>
                <label className="text-[12px] text-[#888] mb-1 block">비밀번호</label>
                <div className="relative">
                  <input value={loginPw} onChange={e => setLoginPw(e.target.value)}
                    type={showPw ? 'text' : 'password'}
                    className="w-full px-3 py-2 pr-9 rounded-lg border border-[#d1d5db] text-[14px]" placeholder="비밀번호" />
                  <button type="button" onClick={() => setShowPw(v => !v)} className="absolute right-2 top-2.5 text-[#888]">
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 rounded-lg text-[13px] bg-[#f3f4f6] text-[#666]">취소</button>
                <button onClick={add} disabled={saving} className="px-3 py-1.5 rounded-lg text-[13px] bg-[#2563eb] text-white flex items-center gap-1">
                  <Save size={13} /> {saving ? '저장 중...' : '추가'}
                </button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowAdd(true)}
              className="w-full py-3 border-2 border-dashed border-[#e5e7eb] rounded-xl text-[13px] text-[#999] hover:border-[#2563eb] flex items-center justify-center gap-2">
              <Plus size={15} /> 계정 추가
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
