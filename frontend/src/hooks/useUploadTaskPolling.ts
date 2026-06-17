import { useEffect, useRef, useState } from 'react';
import { fetchUploadTask, type UploadTaskStatus } from '../api/ownerclan';

export function useUploadTaskPolling(taskId: number | null, intervalMs = 3000) {
  const [task, setTask] = useState<UploadTaskStatus | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      return;
    }
    let cancelled = false;
    const tick = async () => {
      try {
        const t = await fetchUploadTask(taskId);
        if (cancelled) return;
        setTask(t);
        if (t.status === 'done' || t.status === 'error') {
          if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
          }
        }
      } catch {
        // 무시 — 다음 tick에서 재시도
      }
    };
    tick();
    timerRef.current = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [taskId, intervalMs]);

  return task;
}
