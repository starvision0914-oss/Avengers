import { Package, Upload } from 'lucide-react';
import { themeStyles } from './constants';

interface Props {
  dark: boolean;
  onUploadClick: () => void;
}

export default function KeywordEmptyState({ dark, onUploadClick }: Props) {
  const s = themeStyles(dark);
  return (
    <div className={`rounded-xl border ${s.card} flex flex-col items-center justify-center py-20 px-4 text-center`}>
      <div className={`w-20 h-20 rounded-full flex items-center justify-center mb-4 ${dark ? 'bg-[#2a2b35]' : 'bg-gray-100'}`}>
        <Package size={36} className={s.text2} />
      </div>
      <h3 className={`text-lg font-bold ${s.text1} mb-1`}>등록된 상품이 없습니다</h3>
      <p className={`text-sm ${s.text2} mb-6 max-w-md`}>
        오너클랜에서 다운로드한 엑셀 또는 ZIP 파일을 업로드하여 상품대장을 시작하세요.
      </p>
      <button
        onClick={onUploadClick}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors"
      >
        <Upload size={16} />
        엑셀 업로드
      </button>
      <p className={`text-[11px] ${s.text3} mt-4`}>
        지원 형식: .xlsx / .zip (오너클랜 상품 일괄 다운로드)
      </p>
    </div>
  );
}
