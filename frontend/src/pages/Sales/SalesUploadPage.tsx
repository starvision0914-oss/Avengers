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
    if (!file) { toast.error('파일을 선택해주세요.'); return; }
    setLoading(true);
    const fd = new FormData();
    fd.append('file', file);
    if (seller) fd.append('seller', seller);
    try {
      const res = await uploadCSV(fd);
      setResult(res);
      toast.success(`${res.success_count}건 업로드 완료`);
    } catch (e: any) {
      // 응답이 없는 네트워크 에러는 서버에선 저장됐을 수 있음(기간교체라 재업로드해도 중복 안 생김)
      const noResponse = !e?.response;
      const msg = e?.response?.data?.error || e?.message || '업로드 실패';
      const shown = noResponse
        ? `${msg} — 서버에 저장됐을 수 있습니다. 목록을 확인하고, 안 됐으면 같은 파일을 다시 올리세요(같은 기간은 자동 교체되어 중복되지 않습니다).`
        : msg;
      toast.error(shown);
      setResult({ error: shown });
    }
    setLoading(false);
  };

  const downloadSample = () => {
    const headers = '셀러,주문일,주문번호,상품명,상품코드,수량,단가,합계,수수료,배송비,순이익';
    const example = '스타피1,2026-06-06,202606060001,샘플상품,P001,1,10000,10000,1000,2500,3500';
    const blob = new Blob(['﻿' + headers + '\n' + example], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = '매출업로드_샘플.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">매출 자료 업로드 (CSV·엑셀)</h1>
        <button onClick={() => navigate('/sales')} className="text-sm text-blue-600 hover:underline">목록으로</button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-4">
          <select value={seller} onChange={e => setSeller(e.target.value)} className="w-full border rounded px-3 py-2">
            <option value="">셀러 선택 (선택사항 — 파일에 '셀러' 컬럼 있으면 불필요)</option>
            {accounts.map(a => <option key={a.id} value={a.id}>{a.seller_name}</option>)}
          </select>

          <div className="border-2 border-dashed rounded-lg p-8 text-center"
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}
          >
            <Upload size={40} className="mx-auto text-gray-400 mb-3" />
            <p className="text-gray-500 mb-2">{file ? file.name : 'CSV·엑셀(.xlsx) 파일을 드래그하거나 클릭하세요'}</p>
            <input type="file" accept=".csv,.xlsx,.xls" onChange={e => setFile(e.target.files?.[0] || null)} className="hidden" id="csv-input" />
            <label htmlFor="csv-input" className="text-blue-600 text-sm cursor-pointer hover:underline">파일 선택</label>
          </div>

          <div className="bg-gray-50 rounded p-4 text-sm">
            <div className="flex items-center justify-between mb-2">
              <p className="font-medium">필드 (한글 또는 영문, 첫 행 = 헤더):</p>
              <button onClick={downloadSample} className="text-blue-600 text-xs hover:underline flex items-center gap-1">
                <FileText size={14} /> 샘플 양식 다운로드
              </button>
            </div>
            <p className="text-gray-500"><b>셀러</b>(seller_name/아이디), 주문일(order_date), 주문번호(order_number), 상품명(product_name), 상품코드(product_code), 수량(quantity), 단가(unit_price), 합계(total_price), 수수료(commission), 배송비(shipping_fee), 순이익(net_profit)</p>
            <p className="text-gray-400 mt-2 text-xs">※ <b>여러 셀러가 섞인 파일 하나</b>를 통째로 올릴 수 있습니다 — 각 행의 '셀러' 컬럼(셀러명 또는 아이디)으로 자동 매칭됩니다. (셀러 컬럼이 없으면 위에서 셀러를 선택)<br/>※ 금액은 콤마(1,000)·"원" 포함돼도 자동 처리. 광고비는 크롤링값과 자동 합산되어 순수익 계산됩니다.</p>
          </div>

          <button onClick={handleUpload} disabled={loading || !file} className="w-full bg-green-600 text-white rounded-lg py-2.5 font-medium hover:bg-green-700 disabled:opacity-50">
            {loading ? '업로드 중...' : '업로드'}
          </button>
        </div>

        {result && (
          <div className={`mt-6 p-4 rounded-lg ${result.error ? 'bg-red-50' : 'bg-blue-50'}`}>
            <p className="font-medium">업로드 결과</p>
            {result.error ? (
              <p className="text-sm mt-1 text-red-600">❌ {result.error}</p>
            ) : (
              <p className="text-sm mt-1">전체: {result.row_count}건 / 성공: {result.success_count}건 / 실패: {result.error_count}건</p>
            )}
            {result.errors?.length > 0 && (
              <div className="mt-2 text-sm text-red-600">
                {result.errors.map((e: string, i: number) => <p key={i}>{e}</p>)}
              </div>
            )}
            {result.detected_columns && (
              <div className="mt-3 text-sm">
                <p className="text-orange-700 font-medium">⚠️ {result.hint}</p>
                <p className="mt-1 text-gray-600">파일의 실제 컬럼: <b>{result.detected_columns.join(' / ')}</b></p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
