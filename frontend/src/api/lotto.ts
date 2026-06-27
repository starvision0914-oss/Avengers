import api from './client';

export interface LottoStats {
  min: number | null;
  max: number | null;
  count: number;
}

export interface LottoHistoryItem {
  drwNo: number;
  drwNoDate: string;
  numbers: number[];
  bonus: number;
}

export interface LottoSyncResult extends LottoStats {
  saved: number;
  log: string[];
  blocked: boolean;
}

export interface LottoCombination {
  numbers: number[];
  sum: number;
  odd_even: string;
  high_low?: string;
  consecutive?: number;
  ac?: number;
  overlap_prev?: number;
  score?: number;
  top_recent_hits?: number[];
  top_all_hits?: number[];
  reason?: string;
  breakdown?: string[];
}

export interface LottoPredictResult {
  combinations: LottoCombination[];
  total_draws: number;
  recent_n?: number;
  top10_freq?: [number, number][];
  top10_freq_recent?: [number, number][];
  log?: string[];
  tries?: number;
  rejects?: Record<string, number>;
  message?: string;
}

export interface LottoScoreTier {
  score: number | string;
  count: number;
}

export interface SavedPrediction {
  id: number;
  created_at: string;
  target_round: number;
  combinations: { numbers: number[]; score?: number; reason?: string }[];
  score_threshold: number;
  combo_count: number;
  drawn?: boolean;
  best_rank?: number | null;
  best_rank_label?: string;
  win_count?: Record<string, number> | null;
}

export interface PredictionCheckResult {
  pending: boolean;
  prediction: SavedPrediction;
  actual_numbers?: number[];
  actual_bonus?: number;
  actual_date?: string;
  combos?: {
    numbers: number[];
    score?: number;
    matched: number[];
    match_count: number;
    bonus_match: boolean;
    rank: number | null;
    rank_label: string;
  }[];
  win_count?: Record<string, number>;
  best_rank?: number | null;
  best_rank_label?: string;
  log: string[];
}

export interface LottoPredictBruteResult {
  mode: 'brute';
  target_score: number;
  found_count: number;
  returned_count: number;
  combinations: LottoCombination[];
  score_table: LottoScoreTier[];
  total_draws: number;
  total_valid_combos: number;
  compute_seconds: number;
  cached?: boolean;
  log: string[];
}

export interface LottoPositionStat {
  position: number;
  ball: number;
  matching_draws: number;
  used_draws: number;
  top10: [number, number][];
}

export interface LottoPredictFollowResult {
  mode: 'follow_next';
  prev_round: number;
  prev_numbers: number[];
  combinations: LottoCombination[];
  position_stats: LottoPositionStat[];
  log: string[];
  total_draws: number;
}

export interface LottoImportResult extends LottoStats {
  added: number;
  skipped: number;
  errors: string[];
}

export const lottoApi = {
  stats: () => api.get<LottoStats>('/lotto/stats/').then(r => r.data),
  history: (limit = 20) =>
    api.get<{ items: LottoHistoryItem[] } & LottoStats>(`/lotto/history/?limit=${limit}`).then(r => r.data),
  sync: (max_to_fetch?: number) =>
    api.post<LottoSyncResult>('/lotto/sync/', { max_to_fetch }).then(r => r.data),
  predict: (count = 5) =>
    api.get<LottoPredictResult>(`/lotto/predict/?count=${count}`).then(r => r.data),
  predictBrute: (target = 100, count = 5) =>
    api.get<LottoPredictBruteResult>(`/lotto/predict-brute/?target=${target}&count=${count}`,
      { timeout: 300_000 }).then(r => r.data),
  predictMirrorPrev: (count = 5) =>
    api.get<LottoPredictBruteResult & { prev_round: number; prev_numbers: number[] }>(
      `/lotto/predict-mirror-prev/?count=${count}`,
      { timeout: 300_000 }).then(r => r.data),
  predictFollowNext: (count = 10) =>
    api.get<LottoPredictFollowResult>(
      `/lotto/predict-follow-next/?count=${count}`).then(r => r.data),
  // 저장된 예측 폴더
  listPredictions: () => api.get<{ items: SavedPrediction[] }>('/lotto/predictions/').then(r => r.data),
  savePrediction: (combinations: LottoCombination[], score_threshold: number) =>
    api.post<SavedPrediction>('/lotto/predictions/', { combinations, score_threshold }).then(r => r.data),
  checkPrediction: (id: number) =>
    api.get<PredictionCheckResult>(`/lotto/predictions/${id}/check/`).then(r => r.data),
  deletePrediction: (id: number) =>
    api.delete<{ deleted: number }>(`/lotto/predictions/${id}/`).then(r => r.data),
  importCsv: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post<LottoImportResult>('/lotto/import-csv/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  exportCsv: async () => {
    const res = await api.get('/lotto/export-csv/', { responseType: 'blob' });
    // 파일명 추출
    const cd = res.headers['content-disposition'] || '';
    const m = cd.match(/filename\*=UTF-8''([^;]+)/);
    const filename = m ? decodeURIComponent(m[1]) : 'lotto_history.csv';
    // 다운로드 트리거
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    return filename;
  },
};
