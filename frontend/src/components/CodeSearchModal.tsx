import { useState, useEffect, useMemo, useRef } from 'react';
import { Search, X, CheckCircle2, ListChecks, Trash2 } from 'lucide-react';

interface Props {
  dark: boolean;
  open: boolean;
  title?: string;
  initialCodes?: string[];
  onClose: () => void;
  onSubmit: (codes: string[]) => void;
  onClear: () => void;
}

function parseCodes(text: string): string[] {
  const tokens = text.split(/[,\n\s]+/).map(t => t.trim()).filter(Boolean);
  return Array.from(new Set(tokens));
}

export default function CodeSearchModal({
  dark, open, title = '코드 대량 검색', initialCodes = [],
  onClose, onSubmit, onClear,
}: Props) {
  const [text, setText] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) {
      setText(initialCodes.join('\n'));
      setTimeout(() => ref.current?.focus(), 50);
    }
  }, [open, initialCodes]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSubmit();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const codes = useMemo(() => parseCodes(text), [text]);

  if (!open) return null;

  const cardCls = dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e5e7eb]';
  const text1 = dark ? 'text-gray-100' : 'text-gray-900';
  const text2 = dark ? 'text-gray-400' : 'text-gray-600';
  const text3 = dark ? 'text-gray-500' : 'text-gray-400';
  const inputBg = dark ? 'bg-[#0f1117] border-[#2a2b35] text-gray-100' : 'bg-white border-gray-300 text-gray-900';
  const cardHover = dark ? 'hover:bg-[#2a2b35]' : 'hover:bg-gray-100';

  function handleSubmit() {
    onSubmit(codes);
    onClose();
  }

  function handleClear() {
    setText('');
    onClear();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        className={`relative w-full max-w-xl rounded-2xl border ${cardCls} shadow-2xl flex flex-col`}
      >
        <header className={`flex items-center justify-between px-5 py-3 border-b ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
          <div className="flex items-center gap-2">
            <ListChecks size={18} className="text-blue-500" />
            <h3 className={`text-[12px] font-bold ${text1}`}>{title}</h3>
          </div>
          <button onClick={onClose} className={`p-1 rounded ${cardHover} ${text2}`}>
            <X size={16} />
          </button>
        </header>

        <div className="px-5 pt-4 pb-2">
          <p className={`text-[11px] ${text3} mb-2`}>
            W코드를 콤마(,) 또는 줄바꿈으로 구분해서 입력하세요. (Ctrl+Enter로 검색)
          </p>
          <textarea
            ref={ref}
            value={text}
            onChange={e => setText(e.target.value)}
            rows={10}
            placeholder="W12345678&#10;W12345679&#10;W12345680, W12345681"
            className={`w-full px-3 py-2 rounded-lg border text-[12px] font-mono outline-none focus:border-blue-500 transition-colors resize-y ${inputBg}`}
          />
        </div>

        <div className={`px-5 py-2 border-t ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 size={14} className={codes.length > 0 ? 'text-green-500' : text3} />
            <span className={`text-[12px] font-semibold ${text1}`}>
              유효 코드 {codes.length.toLocaleString()}개 인식됨
            </span>
          </div>
          {codes.length > 0 && (
            <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
              {codes.slice(0, 20).map(c => (
                <span
                  key={c}
                  className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono ${dark ? 'bg-[#0f1117] text-gray-300' : 'bg-gray-100 text-gray-700'}`}
                >
                  {c}
                </span>
              ))}
              {codes.length > 20 && (
                <span className={`text-[10px] ${text3}`}>+{codes.length - 20}개 더</span>
              )}
            </div>
          )}
        </div>

        <div className={`flex items-center gap-2 px-5 py-3 border-t ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
          {initialCodes.length > 0 && (
            <button
              onClick={handleClear}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-red-400' : 'bg-gray-100 hover:bg-gray-200 text-red-600'}`}
            >
              <Trash2 size={12} /> 검색 해제
            </button>
          )}
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={onClose}
              className={`px-4 py-2 rounded-lg text-[12px] font-semibold ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'}`}
            >
              취소
            </button>
            <button
              onClick={handleSubmit}
              disabled={codes.length === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-[12px] font-semibold bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40"
            >
              <Search size={12} /> 검색 ({codes.length.toLocaleString()})
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
