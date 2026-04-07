import { useEffect, useState } from 'react';
import { getAccounts, createAccount, updateAccount, deleteAccount } from '../../api/accounts';
import type { SellerAccount } from '../../types';
import { Plus, Edit2, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AccountListPage() {
  const [accounts, setAccounts] = useState<SellerAccount[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SellerAccount | null>(null);
  const [form, setForm] = useState({ seller_id: '', seller_name: '', platform: 'gmarket', memo: '', display_order: 0 });

  const load = () => getAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || []));
  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) {
        await updateAccount(editing.id, form);
        toast.success('수정 완료');
      } else {
        await createAccount(form);
        toast.success('추가 완료');
      }
      setShowForm(false);
      setEditing(null);
      load();
    } catch { toast.error('저장 실패'); }
  };

  const handleEdit = (a: SellerAccount) => {
    setEditing(a);
    setForm({ seller_id: a.seller_id, seller_name: a.seller_name, platform: a.platform, memo: a.memo, display_order: a.display_order });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('삭제하시겠습니까?')) return;
    await deleteAccount(id);
    toast.success('삭제 완료');
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">판매자 계정</h1>
        <button onClick={() => { setEditing(null); setForm({ seller_id: '', seller_name: '', platform: 'gmarket', memo: '', display_order: 0 }); setShowForm(true); }}
          className="flex items-center gap-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={16} /> 계정 추가
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">셀러 ID</th>
              <th className="px-4 py-3 text-left">이름</th>
              <th className="px-4 py-3 text-left">플랫폼</th>
              <th className="px-4 py-3 text-left">상태</th>
              <th className="px-4 py-3 text-left">메모</th>
              <th className="px-4 py-3 text-center">관리</th>
            </tr>
          </thead>
          <tbody>
            {accounts.length > 0 ? accounts.map(a => (
              <tr key={a.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{a.seller_id}</td>
                <td className="px-4 py-3">{a.seller_name}</td>
                <td className="px-4 py-3">{a.platform}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {a.is_active ? '활성' : '비활성'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{a.memo}</td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => handleEdit(a)} className="text-blue-600 hover:text-blue-800 mr-2"><Edit2 size={16} /></button>
                  <button onClick={() => handleDelete(a.id)} className="text-red-600 hover:text-red-800"><Trash2 size={16} /></button>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">등록된 판매자 계정이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg p-6 w-[400px]">
            <h2 className="text-lg font-bold mb-4">{editing ? '계정 수정' : '계정 추가'}</h2>
            <div className="space-y-3">
              <input value={form.seller_id} onChange={e => setForm({...form, seller_id: e.target.value})} placeholder="셀러 ID" className="w-full border rounded px-3 py-2" required />
              <input value={form.seller_name} onChange={e => setForm({...form, seller_name: e.target.value})} placeholder="셀러 이름" className="w-full border rounded px-3 py-2" required />
              <select value={form.platform} onChange={e => setForm({...form, platform: e.target.value})} className="w-full border rounded px-3 py-2">
                <option value="gmarket">Gmarket</option>
                <option value="auction">Auction</option>
                <option value="11st">11번가</option>
                <option value="coupang">쿠팡</option>
                <option value="smartstore">스마트스토어</option>
              </select>
              <input type="number" value={form.display_order} onChange={e => setForm({...form, display_order: +e.target.value})} placeholder="표시 순서" className="w-full border rounded px-3 py-2" />
              <textarea value={form.memo} onChange={e => setForm({...form, memo: e.target.value})} placeholder="메모" className="w-full border rounded px-3 py-2" rows={2} />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => { setShowForm(false); setEditing(null); }} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">저장</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
