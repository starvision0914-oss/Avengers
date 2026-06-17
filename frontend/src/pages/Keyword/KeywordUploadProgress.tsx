import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';
import type { UploadTaskStatus } from '../../api/keyword';
import { themeStyles, fmt } from './constants';

interface Props {
  dark: boolean;
  task: UploadTaskStatus | null;
  uploadPct?: number | null;
  onClose?: () => void;
}

const STAGES = [
  { key: 'upload', label: '파일 업로드' },
  { key: 'parse', label: '파싱' },
  { key: 'save', label: 'DB 저장' },
  { key: 'sync', label: '동기화 체크' },
  { key: 'done', label: '완료' },
];

function inferStageIndex(task: UploadTaskStatus | null, uploadPct?: number | null): number {
  if (uploadPct != null && uploadPct < 100) return 0;
  if (!task) return 1;
  if (task.status === 'pending') return 1;
  if (task.status === 'running') {
    const p = task.result_data?.progress ?? 0;
    if (p < 50) return 1;
    if (p < 90) return 2;
    return 3;
  }
  if (task.status === 'done') return 4;
  if (task.status === 'error') return -1;
  return 1;
}

function useCountUp(target: number, durationMs = 600) {
  const [val, setVal] = useState(target);
  const fromRef = useRef(target);
  useEffect(() => {
    const from = fromRef.current;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(Math.round(from + (target - from) * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);
  return val;
}

export default function KeywordUploadProgress({ dark, task, uploadPct, onClose }: Props) {
  const s = themeStyles(dark);
  const idx = inferStageIndex(task, uploadPct);
  const isError = idx < 0;
  const isDone = idx >= 4;

  const inserted = useCountUp(task?.result_data?.inserted ?? 0);
  const updated = useCountUp(task?.result_data?.updated ?? 0);
  const skipped = useCountUp(task?.result_data?.skipped ?? 0);

  return (
    <div className={`rounded-xl border ${s.card} p-4 space-y-3 relative`}>
      {onClose && (isDone || isError) && (
        <button
          onClick={onClose}
          className={`absolute top-2 right-2 p-1 rounded ${s.cardHover} ${s.text2}`}
          aria-label="닫기"
        >
          <X size={14} />
        </button>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isError ? (
            <AlertCircle size={16} className="text-red-500" />
          ) : isDone ? (
            <CheckCircle2 size={16} className="text-green-500" />
          ) : (
            <Loader2 size={16} className="text-blue-500 animate-spin" />
          )}
          <span className={`text-[12px] font-bold ${s.text1}`}>
            {isError ? '업로드 오류' : isDone ? '업로드 완료' : '업로드 진행 중'}
          </span>
        </div>
        {uploadPct != null && uploadPct < 100 && !isError && (
          <span className={`text-[11px] ${s.text2}`}>전송 {uploadPct}%</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {STAGES.map((st, i) => {
          const active = !isError && i === idx;
          const done = !isError && i < idx;
          const errorStage = isError && i === 0;
          return (
            <div key={st.key} className="flex items-center gap-2 flex-1">
              <div
                className={`flex items-center justify-center w-7 h-7 rounded-full text-[10px] font-bold transition-all ${
                  errorStage ? 'bg-red-500 text-white' :
                  done ? 'bg-green-500 text-white' :
                  active ? 'bg-blue-500 text-white animate-pulse' :
                  dark ? 'bg-[#2a2b35] text-gray-500' : 'bg-gray-200 text-gray-400'
                }`}
              >
                {done ? '✓' : i + 1}
              </div>
              <span className={`text-[10px] hidden md:inline ${active ? s.text1 : s.text3}`}>{st.label}</span>
              {i < STAGES.length - 1 && (
                <div className={`flex-1 h-px ${done ? 'bg-green-500' : dark ? 'bg-[#2a2b35]' : 'bg-gray-200'}`} />
              )}
            </div>
          );
        })}
      </div>

      {isError ? (
        <div className="text-[12px] text-red-500 pt-1">{task?.result_data?.error || '알 수 없는 오류'}</div>
      ) : (
        <div className="grid grid-cols-3 gap-2 pt-1">
          <Stat label="추가됨" value={inserted} color="#16a34a" dark={dark} />
          <Stat label="업데이트" value={updated} color="#2563eb" dark={dark} />
          <Stat label="스킵" value={skipped} color="#94a3b8" dark={dark} />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color, dark }: { label: string; value: number; color: string; dark: boolean }) {
  const s = themeStyles(dark);
  return (
    <div className={`rounded-lg px-3 py-2 ${dark ? 'bg-[#0f1117]' : 'bg-gray-50'}`}>
      <div className={`text-[10px] ${s.text3}`}>{label}</div>
      <div className="text-[12px] font-bold tabular-nums" style={{ color }}>{fmt(value)}</div>
    </div>
  );
}
