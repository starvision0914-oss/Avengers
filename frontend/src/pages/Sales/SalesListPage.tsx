import { useEffect, useState } from 'react';
import { getSalesRecords, deleteSalesRecord, createSalesRecord } from '../../api/sales';
import { getAccounts } from '../../api/accounts';
import { Plus, Trash2, Upload, MessageSquare, Copy, Reply, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import dayjs from 'dayjs';
import type { SellerAccount } from '../../types';
import { getLatestSmsList } from '../../api/sms';
import SmsSendModal from '../../components/SmsSendModal';

function smsCleanPhone(p?: string) { return (p || '').replace(/[\u2068\u2069]/g, '').trim(); }
function smsMaskPhone(p: string) {
  const d = (p || '').replace(/\D/g, '');
  if (d.length === 11) return `${d.slice(0,3)}-${d.slice(3,7)}-${d.slice(7)}`;
  if (d.length === 10) return `${d.slice(0,3)}-${d.slice(3,6)}-${d.slice(6)}`;
  return p;
}

export default function SalesListPage() {
  const [records, setRecords] = useState<any>({ results: [] });
  const [accounts, setAccounts] = useState<SellerAccount[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ seller: '', order_date: dayjs().format('YYYY-MM-DD'), product_name: '', product_code: '', quantity: 1, unit_price: 0, total_price: 0, commission: 0, shipping_fee: 0, net_profit: 0, order_number: '' });
  const navigate = useNavigate();
  // SMS 카드 state
  const [smsList, setSmsList] = useState<any[]>([]);
  const [smsLoading, setSmsLoading] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [sendDefaults, setSendDefaults] = useState<{phone:string;message:string}>({phone:'',message:''});

  const load = () => {
    getSalesRecords().then(setRecords);
    getAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || []));
  };
  useEffect(() => { load(); }, []);

  const loadSms = () => {
    setSmsLoading(true);
    getLatestSmsList({ limit: 10 }).then((d: any[]) => setSmsList(d || []))
      .catch(() => setSmsList([]))
      .finally(() => setSmsLoading(false));
  };
  useEffect(() => {
    loadSms();
    const t = setInterval(loadSms, 5000);
    return () => clearInterval(t);
  }, []);

  const copySms = (msg: any) => {
    const m = (msg.message || '').match(/(\d{4,8})/);
    const text = m ? m[1] : (msg.message || '');
    navigator.clipboard.writeText(text);
    toast.success(m ? `인증번호 복사: ${m[1]}` : '메시지 복사됨');
  };

  const replySms = (msg: any) => {
    setSendDefaults({ phone: smsCleanPhone(msg.phone), message: '' });
    setSendOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createSalesRecord(form);
      toast.success('매출 추가 완료');
      setShowForm(false);
      load();
    } catch { toast.error('추가 실패'); }
  };

  const list = records.results || records;

  return (
    <div>
      {/* 📩 SMS 카드 - DB의 최신 SMS를 그대로 표시 */}
      <div className="bg-white border border-blue-200 rounded-lg shadow-sm mb-6">
        <div className="flex items-center justify-between px-4 py-2.5 border-b bg-gradient-to-r from-blue-50 to-cyan-50">
          <h2 className="text-sm font-bold text-blue-900 flex items-center gap-2">
            <MessageSquare size={16} /> 수신 문자 (실시간 · DB 직결 · 5초 자동 새로고침)
            <span className="text-[10px] text-gray-500 font-normal">총 {smsList.length}건 표시</span>
          </h2>
          <div className="flex gap-2">
            <button
              onClick={loadSms}
              className="p-1 text-gray-500 hover:bg-white rounded"
              title="새로고침"
            >
              <RefreshCw size={14} className={smsLoading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => { setSendDefaults({phone:'',message:''}); setSendOpen(true); }}
              className="text-[11px] bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded font-semibold"
            >
              새 발송
            </button>
          </div>
        </div>
        <div className="max-h-[280px] overflow-y-auto">
          {smsList.length === 0 ? (
            <div className="text-center text-gray-400 py-6 text-xs">수신된 문자가 없습니다</div>
          ) : (
            <table className="w-full text-xs">
              <thead className="bg-gray-50 text-[10px] text-gray-500 sticky top-0">
                <tr>
                  <th className="px-3 py-1.5 text-left w-12">ID</th>
                  <th className="px-3 py-1.5 text-left w-32">발신</th>
                  <th className="px-3 py-1.5 text-left w-24">시각</th>
                  <th className="px-3 py-1.5 text-left">메시지</th>
                  <th className="px-3 py-1.5 text-center w-32">동작</th>
                </tr>
              </thead>
              <tbody>
                {smsList.map((m: any) => {
                  const sender = smsCleanPhone(m.phone) || smsCleanPhone(m.csphone) || '알수없음';
                  const isNew = (Date.now() - new Date(m.received_at).getTime()) < 60000;
                  return (
                    <tr key={m.id} className={`border-t ${isNew ? 'bg-yellow-50' : 'hover:bg-gray-50'}`}>
                      <td className="px-3 py-1.5 font-mono text-gray-400">#{m.id}</td>
                      <td className="px-3 py-1.5 font-mono text-blue-700 text-[11px]">
                        {smsMaskPhone(sender)}
                        {isNew && <span className="ml-1 text-[8px] bg-red-500 text-white px-1 rounded">NEW</span>}
                      </td>
                      <td className="px-3 py-1.5 text-gray-500 text-[10px] whitespace-nowrap">
                        {dayjs(m.received_at).format('MM/DD HH:mm:ss')}
                      </td>
                      <td className="px-3 py-1.5 text-gray-800 truncate max-w-md">{m.message}</td>
                      <td className="px-3 py-1.5">
                        <div className="flex gap-1 justify-center">
                          <button
                            onClick={() => copySms(m)}
                            className="px-2 py-0.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded text-[10px] flex items-center gap-1"
                            title="인증번호/메시지 복사"
                          >
                            <Copy size={10} /> 복사
                          </button>
                          <button
                            onClick={() => replySms(m)}
                            className="px-2 py-0.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-[10px] flex items-center gap-1"
                            title="이 발신자에게 답장"
                          >
                            <Reply size={10} /> 답장
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <SmsSendModal
        open={sendOpen}
        onClose={() => setSendOpen(false)}
        defaultPhone={sendDefaults.phone}
        defaultMessage={sendDefaults.message}
        onSent={loadSms}
      />

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">매출 데이터</h1>
        <div className="flex gap-2">
          <button onClick={() => navigate('/sales/upload')} className="flex items-center gap-1 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
            <Upload size={16} /> 매출 업로드
          </button>
          <button onClick={() => navigate('/sales/match')} className="flex items-center gap-1 bg-orange-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-orange-600">
            🔗 셀러 매칭
          </button>
          <button onClick={() => setShowForm(true)} className="flex items-center gap-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
            <Plus size={16} /> 수동 입력
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">주문일</th>
              <th className="px-4 py-3 text-left">셀러</th>
              <th className="px-4 py-3 text-left">상품명</th>
              <th className="px-4 py-3 text-right">수량</th>
              <th className="px-4 py-3 text-right">합계</th>
              <th className="px-4 py-3 text-right">순이익</th>
              <th className="px-4 py-3 text-center">상태</th>
              <th className="px-4 py-3 text-center">삭제</th>
            </tr>
          </thead>
          <tbody>
            {Array.isArray(list) && list.length > 0 ? list.map((r: any) => (
              <tr key={r.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">{r.order_date}</td>
                <td className="px-4 py-3">{r.seller_name}</td>
                <td className="px-4 py-3">{r.product_name}</td>
                <td className="px-4 py-3 text-right">{r.quantity}</td>
                <td className="px-4 py-3 text-right">{r.total_price?.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{r.net_profit?.toLocaleString()}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 rounded text-xs ${r.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{r.status === 'completed' ? '완료' : r.status}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <button onClick={async () => { await deleteSalesRecord(r.id); load(); }} className="text-red-600 hover:text-red-800"><Trash2 size={16} /></button>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">매출 데이터가 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg p-6 w-[480px] max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">매출 수동 입력</h2>
            <div className="space-y-3">
              <select value={form.seller} onChange={e => setForm({...form, seller: e.target.value})} className="w-full border rounded px-3 py-2" required>
                <option value="">셀러 선택</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.seller_name}</option>)}
              </select>
              <input type="date" value={form.order_date} onChange={e => setForm({...form, order_date: e.target.value})} className="w-full border rounded px-3 py-2" />
              <input value={form.order_number} onChange={e => setForm({...form, order_number: e.target.value})} placeholder="주문번호" className="w-full border rounded px-3 py-2" />
              <input value={form.product_name} onChange={e => setForm({...form, product_name: e.target.value})} placeholder="상품명" className="w-full border rounded px-3 py-2" required />
              <input value={form.product_code} onChange={e => setForm({...form, product_code: e.target.value})} placeholder="상품코드" className="w-full border rounded px-3 py-2" />
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs text-gray-500">수량</label><input type="number" value={form.quantity} onChange={e => setForm({...form, quantity: +e.target.value})} className="w-full border rounded px-3 py-2" /></div>
                <div><label className="text-xs text-gray-500">단가</label><input type="number" value={form.unit_price} onChange={e => setForm({...form, unit_price: +e.target.value})} className="w-full border rounded px-3 py-2" /></div>
                <div><label className="text-xs text-gray-500">합계</label><input type="number" value={form.total_price} onChange={e => setForm({...form, total_price: +e.target.value})} className="w-full border rounded px-3 py-2" /></div>
                <div><label className="text-xs text-gray-500">수수료</label><input type="number" value={form.commission} onChange={e => setForm({...form, commission: +e.target.value})} className="w-full border rounded px-3 py-2" /></div>
                <div><label className="text-xs text-gray-500">배송비</label><input type="number" value={form.shipping_fee} onChange={e => setForm({...form, shipping_fee: +e.target.value})} className="w-full border rounded px-3 py-2" /></div>
                <div><label className="text-xs text-gray-500">순이익</label><input type="number" value={form.net_profit} onChange={e => setForm({...form, net_profit: +e.target.value})} className="w-full border rounded px-3 py-2" /></div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg">취소</button>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">저장</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
