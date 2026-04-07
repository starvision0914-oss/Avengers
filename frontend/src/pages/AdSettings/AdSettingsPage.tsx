import { useEffect, useState } from 'react';
import {
  getCpc2Schedule, updateCpc2Schedule,
  getAiSchedule, updateAiSchedule, createAiSchedule,
  getSellerGroups, createSellerGroup, updateSellerGroup, deleteSellerGroup,
  getCrawlerAccounts, controlCpc2, triggerCrawl, getCpc2History
} from '../../api/crawler';
import { Save, Play, Plus, Trash2, Clock, Users } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdSettingsPage() {
  const [tab, setTab] = useState('cpc2');
  const [cpc2Sched, setCpc2Sched] = useState<any>(null);
  const [aiScheds, setAiScheds] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [cpc2History, setCpc2History] = useState<any[]>([]);
  const [cpc2Form, setCpc2Form] = useState({ on_time: '08:45', off_time: '16:45' });
  const [groupForm, setGroupForm] = useState({ name: '', seller_ids: '' });
  const [showGroupForm, setShowGroupForm] = useState(false);

  const load = () => {
    getCpc2Schedule().then(d => {
      const list = Array.isArray(d) ? d : d.results || [];
      if (list[0]) { setCpc2Sched(list[0]); setCpc2Form({ on_time: list[0].on_time || '08:45', off_time: list[0].off_time || '16:45' }); }
    });
    getAiSchedule().then(d => setAiScheds(Array.isArray(d) ? d : d.results || []));
    getSellerGroups().then(d => setGroups(Array.isArray(d) ? d : d.results || []));
    getCrawlerAccounts().then(d => setAccounts(Array.isArray(d) ? d : d.results || []));
    getCpc2History().then(d => setCpc2History(Array.isArray(d) ? d : d.results || []));
  };
  useEffect(() => { load(); }, []);

  const saveCpc2 = async () => {
    if (cpc2Sched) await updateCpc2Schedule(cpc2Sched.id, cpc2Form);
    toast.success('간편광고 예약 저장');
    load();
  };

  const handleCpc2Control = async (action: string) => {
    await controlCpc2({ action, source: 'manual' });
    toast.success(`간편광고 ${action.toUpperCase()} 실행 시작`);
  };

  const addGroup = async () => {
    if (!groupForm.name) return;
    await createSellerGroup({ name: groupForm.name, seller_ids: groupForm.seller_ids.split(',').map(s => s.trim()).filter(Boolean) });
    setGroupForm({ name: '', seller_ids: '' });
    setShowGroupForm(false);
    toast.success('그룹 추가됨');
    load();
  };

  const gmAccounts = accounts.filter(a => a.platform === 'gmarket');
  const elAccounts = accounts.filter(a => a.platform === '11st');

  return (
    <div className="max-w-[1000px] mx-auto space-y-4">
      <h1 className="text-2xl font-bold">광고 설정</h1>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b flex">
          {[
            { key: 'cpc2', label: '간편광고 예약' },
            { key: 'groups', label: '집중관리 그룹' },
            { key: 'history', label: '제어 이력' },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${tab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'}`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {tab === 'cpc2' && (
            <div className="space-y-6">
              {/* 예약 설정 */}
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2"><Clock size={16} /> 간편광고 ON/OFF 예약</h3>
                <div className="flex items-center gap-4">
                  <div>
                    <label className="text-xs text-gray-500">ON 시간</label>
                    <input type="time" value={cpc2Form.on_time} onChange={e => setCpc2Form({...cpc2Form, on_time: e.target.value})} className="block border rounded px-3 py-2" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">OFF 시간</label>
                    <input type="time" value={cpc2Form.off_time} onChange={e => setCpc2Form({...cpc2Form, off_time: e.target.value})} className="block border rounded px-3 py-2" />
                  </div>
                  <button onClick={saveCpc2} className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm mt-4"><Save size={14} /> 저장</button>
                </div>
              </div>

              {/* 수동 제어 */}
              <div>
                <h3 className="font-semibold mb-3">수동 제어</h3>
                <div className="flex gap-3">
                  <button onClick={() => handleCpc2Control('on')} className="flex items-center gap-1 px-5 py-2.5 bg-green-600 text-white rounded-lg">
                    <Play size={14} /> 전체 ON
                  </button>
                  <button onClick={() => handleCpc2Control('off')} className="flex items-center gap-1 px-5 py-2.5 bg-red-600 text-white rounded-lg">
                    <Play size={14} /> 전체 OFF
                  </button>
                </div>
              </div>
            </div>
          )}

          {tab === 'groups' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2"><Users size={16} /> 집중관리 셀러 그룹</h3>
                <button onClick={() => setShowGroupForm(true)} className="flex items-center gap-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm"><Plus size={14} /> 그룹 추가</button>
              </div>

              {groups.length > 0 ? groups.map((g: any) => (
                <div key={g.id} className="border rounded-lg p-4 mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">{g.name}</h4>
                    <button onClick={async () => { await deleteSellerGroup(g.id); load(); }} className="text-red-500"><Trash2 size={14} /></button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(g.seller_ids || []).map((sid: string) => (
                      <span key={sid} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">{sid}</span>
                    ))}
                    {(!g.seller_ids || g.seller_ids.length === 0) && <span className="text-gray-400 text-sm">셀러 없음</span>}
                  </div>
                </div>
              )) : <p className="text-gray-400 text-center py-8">집중관리 그룹이 없습니다.</p>}

              <div className="mt-6 border-t pt-4">
                <h4 className="font-semibold mb-2">전체 셀러 목록</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">지마켓 ({gmAccounts.length})</p>
                    <div className="flex flex-wrap gap-1">{gmAccounts.map(a => (
                      <span key={a.id} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{a.login_id}</span>
                    ))}</div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">11번가 ({elAccounts.length})</p>
                    <div className="flex flex-wrap gap-1">{elAccounts.map(a => (
                      <span key={a.id} className="px-2 py-0.5 bg-orange-50 text-orange-700 rounded text-xs">{a.login_id}</span>
                    ))}</div>
                  </div>
                </div>
              </div>

              {showGroupForm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-white rounded-lg p-6 w-[400px]">
                    <h2 className="font-bold mb-3">새 그룹</h2>
                    <input value={groupForm.name} onChange={e => setGroupForm({...groupForm, name: e.target.value})} placeholder="그룹명 (예: 집중)" className="w-full border rounded px-3 py-2 mb-3" />
                    <textarea value={groupForm.seller_ids} onChange={e => setGroupForm({...groupForm, seller_ids: e.target.value})} placeholder="셀러 ID (쉼표 구분: starvisi, dlwodb000)" className="w-full border rounded px-3 py-2 mb-3" rows={3} />
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setShowGroupForm(false)} className="px-3 py-1.5 border rounded">취소</button>
                      <button onClick={addGroup} className="px-3 py-1.5 bg-blue-600 text-white rounded">추가</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'history' && (
            <div>
              <h3 className="font-semibold mb-3">간편광고 제어 이력</h3>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left">계정</th>
                    <th className="px-3 py-2 text-center">액션</th>
                    <th className="px-3 py-2 text-right">변경전</th>
                    <th className="px-3 py-2 text-right">변경후</th>
                    <th className="px-3 py-2 text-left">소스</th>
                    <th className="px-3 py-2 text-left">시간</th>
                  </tr>
                </thead>
                <tbody>
                  {cpc2History.length > 0 ? cpc2History.map((h: any) => (
                    <tr key={h.id} className="border-t">
                      <td className="px-3 py-2">{h.gmarket_id}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${h.action === 'on' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{h.action.toUpperCase()}</span>
                      </td>
                      <td className="px-3 py-2 text-right">{h.cpc2_before}</td>
                      <td className="px-3 py-2 text-right">{h.cpc2_after}</td>
                      <td className="px-3 py-2">{h.source}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{h.event_time ? new Date(h.event_time).toLocaleString('ko-KR') : ''}</td>
                    </tr>
                  )) : <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400">이력 없음</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
