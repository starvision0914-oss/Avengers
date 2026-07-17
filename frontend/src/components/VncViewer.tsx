import { useEffect, useRef, useState } from 'react';
// @ts-ignore - noVNC ships without bundled TS types
import RFB from '@novnc/novnc';

interface VncViewerProps {
  title: string;
  onClose: () => void;
}

export default function VncViewer({ title, onClose }: VncViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<any>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error'>('connecting');

  useEffect(() => {
    if (!containerRef.current) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/vnc-ws`;
    const rfb = new RFB(containerRef.current, url);
    rfb.scaleViewport = true;
    rfb.resizeSession = false;
    rfb.addEventListener('connect', () => setStatus('connected'));
    rfb.addEventListener('disconnect', () => setStatus('error'));
    rfbRef.current = rfb;
    return () => {
      try { rfb.disconnect(); } catch { /* noop */ }
    };
  }, []);

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{ background: '#111827', borderRadius: 10, width: '90vw', height: '85vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', borderBottom: '1px solid #374151' }}>
          <div style={{ color: '#fff', fontSize: 14, fontWeight: 600 }}>
            {title} — 크롤러 화면 (공용, 계정별로 분리된 화면 아님)
            {status === 'connecting' && <span style={{ marginLeft: 10, color: '#9ca3af', fontWeight: 400 }}>연결 중...</span>}
            {status === 'error' && <span style={{ marginLeft: 10, color: '#f87171', fontWeight: 400 }}>연결 끊김 (재시도하려면 다시 열어주세요)</span>}
          </div>
          <button onClick={onClose}
            style={{ padding: '6px 14px', background: '#374151', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
            닫기
          </button>
        </div>
        <div ref={containerRef} style={{ flex: 1, background: '#000' }} />
      </div>
    </div>
  );
}
