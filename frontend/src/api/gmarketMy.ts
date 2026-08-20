import api from './client';

export interface GmarketMyProduct {
  id: number;
  login_id: string;
  seller_name: string;
  market: string;            // gmarket | auction
  product_no: string;
  product_name: string;
  sale_price: number;
  stock_quantity: number;
  status_type: string;
  seller_product_code: string;
  category_code: string;
  synced_at: string | null;
  purchase_cost?: number | null;   // 구매원가 = 예비상품(ownerclan) 마켓가
  cost_diff?: number | null;       // 차이 = 판매가 - 구매원가
  cost_pct?: number | null;        // 판매가/마켓가*100 (100=원가와동일, <100=역마진, >100=마진)
}

export interface GmarketMyListResponse {
  items: GmarketMyProduct[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  needs_check_total?: number;   // 확인필요(역마진: 구매원가>판매가) 건수
  no_match_total?: number;      // 미매칭(오너클랜 W코드 카탈로그에 없음) 건수
  high_margin_total?: number;   // 고마진(판매가가 구매원가의 1.5배 이상) 건수
}

export interface GmarketAccount {
  account_id: number;
  login_id: string;
  seller_name: string;
  product_count: number;
}

const base = '/cpc/gmarket-my';

export async function fetchGmarketMyAccounts(): Promise<GmarketAccount[]> {
  const { data } = await api.get<{ accounts: GmarketAccount[] }>(`${base}/accounts/`);
  return data.accounts;
}

export async function fetchGmarketMyProducts(
  page = 1, perPage = 50, accountId?: number, market?: string,
  status?: string, search?: string, sort?: string, order: 'asc' | 'desc' = 'asc',
  dedup = false, needsCheck = false, noMatch = false, highMargin = false,
  minAbsPct?: number,
): Promise<GmarketMyListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (accountId) params.account_id = accountId;
  if (market) params.market = market;
  if (status) params.status = status;
  if (search) params.search = search;
  if (sort) { params.sort = sort; params.order = order; }
  if (dedup) params.dedup = 1;
  if (needsCheck) params.needs_check = 1;
  if (noMatch) params.no_match = 1;
  if (highMargin) params.high_margin = 1;
  if (minAbsPct != null) params.min_abs_pct = minAbsPct;
  const { data } = await api.get<GmarketMyListResponse>(`${base}/products/`, { params });
  return data;
}

/** 확인필요/고마진 등에서 선택한 상품 id 목록을 판매중지(지마켓). */
export async function suspendSelectedGmarketProducts(ids: number[]): Promise<{ status: string; message?: string; accounts?: number; total?: number; error?: string }> {
  const { data } = await api.post('/cpc/gmarket-my/suspend-selected/', { ids });
  return data;
}

/** 미매칭 전체(판매중만) 판매중지 — 선택 없이 서버가 현재 필터 기준 전체를 계산해 처리(지마켓). */
export async function suspendAllNoMatchGmarketProducts(accountId?: number, search?: string): Promise<{ status: string; message?: string; accounts?: number; total?: number; error?: string }> {
  const body: Record<string, unknown> = {};
  if (accountId) body.account_id = accountId;
  if (search) body.search = search;
  const { data } = await api.post('/cpc/gmarket-my/suspend-all-no-match/', body);
  return data;
}

export async function exportGmarketMyProducts(
  accountId?: number, market?: string, status?: string, search?: string, dedup = false,
  needsCheck?: boolean, noMatch?: boolean, highMargin?: boolean,
): Promise<Blob> {
  const params: Record<string, string | number> = { export: 1 };
  if (accountId) params.account_id = accountId;
  if (market) params.market = market;
  if (status) params.status = status;
  if (search) params.search = search;
  if (dedup) params.dedup = 1;
  if (needsCheck) params.needs_check = 1;
  if (noMatch) params.no_match = 1;
  if (highMargin) params.high_margin = 1;
  const resp = await api.get(`${base}/products/`, { params, responseType: 'blob' });
  return resp.data as Blob;
}
