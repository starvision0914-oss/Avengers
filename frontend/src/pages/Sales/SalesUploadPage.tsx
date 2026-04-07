import { useState } from 'react';
import { uploadCSV } from '../../api/sales';
import { getAccounts } from '../../api/accounts';
import { useEffect } from 'react';
import { Upload, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import type { SellerAccount } from '../../types';

export default function SalesUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [seller, setSeller] = useState('');
  const [accounts, setAccounts] = useState<SellerAccount[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => { getAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || [])); }, []);

  const handleUpload = async () => {
    if (!file || !seller) { toast.error('파일과 셀러를 선택해주세요.'); return; }
    setLoading(true);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('seller', seller);
    try {
      const res = await uploadCSV(fd);
      setResult(res);
      toast.success(`${res.success_count}건 업로드 완료`);
    } catch { toast.error('업로드 실패'); }
    setLoading(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">CSV 매출 업로드</h1>
        <button onClick={() => navigate('/sales')} className="text-sm text-blue-600 hover:underline">목록으로</button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-4">
          <select value={seller} onChange={e => setSeller(e.target.value)} className="w-full border rounded px-3 py-2">
            <option value="">셀러 선택</option>
            {accounts.map(a => <option key={a.id} value={a.id}>{a.seller_name}</option>)}
          </select>

          <div className="border-2 border-dashed rounded-lg p-8 text-center"
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}
          >
            <Upload size={40} className="mx-auto text-gray-400 mb-3" />
            <p className="text-gray-500 mb-2">{file ? file.name : '파일을 드래그하거나 클릭하세요'}</p>
            <input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)} className="hidden" id="csv-input" />
            <label htmlFor="csv-input" className="text-blue-600 text-sm cursor-pointer hover:underline">파일 선택</label>
          </div>

          <div className="bg-gray-50 rounded p-4 text-sm">
            <p className="font-medium mb-2">CSV 필드 (한글 또는 영문):</p>
            <p className="text-gray-500">주문일(order_date), 주문번호(order_number), 상품명(product_name), 상품코드(product_code), 수량(quantity), 단가(unit_price), 합계(total_price), 수수료(commission), 배송비(shipping_fee), 순이익(net_profit)</p>
          </div>

          <button onClick={handleUpload} disabled={loading || !file} className="w-full bg-green-600 text-white rounded-lg py-2.5 font-medium hover:bg-green-700 disabled:opacity-50">
            {loading ? '업로드 중...' : '업로드'}
          </button>
        </div>

        {result && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="font-medium">업로드 결과</p>
            <p className="text-sm mt-1">전체: {result.row_count}건 / 성공: {result.success_count}건 / 실패: {result.error_count}건</p>
            {result.errors?.length > 0 && (
              <div className="mt-2 text-sm text-red-600">
                {result.errors.map((e: string, i: number) => <p key={i}>{e}</p>)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
