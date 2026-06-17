import { useEffect, useState, useCallback } from 'react';
import { getAiSummary, controlAiStream } from '../../api/gmarket';
import type { AiSummaryItem } from '../../types/cpc';

interface Props {
  onClose: () => void;
}

export default function AiManageModal({ onClose }: Props) {
  const [items, setItems] = useState<AiSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [logs, setLogs] = useState<string[]>([]);
  const [running, setRunning] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getAiSummary().then(setItems).catch(() => setItems([])).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map(i => i.id)));
  };

  const runAction = async (action: 'on' | 'off' | 'off-on') => {
    if (selected.size === 0) return;
    setRunning(true);
    setLogs([]);
    try {
      await controlAiStream(Array.from(selected), action, msg => setLogs(prev => [...prev, msg]));
      setLogs(prev => [...prev, '완료']);
      setTimeout(() => { load(); setSelected(new Set()); }, 1000);
    } catch (e) {
      setLogs(prev => [...prev, `오류: ${e}`]);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-[95vw] max-w-[700px] max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#eee]">
          <h3 className="text-[12px] font-bold text-[#333]">AI 광고 관리</h3>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] text-[12px] leading-none px-1">&times;</button>
        </div>

        <div className="flex items-center gap-2 px-4 py-2 border-b border-[#eee] bg-[#fafafa]">
          <button onClick={selectAll} className="px-3 py-1 text-[11px] border border-[#ddd] rounded hover:bg-[#eee]">
            {selected.size === items.length ? '전체 해제' : '전체 선택'}
          </button>
          <button onClick={() => runAction('on')} disabled={running || selected.size === 0}
            className="px-3 py-1 text-[11px] font-semibold bg-[#00a651] text-white rounded hover:bg-[#008c44] disabled:opacity-40">ON</button>
          <button onClick={() => runAction('off')} disabled={running || selected.size === 0}
            className="px-3 py-1 text-[11px] font-semibold bg-[#e04040] text-white rounded hover:bg-[#c03030] disabled:opacity-40">OFF</button>
          <button onClick={() => runAction('off-on')} disabled={running || selected.size === 0}
            className="px-3 py-1 text-[11px] font-semibold bg-[#e08000] text-white rounded hover:bg-[#c07000] disabled:opacity-40">OFF→ON</button>
          <span className="text-[10px] text-[#999] ml-auto">{selected.size}개 선택</span>
        </div>

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <p className="text-[12px] text-[#999] py-8 text-center">로딩중...</p>
          ) : (
            <table className="w-full text-[12px]">
              <thead className="bg-[#f7f7f7] sticky top-0">
                <tr>
                  <th className="px-2 py-1.5 w-8"></th>
                  <th className="px-2 py-1.5 text-left text-[#555] font-semibold">셀러</th>
                  <th className="px-2 py-1.5 text-center text-[#555] font-semibold">버튼</th>
                  <th className="px-2 py-1.5 text-center text-[#555] font-semibold">실제</th>
                  <th className="px-2 py-1.5 text-left text-[#555] font-semibold">사유</th>
                  <th className="px-2 py-1.5 text-right text-[#555] font-semibold">예산</th>
                  <th className="px-2 py-1.5 text-left text-[#555] font-semibold">기간</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={item.id} className={`border-b border-[#eee] cursor-pointer hover:bg-[#f5f9ff] ${i % 2 ? 'bg-[#fafafa]' : ''}`}
                    onClick={() => toggleSelect(item.id)}>
                    <td className="px-2 py-1.5 text-center">
                      <input type="checkbox" checked={selected.has(item.id)} readOnly className="w-3.5 h-3.5" />
                    </td>
                    <td className="px-2 py-1.5 font-semibold text-[#222]">{item.seller_id || item.gmarket_id}</td>
                    <td className="px-2 py-1.5 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${item.button_status === 'ON' ? 'bg-[#e8f5e9] text-[#00a651]' : 'bg-[#ffeef0] text-[#e04040]'}`}>
                        {item.button_status}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${item.actual_status === 'ON' ? 'bg-[#e8f5e9] text-[#00a651]' : 'bg-[#ffeef0] text-[#e04040]'}`}>
                        {item.actual_status}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-[#666] truncate max-w-[120px]" title={item.actual_reason}>{item.actual_reason}</td>
                    <td className="px-2 py-1.5 text-right text-[#333]">{item.daily_budget}</td>
                    <td className="px-2 py-1.5 text-[#999] text-[10px]">{item.start_date || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {logs.length > 0 && (
          <div className="border-t border-[#eee] px-4 py-2 max-h-[120px] overflow-y-auto bg-[#1a1a2e] text-[#ddd] text-[11px] font-mono">
            {logs.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}
      </div>
    </div>
  );
}
