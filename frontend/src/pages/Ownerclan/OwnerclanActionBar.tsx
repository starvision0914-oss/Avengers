import { useRef } from 'react';
import { Upload, FileSpreadsheet, FileText, RefreshCw, Download, Hash, LayoutGrid, List, Trash2, CheckSquare, Layers, Copy, ListChecks, Tag } from 'lucide-react';
import { themeStyles } from './constants';

interface Props {
  dark: boolean;
  view: 'table' | 'grid';
  onViewChange: (v: 'table' | 'grid') => void;
  onExcelUpload: (file: File) => void;
  onCsvUpload: (file: File) => void;
  onSoldoutUpload: (file: File) => void;
  onSync: () => void;
  onExcelDownload: () => void;
  onWCodes: () => void;
  onDeleteAll: () => void;
  onDeleteSelected: () => void;
  onDedupe: () => void;
  onCopyToMy: () => void;
  onCodeSearch: () => void;
  onElevenName: () => void;
  onElevenPrompt: () => void;
  onGmarketPrompt: () => void;
  onAuctionPrompt: () => void;
  codeSearchCount: number;
  selectedCount: number;
  busy?: boolean;
  syncing?: boolean;
}

export default function OwnerclanActionBar({
  dark, view, onViewChange,
  onExcelUpload, onCsvUpload, onSoldoutUpload, onSync, onExcelDownload, onWCodes,
  onDeleteAll, onDeleteSelected, onDedupe, onCopyToMy, onCodeSearch, onElevenName, onElevenPrompt, onGmarketPrompt, onAuctionPrompt, codeSearchCount, selectedCount,
  busy, syncing,
}: Props) {
  const s = themeStyles(dark);
  const xlsxRef = useRef<HTMLInputElement>(null);
  const csvRef = useRef<HTMLInputElement>(null);
  const txtRef = useRef<HTMLInputElement>(null);

  const btn = `inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed`;

  return (
    <div className={`flex flex-wrap items-center gap-2 rounded-xl border ${s.card} p-2.5`}>
      <input
        ref={xlsxRef} type="file" accept=".xlsx,.xls,.zip" hidden
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onExcelUpload(f); e.target.value = ''; }}
      />
      <input
        ref={csvRef} type="file" accept=".csv" hidden
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onCsvUpload(f); e.target.value = ''; }}
      />
      <input
        ref={txtRef} type="file" accept=".txt" hidden
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onSoldoutUpload(f); e.target.value = ''; }}
      />

      <button
        onClick={() => xlsxRef.current?.click()}
        disabled={busy}
        className={`${btn} bg-blue-600 hover:bg-blue-700 text-white`}
      >
        <Upload size={13} /> 엑셀/ZIP
      </button>
      <button
        onClick={() => csvRef.current?.click()}
        disabled={busy}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
      >
        <FileSpreadsheet size={13} /> CSV 상태
      </button>
      <button
        onClick={() => txtRef.current?.click()}
        disabled={busy}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
      >
        <FileText size={13} /> 품절 TXT
      </button>
      <button
        onClick={onSync}
        disabled={busy || syncing}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
      >
        <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} /> 동기화
      </button>

      <div className={`mx-1 w-px h-6 ${dark ? 'bg-[#2a2b35]' : 'bg-gray-200'}`} />

      <button
        onClick={onExcelDownload}
        disabled={busy}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
      >
        <Download size={13} /> 엑셀 받기
      </button>
      <button
        onClick={onWCodes}
        disabled={busy}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
      >
        <Hash size={13} /> W코드
      </button>
      <button
        onClick={onCodeSearch}
        disabled={busy}
        className={`${btn} ${codeSearchCount > 0 ? 'bg-blue-600 hover:bg-blue-700 text-white' : `${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}`}
        title={codeSearchCount > 0 ? `${codeSearchCount}개 코드 검색중 (클릭해서 수정)` : 'W코드 여러 개 한꺼번에 검색'}
      >
        <ListChecks size={13} /> 코드 대량검색 {codeSearchCount > 0 && <span className="ml-0.5 px-1.5 rounded-full bg-white/25 text-[10px]">{codeSearchCount}</span>}
      </button>
      <button
        onClick={onElevenName}
        disabled={busy}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
        title="선택 상품(없으면 현재 페이지)의 11번가 최적화 상품명 생성"
      >
        <Tag size={13} /> 11번가 상품명
      </button>
      <button
        onClick={onElevenPrompt}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
        title="11번가 상품명 생성용 AI 프롬프트 보기·복사"
      >
        <Tag size={13} /> 11번가 상품명변경
      </button>
      <button
        onClick={onGmarketPrompt}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
        title="지마켓 상품명 생성용 AI 프롬프트 보기·복사"
      >
        <Tag size={13} /> 지마켓 상품명변경
      </button>
      <button
        onClick={onAuctionPrompt}
        className={`${btn} ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
        title="옥션 상품명 생성용 AI 프롬프트 보기·복사"
      >
        <Tag size={13} /> 옥션 상품명변경
      </button>

      <div className={`mx-1 w-px h-6 ${dark ? 'bg-[#2a2b35]' : 'bg-gray-200'}`} />

      <button
        onClick={onCopyToMy}
        disabled={busy || selectedCount === 0}
        className={`${btn} ${selectedCount > 0 ? 'bg-purple-600 hover:bg-purple-700 text-white' : `${dark ? 'bg-[#2a2b35] text-gray-500' : 'bg-gray-100 text-gray-400'}`}`}
        title={selectedCount === 0 ? '체크박스로 상품을 선택하세요' : `${selectedCount}개를 나의 상품으로 복사`}
      >
        <Copy size={13} /> 나의 상품으로 복사 {selectedCount > 0 && <span className="ml-0.5 px-1.5 rounded-full bg-white/25 text-[10px]">{selectedCount}</span>}
      </button>
      <button
        onClick={onDeleteSelected}
        disabled={busy || selectedCount === 0}
        className={`${btn} ${selectedCount > 0 ? 'bg-red-600 hover:bg-red-700 text-white' : `${dark ? 'bg-[#2a2b35] text-gray-500' : 'bg-gray-100 text-gray-400'}`}`}
        title={selectedCount === 0 ? '체크박스로 상품을 선택하세요' : `${selectedCount}개 삭제`}
      >
        <CheckSquare size={13} /> 선택삭제 {selectedCount > 0 && <span className="ml-0.5 px-1.5 rounded-full bg-white/25 text-[10px]">{selectedCount}</span>}
      </button>
      <button
        onClick={onDedupe}
        disabled={busy}
        className={`${btn} bg-orange-500 hover:bg-orange-600 text-white`}
        title="상품명이 같은 상품 중 판매가가 더 높은 것을 삭제"
      >
        <Layers size={13} /> 중복삭제
      </button>
      <button
        onClick={onDeleteAll}
        disabled={busy}
        className={`${btn} bg-red-700 hover:bg-red-800 text-white`}
        title="전체 상품 삭제"
      >
        <Trash2 size={13} /> 전체삭제
      </button>

      <div className="ml-auto flex items-center gap-1">
        <button
          onClick={() => onViewChange('table')}
          className={`p-2 rounded-lg ${view === 'table' ? 'bg-blue-600 text-white' : `${s.text2} ${s.cardHover}`}`}
          aria-label="테이블 뷰"
        >
          <List size={15} />
        </button>
        <button
          onClick={() => onViewChange('grid')}
          className={`p-2 rounded-lg ${view === 'grid' ? 'bg-blue-600 text-white' : `${s.text2} ${s.cardHover}`}`}
          aria-label="그리드 뷰"
        >
          <LayoutGrid size={15} />
        </button>
      </div>
    </div>
  );
}
