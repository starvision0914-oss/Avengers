import { useEffect, useState, useRef, useCallback } from 'react';
import { Dices, RefreshCw, Upload, Download, AlertCircle, TrendingUp, Database, X, FolderOpen, Trash2, Save, Clock, Trophy } from 'lucide-react';
import toast from 'react-hot-toast';
import { lottoApi, type LottoStats, type LottoHistoryItem, type LottoCombination, type LottoScoreTier, type SavedPrediction } from '../../api/lotto';

function BallBadge({ n }: { n: number }) {
  // 동행복권 공식 색상
  const color =
    n <= 10 ? 'bg-yellow-400 text-yellow-900' :
    n <= 20 ? 'bg-blue-500 text-white' :
    n <= 30 ? 'bg-red-500 text-white' :
    n <= 40 ? 'bg-gray-700 text-white' :
              'bg-green-500 text-white';
  return (
    <span className={`inline-flex items-center justify-center w-9 h-9 rounded-full font-bold text-sm ${color}`}>
      {n}
    </span>
  );
}

export default function LottoPage() {
  const [stats, setStats] = useState<LottoStats>({ min: null, max: null, count: 0 });
  const [history, setHistory] = useState<LottoHistoryItem[]>([]);
  const [combos, setCombos] = useState<LottoCombination[]>([]);
  const [totalDraws, setTotalDraws] = useState(0);
  const [topFreq, setTopFreq] = useState<[number, number][]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [comboCount, setComboCount] = useState(5);
  const fileRef = useRef<HTMLInputElement>(null);

  const refreshStats = useCallback(async () => {
    try {
      const s = await lottoApi.stats();
      setStats(s);
      const h = await lottoApi.history(100);
      setHistory(h.items);
    } catch (e: any) {
      toast.error(`통계 로드 실패: ${e.message || e}`);
    }
  }, []);

  const onExport = async () => {
    setExporting(true);
    try {
      const filename = await lottoApi.exportCsv();
      toast.success(`다운로드 완료: ${filename}`);
    } catch (e: any) {
      toast.error(`다운로드 실패: ${e.message || e}`);
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => { refreshStats(); }, [refreshStats]);

  const onSync = async () => {
    setSyncing(true);
    setLog(prev => [...prev, '== 동기화 시작 =='].slice(-200));
    try {
      const r = await lottoApi.sync();
      setLog(prev => [...prev, ...r.log, `== 신규 ${r.saved}건 저장, DB 총 ${r.count}회 ==`].slice(-200));
      if (r.blocked) {
        toast.error('⛔ dhlottery WAF 차단 감지 — CSV 임포트로 우회하세요');
      } else if (r.saved > 0) {
        toast.success(`${r.saved}건 추가됨`);
      } else {
        toast('최신 데이터입니다');
      }
      setStats({ min: r.min, max: r.max, count: r.count });
      await refreshStats();
    } catch (e: any) {
      toast.error(`동기화 실패: ${e.message || e}`);
      setLog(prev => [...prev, `오류: ${e.message || e}`].slice(-200));
    } finally {
      setSyncing(false);
    }
  };

  // 전수조사 결과 캐시 (점수 분포) — 사용자가 다음 점수대 검색할 때 재호출 안 함
  const [scoreTable, setScoreTable] = useState<LottoScoreTier[]>([]);
  const [askNextScore, setAskNextScore] = useState<number | null>(null); // 모달에 표시할 다음 점수
  const [searchedTargets, setSearchedTargets] = useState<number[]>([]); // 이미 시도한 점수들
  const [currentTarget, setCurrentTarget] = useState<number | null>(null); // 마지막 표시된 점수대
  const [savedPredictions, setSavedPredictions] = useState<SavedPrediction[]>([]);
  const [saving, setSaving] = useState(false);

  const refreshPredictions = useCallback(async () => {
    try {
      const r = await lottoApi.listPredictions();
      setSavedPredictions(r.items);
    } catch (e: any) {
      console.error(e);
    }
  }, []);
  useEffect(() => { refreshPredictions(); }, [refreshPredictions]);

  const onSavePrediction = async () => {
    if (combos.length === 0) {
      toast.error('저장할 예측 결과가 없습니다. 먼저 "2. AI 예측"을 실행하세요.');
      return;
    }
    setSaving(true);
    try {
      const r = await lottoApi.savePrediction(combos, currentTarget ?? 0);
      toast.success(`#${r.id} 저장됨 — ${r.target_round}회 대상 ${r.combo_count}조합`);
      setLog(prev => [...prev,
        `💾 예측 저장 #${r.id} — ${r.target_round}회 대상 ${r.combo_count}조합 (${new Date(r.created_at).toLocaleString('ko-KR')})`,
      ].slice(-300));
      await refreshPredictions();
    } catch (e: any) {
      toast.error(`저장 실패: ${e.message || e}`);
    } finally {
      setSaving(false);
    }
  };

  const onClickFolder = async (id: number) => {
    try {
      const r = await lottoApi.checkPrediction(id);
      setLog(prev => [...prev, ...r.log].slice(-400));
      if (r.pending) {
        toast(`⌛ ${r.prediction.target_round}회 추첨 대기 중`);
      } else {
        toast.success(`#${id} 결과 — ${r.best_rank_label}`);
      }
    } catch (e: any) {
      toast.error(`확인 실패: ${e.message || e}`);
    }
  };

  const onDeleteFolder = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`예측 #${id} 삭제할까요?`)) return;
    try {
      await lottoApi.deletePrediction(id);
      toast.success(`#${id} 삭제됨`);
      await refreshPredictions();
    } catch (e: any) {
      toast.error(`삭제 실패: ${e.message || e}`);
    }
  };

  const runBrute = async (target: number) => {
    setPredicting(true);
    const isFirst = scoreTable.length === 0;
    if (isFirst) {
      setLog(prev => [...prev,
        '== 전수조사 시작 (C(45,6) = 8,145,060 조합) ==',
        '※ 최초 호출은 약 100초 소요 (이후 캐시로 즉시 응답)',
      ].slice(-300));
    }
    try {
      const r = await lottoApi.predictBrute(target, comboCount);
      setScoreTable(r.score_table);
      setTotalDraws(r.total_draws);
      setSearchedTargets(prev => prev.includes(target) ? prev : [...prev, target]);
      setLog(prev => [...prev, ...r.log].slice(-400));

      if (r.found_count > 0) {
        setCombos(r.combinations);
        setCurrentTarget(target);
        const filled = r.returned_count - Math.min(r.found_count, r.returned_count);
        if (filled > 0 && r.found_count < r.returned_count) {
          toast.success(
            `${target}점 ${r.found_count}개 + 점수 내림차순 보충 ${filled}개 = 총 ${r.returned_count}조합`
          );
        } else {
          toast.success(`${target}점 이상 ${r.found_count}개 발견 — 상위 ${r.returned_count}개 표시`);
        }
        setAskNextScore(null);
      } else {
        // 없으면 모달로 다음 점수 검색 여부 물어봄
        const next = target - 1;
        if (next >= 0) {
          setAskNextScore(next);
        } else {
          toast.error('모든 점수대 검색 종료');
        }
      }
    } catch (e: any) {
      toast.error(`예측 실패: ${e.message || e}`);
      setLog(prev => [...prev, `오류: ${e.message || e}`].slice(-300));
    } finally {
      setPredicting(false);
    }
  };

  const onPredict = async () => {
    setSearchedTargets([]);
    setCombos([]);
    await runBrute(100);
  };

  const onSearchNextTier = async () => {
    if (askNextScore === null) return;
    const target = askNextScore;
    setAskNextScore(null);
    await runBrute(target);
  };

  const onCancelNextTier = () => {
    setAskNextScore(null);
    toast('검색 중단');
  };

  const onPredictMirrorPrev = async () => {
    setPredicting(true);
    setLog(prev => [...prev,
      '== 전회차 패턴 학습 예측 시작 ==',
      '※ 최초 호출은 약 90초 소요 (캐시 후 즉시)',
    ].slice(-300));
    try {
      const r = await lottoApi.predictMirrorPrev(comboCount);
      setCombos(r.combinations);
      setTotalDraws(stats.count);
      if (r.log) setLog(prev => [...prev, ...r.log!].slice(-400));
      toast.success(`전회차 ${r.prev_round}회 패턴 학습 — ${r.combinations.length}조합 생성`);
    } catch (e: any) {
      toast.error(`예측 실패: ${e.message || e}`);
      setLog(prev => [...prev, `오류: ${e.message || e}`].slice(-300));
    } finally {
      setPredicting(false);
    }
  };

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setImporting(true);
    setLog(prev => [...prev, `== CSV 임포트: ${f.name} ==`].slice(-200));
    try {
      const r = await lottoApi.importCsv(f);
      setLog(prev => [...prev,
        `저장 ${r.added}건, 스킵 ${r.skipped}건`,
        ...(r.errors || []),
        `DB 총 ${r.count}회`,
      ].slice(-200));
      toast.success(`임포트 완료 — 저장 ${r.added} / 스킵 ${r.skipped}`);
      setStats({ min: r.min, max: r.max, count: r.count });
      await refreshStats();
    } catch (err: any) {
      toast.error(`임포트 실패: ${err.message || err}`);
      setLog(prev => [...prev, `오류: ${err.message || err}`].slice(-200));
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Dices className="w-8 h-8 text-purple-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">로또 6/45 AI 예측기</h1>
          <p className="text-sm text-gray-500">SQLite 누적 + 빈도 가중치 + 홀짝 균형 필터로 다음 회차 조합 생성</p>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">저장된 회차</span>
            <Database className="w-5 h-5 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{stats.count.toLocaleString()}</div>
          <div className="text-xs text-gray-500 mt-1">
            {stats.min ? `${stats.min}회 ~ ${stats.max}회` : '데이터 없음'}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">예측 조합 수</span>
            <Dices className="w-5 h-5 text-purple-500" />
          </div>
          <input
            type="number" min={1} max={20} value={comboCount}
            onChange={e => setComboCount(Math.max(1, Math.min(20, +e.target.value || 1)))}
            className="mt-2 w-24 px-3 py-1 border border-gray-300 rounded text-lg font-bold focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>

        <div className="bg-white rounded-lg shadow p-5 border border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">상위 빈출 번호</span>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {topFreq.length === 0
              ? <span className="text-xs text-gray-400">예측 실행 후 표시</span>
              : topFreq.slice(0, 6).map(([n, c]) => (
                  <span key={n} className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">
                    {n} ({c})
                  </span>
                ))}
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button
          onClick={onSync} disabled={syncing}
          className="flex items-center gap-2 px-5 py-3 bg-green-600 text-white font-semibold rounded-lg shadow hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed">
          <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? '동기화 중...' : '1. 최신 데이터 동기화'}
        </button>

        <button
          onClick={onPredict} disabled={predicting || stats.count === 0}
          className="flex items-center gap-2 px-5 py-3 bg-yellow-500 text-white font-semibold rounded-lg shadow hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed">
          <Dices className={`w-5 h-5 ${predicting ? 'animate-spin' : ''}`} />
          {predicting
            ? (scoreTable.length === 0 ? '전수조사 중... (~100초)' : '검색 중...')
            : `2. AI 다음회차 ${comboCount}조합 예측 (100점 부터)`}
        </button>

        <button
          onClick={() => fileRef.current?.click()} disabled={importing}
          className="flex items-center gap-2 px-5 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow hover:bg-blue-700 disabled:opacity-50">
          <Upload className={`w-5 h-5 ${importing ? 'animate-spin' : ''}`} />
          {importing ? '임포트 중...' : '3. CSV 임포트'}
        </button>
        <input type="file" ref={fileRef} accept=".csv" className="hidden" onChange={onFile} />

        <button
          onClick={onSavePrediction} disabled={saving || combos.length === 0}
          className="flex items-center gap-2 px-5 py-3 bg-pink-600 text-white font-semibold rounded-lg shadow hover:bg-pink-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title={combos.length === 0 ? '먼저 "2. AI 예측"을 실행하세요' : `${combos.length}조합 저장`}>
          <Save className={`w-5 h-5 ${saving ? 'animate-pulse' : ''}`} />
          {saving ? '저장 중...' : `4. AI 예측 당첨번호 저장 (${combos.length})`}
        </button>

        <button
          onClick={onPredictMirrorPrev} disabled={predicting || stats.count === 0}
          className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-indigo-600 to-fuchsia-600 text-white font-semibold rounded-lg shadow hover:from-indigo-700 hover:to-fuchsia-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="직전 추첨 회차의 패턴(합/홀짝/고저/3구역/끝자리)을 템플릿으로 가장 유사한 조합 추출">
          <Dices className={`w-5 h-5 ${predicting ? 'animate-spin' : ''}`} />
          {predicting ? '검색 중...' : `5. 전회차 패턴 학습 예측`}
        </button>
      </div>

      {/* 안내 */}
      {stats.count === 0 && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-900">
            <p className="font-semibold">DB가 비어있습니다.</p>
            <p className="mt-1">
              "1. 동기화" 를 눌러 dhlottery API 로 자동 수집을 시도하거나,
              차단된 경우 "3. CSV 임포트" 로 직접 데이터를 채우세요.
            </p>
            <p className="mt-1 text-xs text-amber-700">
              CSV 컬럼: drwNo, drwNoDate, num1~num6, bnusNo (한글 헤더도 인식)
            </p>
          </div>
        </div>
      )}

      {/* 예측 결과 */}
      {combos.length > 0 && (
        <div className="bg-white rounded-lg shadow border border-gray-200 mb-6">
          <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">예측 조합 ({combos.length}개) — 학습 데이터 {totalDraws.toLocaleString()}회</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">순위</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-purple-700 uppercase">점수</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">번호</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase">합</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase">홀:짝</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase">고:저</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase">연속</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase">AC</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">근거</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {combos.map((c, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-bold text-gray-900">{i + 1}위</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-block px-2 py-1 text-sm font-bold rounded-full bg-gradient-to-r from-purple-500 to-pink-500 text-white" title="100점 만점">
                        {c.score ?? '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5">
                        {c.numbers.map(n => <BallBadge key={n} n={n} />)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-mono text-gray-700">{c.sum}</td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600">{c.odd_even}</td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600">{c.high_low ?? '-'}</td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600">{c.consecutive ?? '-'}</td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600">{c.ac ?? '-'}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {c.breakdown && c.breakdown.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {c.breakdown.slice(0, 4).map((b, k) => (
                            <span key={k} className="px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded text-[10px]">
                              {b}
                            </span>
                          ))}
                          {c.breakdown.length > 4 && (
                            <span className="text-[10px] text-gray-400">+{c.breakdown.length - 4}</span>
                          )}
                        </div>
                      ) : <span className="text-gray-300">-</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 저장된 AI 예측 폴더 */}
      {savedPredictions.length > 0 && (
        <div className="bg-white rounded-lg shadow border border-gray-200 mb-6">
          <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-pink-600" />
              저장된 AI 예측 폴더 ({savedPredictions.length})
              <span className="ml-3 text-xs font-normal text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                ⏰ 매주 토요일 21:00 자동 평가
              </span>
            </h3>
            <span className="text-xs text-gray-500">폴더 클릭 → 실행 로그에 등수 결과 표시</span>
          </div>
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">#</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">저장 시각</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">대상</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">타겟</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">조합 전체 ({savedPredictions[0]?.combinations.length ?? 0}세트)</th>
                  <th className="px-4 py-2 text-center text-xs font-semibold text-gray-600">상태</th>
                  <th className="px-4 py-2 text-right text-xs font-semibold text-gray-600"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {savedPredictions.map(p => {
                  const rankColor =
                    p.best_rank === 1 ? 'bg-yellow-100 text-yellow-900' :
                    p.best_rank === 2 ? 'bg-gray-200 text-gray-900' :
                    p.best_rank === 3 ? 'bg-orange-100 text-orange-800' :
                    p.best_rank === 4 ? 'bg-orange-50 text-orange-700' :
                    p.best_rank === 5 ? 'bg-green-50 text-green-700' :
                    p.drawn ? 'bg-gray-100 text-gray-500' : 'bg-blue-50 text-blue-700';
                  return (
                    <tr key={p.id}
                        className="hover:bg-pink-50 cursor-pointer transition-colors align-top"
                        onClick={() => onClickFolder(p.id)}>
                      <td className="px-4 py-2 text-gray-900 font-mono text-xs">#{p.id}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-gray-400" />
                          {new Date(p.created_at).toLocaleString('ko-KR', {
                            month: '2-digit', day: '2-digit',
                            hour: '2-digit', minute: '2-digit'
                          })}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-center text-gray-900 font-semibold whitespace-nowrap">{p.target_round}회</td>
                      <td className="px-4 py-2 text-center text-purple-700 font-semibold">{p.score_threshold || '-'}</td>
                      <td className="px-4 py-2 text-xs">
                        <div className="space-y-1">
                          {p.combinations.map((c, idx) => {
                            const scoreColor =
                              (c.score ?? 0) >= 100 ? 'bg-purple-600 text-white' :
                              (c.score ?? 0) >= 95 ? 'bg-purple-100 text-purple-800' :
                              (c.score ?? 0) >= 90 ? 'bg-indigo-100 text-indigo-800' :
                              'bg-gray-100 text-gray-700';
                            return (
                              <div key={idx} className="flex items-center gap-2">
                                <span className={`inline-flex items-center justify-center min-w-[42px] px-1.5 py-0.5 rounded text-[10px] font-bold ${scoreColor}`}>
                                  {c.score ?? '-'}점
                                </span>
                                <span className="font-mono text-gray-800">
                                  {c.numbers.map(n => String(n).padStart(2, '0')).join(' · ')}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${rankColor}`}>
                          {p.best_rank && p.best_rank <= 3 && <Trophy className="w-3 h-3" />}
                          {p.best_rank_label}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={(e) => onDeleteFolder(p.id, e)}
                          className="text-gray-400 hover:text-red-600 p-1"
                          title="삭제">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 최근 회차 */}
        <div className="bg-white rounded-lg shadow border border-gray-200">
          <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">최근 회차 (최근 100)</h3>
            <button
              onClick={onExport}
              disabled={exporting || stats.count === 0}
              title={`전체 ${stats.count.toLocaleString()}회 CSV 다운로드`}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className={`w-4 h-4 ${exporting ? 'animate-pulse' : ''}`} />
              {exporting ? '다운로드 중...' : `전체 ${stats.count.toLocaleString()}회 CSV`}
            </button>
          </div>
          <div className="overflow-y-auto max-h-96">
            {history.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">데이터 없음</div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">회차</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">추첨일</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600">번호</th>
                    <th className="px-3 py-2 text-center text-xs font-semibold text-gray-600">+보너스</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {history.map(h => (
                    <tr key={h.drwNo} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-sm font-medium">{h.drwNo}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{h.drwNoDate}</td>
                      <td className="px-3 py-2 text-xs font-mono">{h.numbers.join(', ')}</td>
                      <td className="px-3 py-2 text-xs text-center text-amber-600 font-semibold">{h.bonus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* 로그 */}
        <div className="bg-white rounded-lg shadow border border-gray-200">
          <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">실행 로그</h3>
            <button onClick={() => setLog([])} className="text-xs text-gray-400 hover:text-gray-700">지우기</button>
          </div>
          <div className="p-3 bg-gray-50 max-h-96 overflow-y-auto font-mono text-xs text-gray-700">
            {log.length === 0
              ? <div className="text-gray-400 text-center py-8">로그가 비어있습니다</div>
              : log.map((l, i) => <div key={i} className="py-0.5">{l}</div>)
            }
          </div>
        </div>
      </div>

      {/* 다음 점수대 검색 확인 모달 */}
      {askNextScore !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-500" />
                {searchedTargets[searchedTargets.length - 1]}점 조합 없음
              </h3>
              <button onClick={onCancelNextTier} className="text-gray-400 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-gray-700 mb-4">
              <span className="font-semibold text-red-600">{searchedTargets[searchedTargets.length - 1]}점</span> 이상 조합이 존재하지 않습니다.
              <br />
              <span className="font-semibold text-blue-700">{askNextScore}점</span> 이상 조합으로 검색을 진행할까요?
            </p>

            {/* 점수대별 개수 미리보기 */}
            <div className="mb-5 p-3 bg-gray-50 rounded-lg max-h-56 overflow-y-auto">
              <div className="text-xs font-semibold text-gray-500 mb-2">점수대별 조합 개수 (현재 점수에 이미 누적 표시)</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs font-mono">
                {scoreTable
                  .filter(t => typeof t.score === 'number' && (t.score as number) >= Math.max(askNextScore - 10, 0) && (t.score as number) <= 100)
                  .map(t => {
                    const isNext = t.score === askNextScore;
                    const isSearched = typeof t.score === 'number' && searchedTargets.includes(t.score as number);
                    return (
                      <div
                        key={String(t.score)}
                        className={`flex justify-between px-2 py-1 rounded ${
                          isNext ? 'bg-blue-100 text-blue-900 font-bold' :
                          isSearched ? 'bg-red-50 text-red-700 line-through' : ''
                        }`}
                      >
                        <span>{t.score}점</span>
                        <span>{t.count.toLocaleString()}개</span>
                      </div>
                    );
                  })}
              </div>
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={onCancelNextTier}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">
                중단
              </button>
              <button
                onClick={onSearchNextTier}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                {askNextScore}점으로 검색
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
