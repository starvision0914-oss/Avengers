import api from './client';

export interface ElevenMyProduct {
  id: number;
  account_id: number;
  login_id: string;
  seller_name: string;
  is_focused: boolean;
  product_no: number;
  product_name: string;
  sale_price: number;
  stock_quantity: number;
  status_type: string;
  seller_product_code: string;
  category_id: string;
  product_image_url: string;
  synced_at: string | null;
  created_at: string;
  updated_at: string;
  purchase_cost?: number | null;   // 구매원가 = 예비상품(ownerclan) 마켓가
  cost_diff?: number | null;       // 차이 = 판매가 - 구매원가
}

export interface ElevenMyListResponse {
  items: ElevenMyProduct[];
  total: number;
  needs_check_total?: number;   // 확인필요(역마진: 구매원가>판매가) 건수
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ElevenAccountSummary {
  account_id: number;
  login_id: string;
  seller_name: string;
  cost_type: string;
  crawling_status: string;
  fail_count: number;
  last_crawled_at: string | null;
  has_api_key: boolean;
  api_key_masked: string;
  product_count: number;
  last_synced: string | null;
  grade: number | null;
  grade_message: string;
  required_sales: number | null;
  grade_collected_at: string | null;
  balance: number | null;
  balance_at: string | null;
  cost_30days: number;
  // 셀러오피스 (crawl_11st_office)
  office_collected_at: string | null;
  office_cash: number | null;
  office_point: number | null;
  office_ad_balance: number | null;
  product_limit: number | null;
  products: number | null;
  banned: number | null;
  available: number | null;
  overdue: number | null;
  undelivered: number | null;
  draft: number | null;
  fulfillment: string;
  shipping: string;
  inquiry: string;
  office_error: string;
}

export interface IntegratedSyncResult {
  started: string[];
  products_result: SyncResult | SyncBatchResult | null;
  message: string;
}

export interface SyncResult {
  login_id?: string;
  seller_name?: string;
  synced?: number;
  total_from_api?: number;
  synced_at?: string;
  error?: string;
}

export interface SyncBatchResult {
  accounts?: SyncResult[];
  skipped_no_api_key?: string[];
  total_accounts?: number;
}

const base = '/cpc/eleven-my';

export async function fetchElevenMyProducts(
  page = 1,
  perPage = 50,
  accountId?: number,
  status?: string,
  search?: string,
  focusedOnly?: boolean,
  sort?: string,
  order?: 'asc' | 'desc',
  needsCheck?: boolean,
): Promise<ElevenMyListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (accountId) params.account_id = accountId;
  if (status) params.status = status;
  if (search) params.search = search;
  if (focusedOnly) params.focused_only = '1';
  if (sort) { params.sort = sort; params.order = order || 'asc'; }
  if (needsCheck) params.needs_check = '1';
  const { data } = await api.get<ElevenMyListResponse>(`${base}/products/`, { params });
  return data;
}

/** 현재 필터에 맞는 '전체' 상품을 CSV(blob)로 내려받기 (페이지/선택 무관). */
export async function exportElevenMyProducts(
  accountId?: number, status?: string, search?: string,
  sort?: string, order?: 'asc' | 'desc',
): Promise<Blob> {
  const params: Record<string, string | number> = { export: 1, focused_only: '1' };
  if (accountId) params.account_id = accountId;
  if (status) params.status = status;
  if (search) params.search = search;
  if (sort) { params.sort = sort; params.order = order || 'asc'; }
  const resp = await api.get(`${base}/products/`, { params, responseType: 'blob' });
  return resp.data as Blob;
}

export async function fetchElevenMyProductDetail(id: number): Promise<ElevenMyProduct> {
  const { data } = await api.get<ElevenMyProduct>(`${base}/products/${id}/`);
  return data;
}

export async function syncElevenMyProducts(accountId?: number): Promise<SyncResult | SyncBatchResult> {
  const body: Record<string, number> = {};
  if (accountId) body.account_id = accountId;
  const { data } = await api.post(`${base}/sync/`, body, { timeout: 600000 });
  return data;
}

export async function fetchElevenMyAccounts(all?: boolean): Promise<{ accounts: ElevenAccountSummary[] }> {
  const { data } = await api.get<{ accounts: ElevenAccountSummary[] }>(`${base}/accounts/`, {
    params: all ? { all: '1' } : undefined,
  });
  return data;
}

// 선택 계정 등록상품(대량엑셀) 재크롤 트리거
export async function triggerProductRecrawl(loginIds: string[]): Promise<{ status: string; error?: string }> {
  const { data } = await api.post('/cpc/crawler/trigger/', {
    platform: '11st', type: 'product', accounts: loginIds,
  });
  return data;
}

export type DuplicateMode = 'strict' | 'loose' | 'image';

export interface DuplicateItem {
  id: number;
  account_id: number;
  login_id: string;
  seller_name: string;
  product_no: number;
  product_name: string;
  sale_price: number;
  stock_quantity: number;
  status_type: string;
  product_image_url: string;
  seller_product_code: string;
  category_id: string;
}

export interface DuplicateGroup {
  group_key: string;
  kind: string;
  count: number;
  sample_name: string;
  sample_price: number;
  sample_image: string;
  items: DuplicateItem[];
}

export interface DuplicateResult {
  mode: DuplicateMode;
  group_count: number;
  total_duplicate_items: number;
  total_scanned: number;
  groups: DuplicateGroup[];
}

export async function fetchDuplicates(mode: DuplicateMode = 'strict'): Promise<DuplicateResult> {
  const { data } = await api.get<DuplicateResult>('/cpc/eleven-my/duplicates/', { params: { mode } });
  return data;
}

export async function triggerIntegratedSync(tasks?: string[], accountId?: number): Promise<IntegratedSyncResult> {
  const body: Record<string, unknown> = {};
  if (tasks && tasks.length > 0) body.tasks = tasks;
  if (accountId) body.account_id = accountId;
  const { data } = await api.post<IntegratedSyncResult>(`${base}/integrated-sync/`, body, { timeout: 600000 });
  return data;
}
