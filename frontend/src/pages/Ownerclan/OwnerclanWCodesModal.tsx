import { useState } from 'react';
import { X, Copy, Check } from 'lucide-react';
import { themeStyles } from './constants';
import toast from 'react-hot-toast';

interface Props {
  dark: boolean;
  codes: string[] | null;
  onClose: () => void;
}

export default function OwnerclanWCodesModal({ dark, codes, onClose }: Props) {
  const s = themeStyles(dark);
  const [copied, setCopied] = useState(false);
  if (!codes) return null;
  const text = codes.join('\n');
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('클립보드에 복사되었습니다');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error('복사 실패');
    }
  };
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className={`w-full max-w-xl rounded-2xl border ${s.card} shadow-2xl overflow-hidden`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={`flex items-center justify-between px-5 py-3 border-b ${s.border}`}>
          <div className={`text-[12px] font-bold ${s.text1}`}>W코드 ({codes.length}개)</div>
          <div className="flex items-center gap-2">
            <button
              onClick={copy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold"
            >
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? '복사됨' : '복사'}
            </button>
            <button onClick={onClose} className={`p-1 rounded ${s.cardHover} ${s.text2}`}><X size={16} /></button>
          </div>
        </header>
        <div className="p-4">
          <textarea
            readOnly
            value={text}
            className={`w-full h-[400px] font-mono text-[12px] p-3 rounded-lg border resize-none ${s.inputBg}`}
          />
        </div>
      </div>
    </div>
  );
}
