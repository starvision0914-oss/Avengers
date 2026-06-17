import api from './client';

export interface SpeedgoItem {
  id: number;
  domemea_no: string;
  original_name: string;
  processed_name: string;
  display_name: string;
  wholesale_price: number;
  shipping_fee: number;
  supplier: string;
  main_image_url: string;
  naver_category_path: string;
  naver_top_product_url: string;
  naver_matched_at: string | null;
  status: string;
  collected_at: string;
  updated_at: string;
}

export interface SpeedgoStats {
  total: number;
  matched_categories: number;
  unmatched_categories: number;
  by_status: Record<string, number>;
}

export interface SpeedgoListResult {
  items: SpeedgoItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface MatchResult {
  matched: number;
  failed: number;
  total: number;
  results: { item_id?: number; path?: string; top_url?: string; error?: string; source?: string }[];
  log: string[];
}

export const speedgoApi = {
  stats: () => api.get<SpeedgoStats>('/speedgo/stats/').then(r => r.data),
  list: (params: { page?: number; per_page?: number; status?: string; search?: string; only_unmatched?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    if (params.status) qs.set('status', params.status);
    if (params.search) qs.set('search', params.search);
    if (params.only_unmatched) qs.set('only_unmatched', '1');
    return api.get<SpeedgoListResult>(`/speedgo/items/?${qs}`).then(r => r.data);
  },
  matchCategories: (only_unmatched = true) =>
    api.post<MatchResult>('/speedgo/match-categories/', { only_unmatched },
      { timeout: 600_000 }).then(r => r.data),
  collectMybox: (login_id: string, password: string) =>
    api.post('/speedgo/collect-mybox/', { login_id, password },
      { timeout: 600_000 }).then(r => r.data),
  addManual: (original_name: string, wholesale_price?: number) =>
    api.post<{ id: number; created: boolean; item: SpeedgoItem }>(
      '/speedgo/items/add-manual/', { original_name, wholesale_price }).then(r => r.data),
  delete: (id: number) => api.delete(`/speedgo/items/${id}/`).then(r => r.data),
  run: (steps?: string[]) => api.post('/speedgo/run/', { steps }).then(r => r.data),
  runStatus: () => api.get<{ connected: boolean; busy: boolean; logs: { message: string; level: string; created_at: string }[] }>('/speedgo/run/status/').then(r => r.data),
  closeSession: () => api.post('/speedgo/session/close/').then(r => r.data),
};
