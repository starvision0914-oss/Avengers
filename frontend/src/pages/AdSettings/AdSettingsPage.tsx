import { useEffect, useState } from 'react';
import {
  getCpc2Schedule, updateCpc2Schedule,
  getAiSchedule, updateAiSchedule, createAiSchedule,
  controlCpc2, getCpc2History, getGmarketMyAccounts, controlAi, getAiHistory, stopGmarketControl, getGmarketControlStatus,
  getSt11StrategyAccounts, getSt11StrategyCampaigns, fetchSt11StrategyCampaigns, controlSt11Strategy, getSt11StrategyLogs, getSt11StrategyRuns,
  getSt11StrategySchedule, saveSt11StrategySchedule
} from '../../api/crawler';
import { Save, Play, Clock, Zap, Target, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

const WEEKDAYS = [{ v: 1, n: '월' }, { v: 2, n: '화' }, { v: 3, n: '수' }, { v: 4, n: '목' }, { v: 5, n: '금' }, { v: 6, n: '토' }, { v: 7, n: '일' }];

export default function AdSettingsPage() {
  const [tab, setTab] = useState('cpc2');
  const [cpc2Sched, setCpc2Sched] = useState<any>(null);
  const [aiScheds, setAiScheds] = useState<any[]>([]);
  const [cpc2History, setCpc2History] = useState<any[]>([]);
  const [cpc2Form, setCpc2Form] = useState<any>({ on_time: '08:30', off_time: '16:00', weekdays: [1, 2, 3, 4, 5], off_weekdays: [1, 2, 3, 4, 5], include_cpc1: false });
  const [gmAccounts, setGmAccounts] = useState<any[]>([]);          // 지마켓 계정 목록(선택용)
  const [cpc2Accounts, setCpc2Accounts] = useState<string[]>([]);   // 간편광고 제어 대상 선택 계정
  const [cpc2Running, setCpc2Running] = useState(false);            // 실행 중(진행사항 폴링)
  const [aiSched, setAiSched] = useState<any>(null);               // 지마켓 AI 예약(싱글톤)
  const [aiForm, setAiForm] = useState<any>({ on_time: '20:00', off_time: '16:00', weekdays: [7, 1, 2, 3, 4], off_weekdays: [1, 2, 3, 4, 5] });
  const [aiAccounts, setAiAccounts] = useState<string[]>([]);      // AI 제어 대상 선택 계정
  const [aiRunning, setAiRunning] = useState(false);
  const [aiHistory, setAiHistory] = useState<any[]>([]);          // AI 제어 진행사항/이력
  const [ctrlStatus, setCtrlStatus] = useState<any>(null);        // 예약·실행 현황(상단 배너)

  // ── 11번가 전략설정 ──
  const [elOrdered, setElOrdered] = useState<any[]>([]);   // 등급순 정렬된 11번가 계정
  const [stratAccounts, setStratAccounts] = useState<string[]>([]);
  const [campOptions, setCampOptions] = useState<string[]>([]);
  const [stratCamps, setStratCamps] = useState<string[]>([]);
  const [campLoading, setCampLoading] = useState(false);
  const [onStart, setOnStart] = useState(8);
  const [onEnd, setOnEnd] = useState(16);
  const [stratWeekdays, setStratWeekdays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [stratLogs, setStratLogs] = useState<any[]>([]);
  const [stratRunning, setStratRunning] = useState(false);
  const [stratRunId, setStratRunId] = useState<string>('');
  const [stratRuns, setStratRuns] = useState<any[]>([]);   // 실행 내역 목록
  const [stratEnabled, setStratEnabled] = useState(false); // cron 자동 재적용
  const [stratSched, setStratSched] = useState<any>(null); // 저장된 전략(메타)
  const [stratSaving, setStratSaving] = useState(false);

  const load = () => {
    getCpc2Schedule().then(d => {
      const list = Array.isArray(d) ? d : d.results || [];
      if (list[0]) { setCpc2Sched(list[0]); setCpc2Form({ on_time: list[0].on_time || '08:30', off_time: list[0].off_time || '16:00', weekdays: list[0].weekdays?.length ? list[0].weekdays : [1, 2, 3, 4, 5], off_weekdays: list[0].off_weekdays?.length ? list[0].off_weekdays : [1, 2, 3, 4, 5], include_cpc1: !!list[0].include_cpc1 }); setCpc2Accounts(list[0].selected_accounts || []); }
    });
    getAiSchedule().then(d => {
      const list = Array.isArray(d) ? d : d.results || [];
      setAiScheds(list);
      const gm = list.find((s: any) => s.platform === 'gmarket');
      if (gm) setAiSched(gm);
      if (gm) { setAiForm({ on_time: gm.on_time || '20:00', off_time: gm.off_time || '16:00', weekdays: gm.weekdays?.length ? gm.weekdays : [7, 1, 2, 3, 4], off_weekdays: gm.off_weekdays?.length ? gm.off_weekdays : [1, 2, 3, 4, 5] }); setAiAccounts(gm.selected_accounts || []); }
    });
    getCpc2History().then(d => setCpc2History(Array.isArray(d) ? d : d.results || []));
    getAiHistory().then(d => setAiHistory(Array.isArray(d) ? d : d.results || [])).catch(() => {});
    getGmarketMyAccounts().then(d => setGmAccounts(d.accounts || [])).catch(() => {});
    getSt11StrategyAccounts().then(d => setElOrdered(d.accounts || [])).catch(() => {});
    getSt11StrategySchedule().then(d => {
      const s = d.schedule;
      if (!s) return;
      // 공통 시간대 프리셋만 복원(계정/캠페인은 매번 직접 선택)
      setStratSched(s);
      setOnStart(s.on_start ?? 8);
      setOnEnd(s.on_end ?? 16);
      setStratWeekdays(s.weekdays?.length ? s.weekdays : [1, 2, 3, 4, 5]);
      setStratEnabled(!!s.enabled);
    }).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  // 예약·실행 현황 상시 폴링(상단 배너) — 겹침/중복 확인
  useEffect(() => {
    const f = () => getGmarketControlStatus().then(setCtrlStatus).catch(() => {});
    f();
    const t = setInterval(f, 4000);
    return () => clearInterval(t);
  }, []);

  // 간편 탭 보는 동안 진행사항(이력) 실시간 폴링 — 예약/크론 실행도 실시간 표시
  useEffect(() => {
    if (tab !== 'cpc2') return;
    const t = setInterval(() => {
      getCpc2History().then(d => setCpc2History(Array.isArray(d) ? d : d.results || [])).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [tab]);

  // AI 탭 보는 동안 진행사항 실시간 폴링
  useEffect(() => {
    if (tab !== 'ai') return;
    const t = setInterval(() => {
      getAiHistory().then(d => setAiHistory(Array.isArray(d) ? d : d.results || [])).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [tab]);

  const saveCpc2 = async () => {
    if (!cpc2Accounts.length && !confirm('계정이 선택되지 않았습니다.\n계정을 선택해야 예약(크론)이 등록됩니다.\n그래도 저장할까요?')) return;
    const payload = { ...cpc2Form, selected_accounts: cpc2Accounts };
    if (cpc2Sched) await updateCpc2Schedule(cpc2Sched.id, payload);
    toast.success(`간편광고 예약 저장 (계정 ${cpc2Accounts.length}개)`);
    load();
  };

  const toggleCpc2Weekday = (v: number) =>
    setCpc2Form((f: any) => ({ ...f, weekdays: f.weekdays.includes(v) ? f.weekdays.filter((x: number) => x !== v) : [...f.weekdays, v].sort() }));
  const toggleCpc2OffWeekday = (v: number) =>
    setCpc2Form((f: any) => ({ ...f, off_weekdays: (f.off_weekdays || []).includes(v) ? f.off_weekdays.filter((x: number) => x !== v) : [...(f.off_weekdays || []), v].sort() }));

  const toggleCpc2Account = (id: string) =>
    setCpc2Accounts(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  const handleCpc2Control = async (action: string) => {
    const accts = cpc2Accounts.length ? cpc2Accounts : undefined;
    const label = accts ? `선택 ${accts.length}개 계정` : '전체 계정';
    const withGen = cpc2Form.include_cpc1 ? ' + 일반광고' : '';
    if (!confirm(`간편광고${withGen} ${action.toUpperCase()}\n대상: ${label}\n진행할까요?`)) return;
    await controlCpc2({ action, accounts: accts, source: 'manual', include_cpc1: cpc2Form.include_cpc1 });
    toast.success(`간편광고 ${action.toUpperCase()} 실행 시작 (${label})`);
    // 진행사항 폴링: 이력(계정별 ON/OFF 결과)을 주기적으로 갱신
    setCpc2Running(true);
    let n = 0;
    const timer = setInterval(async () => {
      try {
        const d = await getCpc2History();
        setCpc2History(Array.isArray(d) ? d : d.results || []);
      } catch { /* ignore */ }
      if (++n >= 24) { clearInterval(timer); setCpc2Running(false); }   // 최대 2분 폴링
    }, 5000);
  };

  const saveAi = async () => {
    if (!aiAccounts.length && !confirm('계정이 선택되지 않았습니다.\n계정을 선택해야 예약(크론)이 등록됩니다.\n그래도 저장할까요?')) return;
    const payload = { ...aiForm, platform: 'gmarket', selected_accounts: aiAccounts };
    if (aiSched) await updateAiSchedule(aiSched.id, payload);
    else await createAiSchedule(payload);
    toast.success(`AI 예약 저장 (계정 ${aiAccounts.length}개)`);
    load();
  };
  const toggleAiWeekday = (v: number) =>
    setAiForm((f: any) => ({ ...f, weekdays: f.weekdays.includes(v) ? f.weekdays.filter((x: number) => x !== v) : [...f.weekdays, v].sort() }));
  const toggleAiOffWeekday = (v: number) =>
    setAiForm((f: any) => ({ ...f, off_weekdays: (f.off_weekdays || []).includes(v) ? f.off_weekdays.filter((x: number) => x !== v) : [...(f.off_weekdays || []), v].sort() }));
  const toggleAiAccount = (id: string) =>
    setAiAccounts(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  const handleStopControl = async () => {
    if (!confirm('실행 중인 지마켓 광고제어를 강제 중지할까요?\n(현재 계정 처리 후 멈춥니다 — 최대 40초)')) return;
    await stopGmarketControl();
    toast('🛑 강제중지 요청 — 곧 멈춥니다', { icon: '🛑' });
    setCpc2Running(false); setAiRunning(false);
  };

  const handleAiControl = async (action: string) => {
    const accts = aiAccounts.length ? aiAccounts : undefined;
    const label = accts ? `선택 ${accts.length}개 계정` : '전체 계정';
    if (!confirm(`AI 광고 ${action.toUpperCase()}\n대상: ${label}\n진행할까요?`)) return;
    await controlAi({ action, accounts: accts, source: 'manual' });
    toast.success(`AI 광고 ${action.toUpperCase()} 실행 시작 (${label})`);
    // 진행사항 폴링: AI 이력(계정별 ON/OFF 결과)을 주기적으로 갱신
    setAiRunning(true);
    let n = 0;
    const timer = setInterval(async () => {
      try {
        const d = await getAiHistory();
        setAiHistory(Array.isArray(d) ? d : d.results || []);
      } catch { /* ignore */ }
      if (++n >= 36) { clearInterval(timer); setAiRunning(false); }   // 최대 3분 폴링
    }, 5000);
  };


  // 캠페인 이름 불러오기: 먼저 DB(즉시), 없으면 대표계정 1개로 광고센터 실시간 조회(백그라운드+폴링).
  // ※ 캠페인 이름은 계정 공통이므로 대표 1개만 로그인(동시 로그인=IP차단 위험).
  const loadCampaigns = async () => {
    if (stratAccounts.length === 0) { toast.error('계정을 먼저 선택하세요.'); return; }
    setCampLoading(true);
    try {
      const rep = stratAccounts[0];
      const db = await getSt11StrategyCampaigns(rep);
      if ((db.campaigns || []).length > 0) {
        setCampOptions(db.campaigns); toast.success(`캠페인 ${db.campaigns.length}개 (저장됨)`); setCampLoading(false); return;
      }
      // 실시간 조회(로그인 필요, ~1분)
      toast(`'${rep}' 광고센터에서 캠페인 조회 중… (~1분)`, { icon: '⏳' });
      const r = await fetchSt11StrategyCampaigns(rep);
      setStratRunId(r.run_id); setStratRunning(true); setStratLogs([]);
      const poll = setInterval(async () => {
        const d = await getSt11StrategyLogs(r.run_id);
        setStratLogs(d.logs || []);
        if (!d.running) {
          clearInterval(poll); setStratRunning(false); setCampLoading(false);
          const names = (d.logs || []).filter((l: any) => l.status === 'CAMP').map((l: any) => l.detail);
          setCampOptions(names);
          if (names.length === 0) toast('캠페인을 못 찾았습니다. 이름을 직접 입력하세요.', { icon: 'ℹ️' });
          else toast.success(`캠페인 ${names.length}개 불러옴`);
        }
      }, 2000);
    } catch (e) { setCampLoading(false); toast.error('캠페인 조회 실패'); }
  };

  const toggleStratAccount = (eid: string) =>
    setStratAccounts(p => p.includes(eid) ? p.filter(x => x !== eid) : [...p, eid]);
  const toggleStratCamp = (c: string) =>
    setStratCamps(p => p.includes(c) ? p.filter(x => x !== c) : [...p, c]);
  const toggleWeekday = (v: number) =>
    setStratWeekdays(p => p.includes(v) ? p.filter(x => x !== v) : [...p, v].sort());

  const runStrategy = async (execute: boolean) => {
    if (stratAccounts.length === 0) { toast.error('계정을 선택하세요.'); return; }
    if (stratCamps.length === 0) { toast.error('캠페인을 선택하세요.'); return; }
    if (stratWeekdays.length === 0) { toast.error('요일을 하나 이상 선택하세요.'); return; }
    if (execute && !confirm(`실제 적용합니다.\n계정 ${stratAccounts.length}개 / 캠페인 ${stratCamps.length}개\n${onStart}~${onEnd}시 ON, 그 외·미선택요일 OFF.\n진행할까요?`)) return;
    const r = await controlSt11Strategy({
      accounts: stratAccounts, campaigns: stratCamps,
      on_start: onStart, on_end: onEnd, weekdays: stratWeekdays, execute,
    });
    setStratRunId(r.run_id); setStratRunning(true); setStratLogs([]);
    toast.success(`${r.mode} 시작 (${r.run_id})`);
  };

  // 공통 시간대 저장 — 계정/캠페인과 무관하게 ON시각·요일만 공통 프리셋으로 보관.
  const saveStrategy = async (enabled?: boolean) => {
    if (stratWeekdays.length === 0) { toast.error('요일을 하나 이상 선택하세요.'); return; }
    setStratSaving(true);
    try {
      const next = enabled === undefined ? stratEnabled : enabled;
      const r = await saveSt11StrategySchedule({
        on_start: onStart, on_end: onEnd, weekdays: stratWeekdays, enabled: next,
      });
      setStratSched(r.schedule);
      setStratEnabled(!!r.schedule.enabled);
      toast.success(`시간대 저장됨 (${stratWeekdays.map(v => WEEKDAYS.find(w => w.v === v)?.n).join('')} ${onStart}~${onEnd}시)`);
    } catch { toast.error('저장 실패'); }
    finally { setStratSaving(false); }
  };

  // 실행 중이면 로그 폴링
  useEffect(() => {
    if (!stratRunId) return;
    const t = setInterval(async () => {
      const d = await getSt11StrategyLogs(stratRunId);
      setStratLogs(d.logs || []);
      setStratRunning(d.running);
      if (!d.running) clearInterval(t);
    }, 2000);
    return () => clearInterval(t);
  }, [stratRunId]);

  // 전략 탭에 있는 동안 실행 내역 목록 폴링(다른 세션·CLI 실행도 보임)
  useEffect(() => {
    if (tab !== 'st11strategy') return;
    const fetchRuns = () => getSt11StrategyRuns().then(d => setStratRuns(d.runs || [])).catch(() => {});
    fetchRuns();
    const t = setInterval(fetchRuns, 3000);
    return () => clearInterval(t);
  }, [tab]);

  return (
    <div className="max-w-[1000px] mx-auto space-y-4">
      <h1 className="text-2xl font-bold">광고 설정</h1>

      {/* 예약·실행 현황 배너 */}
      {ctrlStatus && (
        <div className={`rounded-lg border p-3 text-sm ${ctrlStatus.running ? 'bg-orange-50 border-orange-300' : 'bg-green-50 border-green-200'}`}>
          <div className="flex items-center gap-2 font-semibold mb-1.5">
            {ctrlStatus.running
              ? <span className="flex items-center gap-1 text-orange-700"><RefreshCw size={14} className="animate-spin" /> 실행 중: {ctrlStatus.running.name} {ctrlStatus.running.since && `(${ctrlStatus.running.since} 시작)`}</span>
              : <span className="text-green-700">🟢 실행 중 아님 (지금 실행해도 안전)</span>}
            {ctrlStatus.proc_count > 1 && <span className="text-red-600 font-bold">· ⚠️ 대기/중복 {ctrlStatus.proc_count}건</span>}
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-gray-600">
            {ctrlStatus.cpc2 && (
              <span>🟦 간편: ON <b>{ctrlStatus.cpc2.on_days} {ctrlStatus.cpc2.on_time}</b> · OFF <b>{ctrlStatus.cpc2.off_days} {ctrlStatus.cpc2.off_time}</b> · 계정 {ctrlStatus.cpc2.accounts}{ctrlStatus.cpc2.include_cpc1 && ' · 일반포함'}</span>
            )}
            {ctrlStatus.ai && (
              <span>🟪 AI: ON <b>{ctrlStatus.ai.on_days} {ctrlStatus.ai.on_time}</b> · OFF <b>{ctrlStatus.ai.off_days} {ctrlStatus.ai.off_time}</b> · 계정 {ctrlStatus.ai.accounts}</span>
            )}
          </div>
          {ctrlStatus.proc_count > 1 && <p className="text-[11px] text-red-500 mt-1">※ 중복 실행이 큐에 쌓여 있습니다. 새로 실행하지 말고 끝날 때까지 기다리거나 강제 중지하세요.</p>}
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        <div className="border-b flex">
          {[
            { key: 'cpc2', label: '간편광고 제어' },
            { key: 'ai', label: 'AI 광고 제어' },
            { key: 'st11strategy', label: '11번가 전략설정' },
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
                <div className="space-y-3">
                  {/* ON 설정 */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="px-2 py-0.5 rounded bg-green-100 text-green-700 text-xs font-bold w-12 text-center">ON</span>
                    <input type="time" value={cpc2Form.on_time} onChange={e => setCpc2Form({...cpc2Form, on_time: e.target.value})} className="border rounded px-3 py-2" />
                    <div className="flex gap-1">
                      {WEEKDAYS.map(w => (
                        <button key={w.v} onClick={() => toggleCpc2Weekday(w.v)}
                          className={`w-8 h-9 rounded text-xs font-medium ${cpc2Form.weekdays?.includes(w.v) ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-500'}`}>{w.n}</button>
                      ))}
                    </div>
                  </div>
                  {/* OFF 설정 */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 text-xs font-bold w-12 text-center">OFF</span>
                    <input type="time" value={cpc2Form.off_time} onChange={e => setCpc2Form({...cpc2Form, off_time: e.target.value})} className="border rounded px-3 py-2" />
                    <div className="flex gap-1">
                      {WEEKDAYS.map(w => (
                        <button key={w.v} onClick={() => toggleCpc2OffWeekday(w.v)}
                          className={`w-8 h-9 rounded text-xs font-medium ${cpc2Form.off_weekdays?.includes(w.v) ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-500'}`}>{w.n}</button>
                      ))}
                    </div>
                    <button onClick={saveCpc2} className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm"><Save size={14} /> 저장</button>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  → <b className="text-green-600">{(cpc2Form.weekdays||[]).map((v:number)=>WEEKDAYS.find(w=>w.v===v)?.n).join('')||'매일'}</b> {cpc2Form.on_time} ON ·
                  <b className="text-red-500"> {(cpc2Form.off_weekdays||[]).map((v:number)=>WEEKDAYS.find(w=>w.v===v)?.n).join('')||'매일'}</b> {cpc2Form.off_time} OFF (ON·OFF 요일/시간 독립 설정)
                </p>
                <label className="flex items-center gap-2 mt-3 text-sm cursor-pointer select-none">
                  <input type="checkbox" checked={!!cpc2Form.include_cpc1}
                    onChange={e => setCpc2Form({ ...cpc2Form, include_cpc1: e.target.checked })} />
                  <span><b>일반광고(일반그룹)도 함께</b> ON/OFF — 한 로그인으로 간편+일반 같이 제어 (예약·수동 모두 적용)</span>
                </label>
              </div>

              {/* 계정 선택 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-sm">계정 선택 ({cpc2Accounts.length}/{gmAccounts.length}) <span className="text-xs text-gray-400 font-normal">— 수동: 미선택=전체 / 예약: 계정 선택 필수(0개면 예약 안 됨)</span></h3>
                  <button onClick={() => setCpc2Accounts(cpc2Accounts.length === gmAccounts.length ? [] : gmAccounts.map((a: any) => a.login_id))}
                    className="text-xs text-blue-600">{cpc2Accounts.length === gmAccounts.length ? '전체해제' : '전체선택'}</button>
                </div>
                <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto border rounded p-2">
                  {gmAccounts.map((a: any) => {
                    const sel = cpc2Accounts.includes(a.login_id);
                    return (
                      <button key={a.login_id} onClick={() => toggleCpc2Account(a.login_id)}
                        className={`px-2 py-1 rounded text-xs border ${sel ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-gray-600 border-gray-200'}`}>
                        {a.login_id}{a.seller_name ? ` (${a.seller_name})` : ''}
                      </button>
                    );
                  })}
                  {gmAccounts.length === 0 && <span className="text-xs text-gray-400 px-1">계정 로딩 중…</span>}
                </div>
              </div>

              {/* 수동 제어 */}
              <div>
                <h3 className="font-semibold mb-3">수동 제어 <span className="text-xs text-gray-400 font-normal">— {cpc2Accounts.length ? `선택 ${cpc2Accounts.length}개` : '전체'} 계정 대상</span></h3>
                <div className="flex items-center gap-3">
                  <button onClick={() => handleCpc2Control('on')} className="flex items-center gap-1 px-5 py-2.5 bg-green-600 text-white rounded-lg">
                    <Play size={14} /> {cpc2Accounts.length ? '선택' : '전체'} ON
                  </button>
                  <button onClick={() => handleCpc2Control('off')} className="flex items-center gap-1 px-5 py-2.5 bg-red-600 text-white rounded-lg">
                    <Play size={14} /> {cpc2Accounts.length ? '선택' : '전체'} OFF
                  </button>
                  <button onClick={handleStopControl} className="flex items-center gap-1 px-5 py-2.5 bg-gray-800 text-white rounded-lg hover:bg-black">
                    🛑 강제 중지
                  </button>
                  {cpc2Running && <span className="flex items-center gap-1 text-sm text-orange-600"><RefreshCw size={14} className="animate-spin" /> 진행 중…</span>}
                </div>
              </div>

              {/* 진행사항 / 이력 */}
              <div>
                <h3 className="font-semibold mb-2">진행사항 <span className="text-xs text-gray-400 font-normal">(계정별 ON/OFF 결과)</span></h3>
                <div className="border rounded max-h-56 overflow-y-auto text-xs">
                  <table className="w-full">
                    <thead className="bg-gray-50 sticky top-0"><tr className="text-gray-500">
                      <th className="text-left px-2 py-1">시각</th><th className="text-left px-2 py-1">계정</th>
                      <th className="text-left px-2 py-1">동작</th><th className="text-right px-2 py-1">전→후</th><th className="text-left px-2 py-1">출처</th>
                    </tr></thead>
                    <tbody>
                      {cpc2History.slice(0, 50).map((h: any, i: number) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-1">{h.event_time ? new Date(h.event_time).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}</td>
                          <td className="px-2 py-1">{h.gmarket_id}</td>
                          <td className={`px-2 py-1 font-semibold ${h.action === 'on' ? 'text-green-600' : 'text-red-600'}`}>{(h.action || '').toUpperCase()}</td>
                          <td className="px-2 py-1 text-right">{h.cpc2_before}→{h.cpc2_after}</td>
                          <td className="px-2 py-1 text-gray-400">{h.source}</td>
                        </tr>
                      ))}
                      {cpc2History.length === 0 && <tr><td colSpan={5} className="px-2 py-3 text-center text-gray-400">이력 없음</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {tab === 'st11strategy' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-1 flex items-center gap-2"><Target size={16} /> 11번가 광고 그룹 전략설정 (노출 스케줄)</h3>
                <p className="text-sm text-gray-500">계정 선택 → 캠페인 불러오기·선택 → 시간·요일 설정 → 순서대로 광고그룹('전체-') 스케줄을 일괄 적용합니다. <b>지정 시간·요일만 ON, 나머지·미선택 요일은 OFF.</b></p>
              </div>

              {/* 1. 계정 선택 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-sm">① 계정 선택 ({stratAccounts.length}/{elOrdered.length})</h4>
                  <button onClick={() => setStratAccounts(stratAccounts.length === elOrdered.length ? [] : elOrdered.map(a => a.login_id))}
                    className="text-xs text-blue-600">{stratAccounts.length === elOrdered.length ? '전체해제' : '전체선택'}</button>
                </div>
                <p className="text-[11px] text-gray-400 mb-1">표시순서: 1등급 → 2등급 → 3등급 → 4등급 → 광고이력 → 나머지</p>
                <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto border rounded p-2">
                  {elOrdered.map(a => {
                    const sel = stratAccounts.includes(a.login_id);
                    const badge = a.grade && a.grade >= 1 && a.grade <= 4 ? `${a.grade}` : (a.bucket === '광고이력' ? '광' : '·');
                    return (
                      <button key={a.login_id} onClick={() => toggleStratAccount(a.login_id)}
                        className={`px-2 py-1 rounded text-xs border flex items-center gap-1 ${sel ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-gray-600 border-gray-200'}`}>
                        <span className={`inline-flex items-center justify-center w-4 h-4 rounded text-[9px] font-bold ${sel ? 'bg-white/30' : a.bucket === '광고이력' ? 'bg-blue-100 text-blue-700' : a.grade >= 1 && a.grade <= 4 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'}`}>{badge}</span>
                        {a.login_id}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 2. 캠페인 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-sm">② 캠페인 선택 ({stratCamps.length}개 선택)</h4>
                  <button onClick={loadCampaigns} disabled={campLoading}
                    className="flex items-center gap-1 text-xs px-2 py-1 bg-blue-600 text-white rounded disabled:opacity-50">
                    <RefreshCw size={12} className={campLoading ? 'animate-spin' : ''} /> 캠페인 불러오기
                  </button>
                </div>
                {campOptions.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto border rounded p-2">
                    {campOptions.map(c => (
                      <button key={c} onClick={() => toggleStratCamp(c)}
                        className={`px-2 py-1 rounded text-xs border ${stratCamps.includes(c) ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200'}`}>
                        {c}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="flex gap-2 items-center">
                    <input placeholder="캠페인 이름 직접 입력 (예: 자동_캠페인)" className="flex-1 border rounded px-3 py-2 text-sm"
                      onKeyDown={(e: any) => { if (e.key === 'Enter' && e.target.value.trim()) { toggleStratCamp(e.target.value.trim()); e.target.value=''; } }} />
                    <span className="text-xs text-gray-400">Enter로 추가</span>
                  </div>
                )}
                {stratCamps.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {stratCamps.map(c => (
                      <span key={c} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs cursor-pointer" onClick={() => toggleStratCamp(c)}>{c} ✕</span>
                    ))}
                  </div>
                )}
              </div>

              {/* 3. 스케줄 */}
              <div>
                <h4 className="font-semibold text-sm mb-2">③ 노출 시간·요일 설정</h4>
                <div className="flex flex-wrap items-end gap-4">
                  <div>
                    <label className="text-xs text-gray-500 block">ON 시작</label>
                    <select value={onStart} onChange={e => setOnStart(+e.target.value)} className="border rounded px-3 py-2 text-sm">
                      {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{i}시</option>)}
                    </select>
                  </div>
                  <span className="pb-2">~</span>
                  <div>
                    <label className="text-xs text-gray-500 block">ON 종료</label>
                    <select value={onEnd} onChange={e => setOnEnd(+e.target.value)} className="border rounded px-3 py-2 text-sm">
                      {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{i}시</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">ON 요일</label>
                    <div className="flex gap-1">
                      {WEEKDAYS.map(w => (
                        <button key={w.v} onClick={() => toggleWeekday(w.v)}
                          className={`w-9 h-9 rounded text-xs font-medium border ${stratWeekdays.includes(w.v) ? (w.v >= 6 ? 'bg-red-500 text-white border-red-500' : 'bg-green-600 text-white border-green-600') : 'bg-white text-gray-400 border-gray-200'}`}>
                          {w.n}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">→ <b>{stratWeekdays.map(v => WEEKDAYS.find(w => w.v === v)?.n).join('')}</b> 요일 <b>{onStart}시~{onEnd}시</b>만 광고 ON, 그 외 시간·요일은 OFF</p>
              </div>

              {/* 4. 공통 시간대 저장 */}
              <div className="border-t pt-4">
                <div className="flex items-center gap-3 flex-wrap">
                  <button onClick={() => saveStrategy()} disabled={stratSaving}
                    className="flex items-center gap-1 px-5 py-2.5 bg-blue-600 text-white rounded-lg disabled:opacity-50">
                    <Save size={14} /> {stratSaving ? '저장 중…' : '공통 시간대 저장'}
                  </button>
                  <span className="text-xs text-gray-400">계정과 무관하게 ON 시각·요일을 공통 프리셋으로 저장 (페이지 열면 자동 복원)</span>
                </div>
                {stratSched && (
                  <p className="text-xs text-gray-500 mt-2">
                    저장된 공통 시간대: <b className="text-green-600">{(stratSched.weekdays?.length ? stratSched.weekdays : [1,2,3,4,5]).map((v:number) => WEEKDAYS.find(w => w.v === v)?.n).join('')}</b> 요일 <b>{stratSched.on_start}~{stratSched.on_end}시</b> ON
                    {' '}(수정 {stratSched.updated_at})
                  </p>
                )}
              </div>

              {/* 5. 실행 */}
              <div className="flex gap-3 border-t pt-4">
                <button onClick={() => runStrategy(false)} disabled={stratRunning}
                  className="flex items-center gap-1 px-5 py-2.5 bg-gray-700 text-white rounded-lg disabled:opacity-50">
                  <Play size={14} /> 미리보기(드라이런)
                </button>
                <button onClick={() => runStrategy(true)} disabled={stratRunning}
                  className="flex items-center gap-1 px-5 py-2.5 bg-orange-600 text-white rounded-lg disabled:opacity-50">
                  <Play size={14} /> 실제 적용
                </button>
                {stratRunning && <span className="flex items-center gap-1 text-sm text-orange-600"><RefreshCw size={14} className="animate-spin" /> 실행 중…</span>}
              </div>

              {/* 진행 내역 목록 */}
              <div>
                <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                  진행 내역
                  {stratRuns.some(r => r.running) && <span className="flex items-center gap-1 text-orange-600 text-xs"><RefreshCw size={12} className="animate-spin" /> 실행 중</span>}
                </h4>
                {stratRuns.length > 0 ? (
                  <div className="border rounded-lg divide-y max-h-56 overflow-y-auto text-xs">
                    {stratRuns.map(r => {
                      const label = r.mode === '실제적용' ? '전략설정' : '미리보기';
                      const acct = (r.accounts || []).join(', ') || '-';
                      return (
                      <div key={r.run_id} onClick={() => setStratRunId(r.run_id)}
                        className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 ${stratRunId === r.run_id ? 'bg-blue-50' : ''}`}>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${r.mode === '실제적용' ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-600'}`}>{r.mode}</span>
                        <span className="text-gray-800 font-medium">
                          {acct} {label} {r.running
                            ? <span className="text-orange-600 inline-flex items-center gap-1"><RefreshCw size={11} className="animate-spin" />진행중</span>
                            : <span className="text-green-600">완료</span>}
                        </span>
                        <span className="text-gray-400 truncate max-w-[150px]">{(r.campaigns || []).join(', ')}</span>
                        <span className="ml-auto">
                          <span className="text-green-600">성공 {r.applied}</span>
                          {' · '}
                          {r.error > 0
                            ? <b className="text-red-500">실패 {r.error}번</b>
                            : <span className="text-gray-400">실패 0</span>}
                          {r.skip > 0 && <span className="text-gray-400"> · 스킵 {r.skip}</span>}
                        </span>
                        <span className="text-gray-400 w-[110px] text-right">{r.started}</span>
                      </div>
                      );
                    })}
                  </div>
                ) : <p className="text-gray-400 text-sm py-3">아직 실행 내역이 없습니다.</p>}
                <p className="text-[11px] text-gray-400 mt-1">행을 클릭하면 아래에 상세 로그가 표시됩니다. (3초마다 자동 새로고침)</p>
              </div>

              {/* 상세 로그 */}
              {stratLogs.length > 0 && (
                <div className="border rounded-lg bg-gray-900 text-gray-100 p-3 max-h-72 overflow-y-auto font-mono text-xs">
                  {stratLogs.map(l => (
                    <div key={l.id} className={l.status === 'ERROR' ? 'text-red-400' : l.status === 'APPLIED' ? 'text-green-400' : l.status === 'SKIP' ? 'text-yellow-300' : 'text-gray-300'}>
                      {l.at} [{l.status}] {l.eid} {l.campaign} {l.group} {l.detail}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === 'ai' && (
            <div className="space-y-6">
              {/* 예약 설정 (익일 자동 인식) */}
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2"><Clock size={16} /> AI 광고 ON/OFF 예약</h3>
                <div className="space-y-3">
                  {/* ON 설정 */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="px-2 py-0.5 rounded bg-green-100 text-green-700 text-xs font-bold w-12 text-center">ON</span>
                    <input type="time" value={aiForm.on_time} onChange={e => setAiForm({ ...aiForm, on_time: e.target.value })} className="border rounded px-3 py-2" />
                    <div className="flex gap-1">
                      {WEEKDAYS.map(w => (
                        <button key={w.v} onClick={() => toggleAiWeekday(w.v)}
                          className={`w-8 h-9 rounded text-xs font-medium ${aiForm.weekdays?.includes(w.v) ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-500'}`}>{w.n}</button>
                      ))}
                    </div>
                  </div>
                  {/* OFF 설정 */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 text-xs font-bold w-12 text-center">OFF</span>
                    <input type="time" value={aiForm.off_time} onChange={e => setAiForm({ ...aiForm, off_time: e.target.value })} className="border rounded px-3 py-2" />
                    <div className="flex gap-1">
                      {WEEKDAYS.map(w => (
                        <button key={w.v} onClick={() => toggleAiOffWeekday(w.v)}
                          className={`w-8 h-9 rounded text-xs font-medium ${aiForm.off_weekdays?.includes(w.v) ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-500'}`}>{w.n}</button>
                      ))}
                    </div>
                    <button onClick={saveAi} className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm"><Save size={14} /> 저장</button>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  → <b className="text-green-600">{(aiForm.weekdays||[]).map((v:number)=>WEEKDAYS.find(w=>w.v===v)?.n).join('')||'매일'}</b> {aiForm.on_time} ON ·
                  <b className="text-red-500"> {(aiForm.off_weekdays||[]).map((v:number)=>WEEKDAYS.find(w=>w.v===v)?.n).join('')||'매일'}</b> {aiForm.off_time} OFF
                  <br/>ON·OFF 요일·시간을 따로 지정합니다 (예: ON 일·월·화·수·목 20:00 / OFF 월·화·수·목·금 16:00 → 금요일 저녁은 안 켜짐)
                </p>
              </div>

              {/* 계정 선택 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-sm">계정 선택 ({aiAccounts.length}/{gmAccounts.length}) <span className="text-xs text-gray-400 font-normal">— 수동: 미선택=전체(서브 포함) / 예약: 계정 선택 필수(0개면 예약 안 됨)</span></h3>
                  <button onClick={() => setAiAccounts(aiAccounts.length === gmAccounts.length ? [] : gmAccounts.map((a: any) => a.login_id))}
                    className="text-xs text-blue-600">{aiAccounts.length === gmAccounts.length ? '전체해제' : '전체선택'}</button>
                </div>
                <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto border rounded p-2">
                  {gmAccounts.map((a: any) => {
                    const sel = aiAccounts.includes(a.login_id);
                    return (
                      <button key={a.login_id} onClick={() => toggleAiAccount(a.login_id)}
                        className={`px-2 py-1 rounded text-xs border ${sel ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-gray-600 border-gray-200'}`}>
                        {a.login_id}{a.seller_name ? ` (${a.seller_name})` : ''}
                      </button>
                    );
                  })}
                  {gmAccounts.length === 0 && <span className="text-xs text-gray-400 px-1">계정 로딩 중…</span>}
                </div>
                <p className="text-[11px] text-gray-400 mt-1">마스터(대표)로 ON하면 서브 상품 AI도 함께 ON됩니다.</p>
              </div>

              {/* 수동 제어 */}
              <div>
                <h3 className="font-semibold mb-3">수동 제어 <span className="text-xs text-gray-400 font-normal">— {aiAccounts.length ? `선택 ${aiAccounts.length}개` : '전체'} 계정 대상</span></h3>
                <div className="flex items-center gap-3">
                  <button onClick={() => handleAiControl('on')} className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700">
                    <Play size={16} /> {aiAccounts.length ? '선택' : '전체'} ON
                  </button>
                  <button onClick={() => handleAiControl('off')} className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700">
                    <Play size={16} /> {aiAccounts.length ? '선택' : '전체'} OFF
                  </button>
                  <button onClick={handleStopControl} className="flex items-center gap-1 px-5 py-2.5 bg-gray-800 text-white rounded-lg hover:bg-black">
                    🛑 강제 중지
                  </button>
                  {aiRunning && <span className="flex items-center gap-1 text-sm text-orange-600"><RefreshCw size={14} className="animate-spin" /> 진행 중…</span>}
                </div>
              </div>

              {/* 진행사항 / 이력 */}
              <div>
                <h3 className="font-semibold mb-2">진행사항 <span className="text-xs text-gray-400 font-normal">(계정별 ON/OFF 결과)</span></h3>
                <div className="border rounded max-h-56 overflow-y-auto text-xs">
                  <table className="w-full">
                    <thead className="bg-gray-50 sticky top-0"><tr className="text-gray-500">
                      <th className="text-left px-2 py-1">시각</th><th className="text-left px-2 py-1">계정</th>
                      <th className="text-left px-2 py-1">동작</th><th className="text-left px-2 py-1">상세</th>
                    </tr></thead>
                    <tbody>
                      {aiHistory.slice(0, 50).map((h: any, i: number) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-1">{h.event_time ? new Date(h.event_time).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}</td>
                          <td className="px-2 py-1 font-medium">
                            {h.seller_id || h.gmarket_id}
                            {h.seller_id && h.gmarket_id && h.seller_id !== h.gmarket_id && (
                              <span className="text-gray-400 font-normal"> ↳{h.gmarket_id}</span>
                            )}
                          </td>
                          <td className={`px-2 py-1 font-semibold ${(h.history_type || '').includes('ON') ? 'text-green-600' : 'text-red-600'}`}>{h.history_type}</td>
                          <td className="px-2 py-1 text-gray-500">{h.detail}</td>
                        </tr>
                      ))}
                      {aiHistory.length === 0 && <tr><td colSpan={4} className="px-2 py-3 text-center text-gray-400">이력 없음</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
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
