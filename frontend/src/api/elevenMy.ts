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
  cost_pct?: number | null;        // 판매가/마켓가*100 (100=원가와동일, <100=역마진, >100=마진)
}

export interface ElevenMyListResponse {
  items: ElevenMyProduct[];
  total: number;
  needs_check_total?: number;   // 확인필요(역마진: 구매원가>판매가) 건수
  no_match_total?: number;      // 미매칭(오너클랜 W코드 카탈로그에 없음) 건수
  high_margin_total?: number;   // 고마진(판매가가 구매원가의 1.5배 이상) 건수
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
  soldout_count: number;
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
  noMatch?: boolean,
  highMargin?: boolean,
  minAbsPct?: number,
  needsCheckPct?: number,
): Promise<ElevenMyListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (accountId) params.account_id = accountId;
  if (status) params.status = status;
  if (search) params.search = search;
  if (focusedOnly) params.focused_only = '1';
  if (sort) { params.sort = sort; params.order = order || 'asc'; }
  if (needsCheck) params.needs_check = '1';
  if (noMatch) params.no_match = '1';
  if (highMargin) params.high_margin = '1';
  if (minAbsPct != null) params.min_abs_pct = minAbsPct;
  if (needsCheckPct != null) params.needs_check_pct = needsCheckPct;
  const { data } = await api.get<ElevenMyListResponse>(`${base}/products/`, { params });
  return data;
}

/** 현재 필터에 맞는 '전체' 상품을 CSV(blob)로 내려받기 (페이지/선택 무관). */
export async function exportElevenMyProducts(
  accountId?: number, status?: string, search?: string,
  sort?: string, order?: 'asc' | 'desc',
  needsCheck?: boolean, noMatch?: boolean, highMargin?: boolean,
  focusedOnly?: boolean, needsCheckPct?: number,
): Promise<Blob> {
  const params: Record<string, string | number> = { export: 1 };
  if (focusedOnly) params.focused_only = '1';
  if (accountId) params.account_id = accountId;
  if (status) params.status = status;
  if (search) params.search = search;
  if (sort) { params.sort = sort; params.order = order || 'asc'; }
  if (needsCheck) params.needs_check = '1';
  if (noMatch) params.no_match = '1';
  if (highMargin) params.high_margin = '1';
  if (needsCheckPct != null) params.needs_check_pct = needsCheckPct;
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

export async function suspendSoldoutProducts(loginIds: string[]): Promise<{ status: string; message?: string; accounts?: number; total?: number; error?: string }> {
  const { data } = await api.post('/cpc/eleven-my/suspend-soldout/', { eids: loginIds });
  return data;
}

/** 확인필요/고마진 등에서 선택한 상품 id 목록을 판매중지(11번가). */
export async function suspendSelectedProducts(ids: number[]): Promise<{ status: string; message?: string; accounts?: number; total?: number; error?: string }> {
  const { data } = await api.post('/cpc/eleven-my/suspend-selected/', { ids });
  return data;
}

/** 나의상품(전체 플랫폼) 판매중 W코드 목록을 txt로 다운로드 — 누를 때마다 최신 데이터로 재추출.
 * batch/chunkSize 지정 시 그 구간만(오너클랜 등 대량조회 붙여넣기용 15만개 단위 분할). */
export async function downloadWCodes(missingOnly = true, batch?: number, chunkSize = 150000): Promise<Blob> {
  const params: Record<string, string | number> = {};
  if (missingOnly) params.missing_only = '1';
  if (batch) { params.batch = batch; params.chunk_size = chunkSize; }
  const resp = await api.get('/cpc/my-products/w-codes/', { params, responseType: 'blob' });
  return resp.data as Blob;
}

export interface LCodeStatusSummary {
  total: number;
  checked: number;
  unchecked: number;
  in_stock: number;
  soldout: number;
  not_found: number;
  running: boolean;
  last_checked_at: string | null;
  soldout_target_count: number;   // 품절 확정 L코드가 실제로 걸리는 나의상품(판매중) 건수 — 판매중지 대상
  soldout_target_by_platform?: { eleven: number; gmarket: number; smartstore: number };
}

/** 도매마트 L코드 판매중/품절 조회 시작(백그라운드, 재개 가능 — 이미 확인된 건 건너뜀). */
export async function startLCodeCheck(): Promise<{ status: string; message: string }> {
  const { data } = await api.post('/cpc/my-products/l-codes/start/');
  return data;
}

/** 실행 중인 L코드 조회 중지. */
export async function stopLCodeCheck(): Promise<{ status: string; message?: string; pid?: number }> {
  const { data } = await api.post('/cpc/my-products/l-codes/stop/');
  return data;
}

/** L코드 조회 진행상황(전체/확인됨/판매중/품절/실행여부). */
export async function fetchLCodeStatus(): Promise<LCodeStatusSummary> {
  const { data } = await api.get('/cpc/my-products/l-codes/status/');
  return data;
}

/** 미매칭 전체(판매중만) 판매중지 — 선택 없이 서버가 현재 필터 기준 전체를 계산해 처리(11번가). */
export async function suspendAllNoMatchProducts(accountId?: number, search?: string, kind?: 'no_match' | 'needs_check' | 'lcode_soldout', pct?: number): Promise<{ status: string; message?: string; accounts?: number; total?: number; error?: string }> {
  const body: Record<string, unknown> = {};
  if (accountId) body.account_id = accountId;
  if (search) body.search = search;
  if (kind) body.kind = kind;
  if (pct != null) body.pct = pct;
  const { data } = await api.post('/cpc/eleven-my/suspend-all-no-match/', body);
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
