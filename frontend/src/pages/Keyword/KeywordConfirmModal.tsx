import { AlertTriangle, X } from 'lucide-react';
import { themeStyles } from './constants';

interface Props {
  dark: boolean;
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  variant?: 'danger' | 'warning';
  onConfirm: () => void;
  onCancel: () => void;
}

export default function KeywordConfirmModal({
  dark, open, title, message,
  confirmLabel = '삭제', cancelLabel = '취소',
  busy, variant = 'danger',
  onConfirm, onCancel,
}: Props) {
  if (!open) return null;
  const s = themeStyles(dark);
  const accent = variant === 'danger' ? 'text-red-500' : 'text-orange-500';
  const btnConfirm = variant === 'danger'
    ? 'bg-red-600 hover:bg-red-700 text-white'
    : 'bg-orange-500 hover:bg-orange-600 text-white';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`relative w-full max-w-md mx-4 rounded-xl border ${s.card} shadow-2xl`}
      >
        <button
          onClick={onCancel}
          className={`absolute top-3 right-3 p-1 rounded-lg ${s.cardHover} ${s.text2}`}
          disabled={busy}
        >
          <X size={16} />
        </button>
        <div className="p-5 pb-3 flex items-start gap-3">
          <AlertTriangle size={28} className={`${accent} shrink-0 mt-0.5`} />
          <div>
            <h3 className={`text-[12px] font-bold ${s.text1}`}>{title}</h3>
            <p className={`mt-2 text-[12px] leading-relaxed ${s.text2} whitespace-pre-line`}>{message}</p>
          </div>
        </div>
        <div className={`flex items-center justify-end gap-2 px-5 py-3 border-t ${dark ? 'border-[#2a2b35]' : 'border-gray-200'}`}>
          <button
            onClick={onCancel}
            disabled={busy}
            className={`px-4 py-2 rounded-lg text-[12px] font-semibold ${dark ? 'bg-[#2a2b35] hover:bg-[#353749] text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-900'} disabled:opacity-50`}
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className={`px-4 py-2 rounded-lg text-[12px] font-semibold ${btnConfirm} disabled:opacity-50`}
          >
            {busy ? '처리 중...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
