import api from './client';

export interface SmartStoreAccount {
  id: number;
  login_id: string;
  store_name: string;
  store_slug: string;
  display_name: string;
  memo: string;
  has_pw: boolean;
  has_api_key: boolean;
  is_active: boolean;
  display_order: number;
  purchase_rate: number;
}

export interface DashboardSummary {
  total_sales: number;
  total_cancel: number;
  total_return: number;
  total_settlement: number;
  total_orders: number;
  total_ad_cost: number;
  total_ad_cpc: number;
  total_ad_ai: number;
  total_cogs: number;
  total_excel_revenue: number;
  total_clicks: number;
  total_conversion: number;
  roas: number | null;
}

export interface AccountRow {
  account_id: number;
  account_name: string;
  naver_ad_account_id?: string | null;
  sales: number;
  settlement: number;
  orders: number;
  ad_cost: number;
  ad_cpc: number;
  ad_ai: number;
  excel_revenue: number;
  cogs: number;
  roas: number | null;
}

export interface DailyRow {
  date: string;
  sales: number;
  settlement: number;
  orders: number;
  ad_cost: number;
}

export interface DashboardResponse {
  period: { start: string; end: string };
  summary: DashboardSummary;
  by_account: AccountRow[];
  daily: DailyRow[];
}

export interface SmartStoreProduct {
  id: number;
  account_id: number;
  store_name: string;
  product_no: string;
  channel_product_no: string;
  name: string;
  sale_price: number;
  stock_quantity: number;
  status_type: string;
  seller_management_code: string;
  category_id: string;
  product_image_url: string;
  ownerclan_soldout: boolean;
  synced_at: string;
}

export interface ProductListResponse {
  items: SmartStoreProduct[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ProductStats {
  total: number;
  by_status: Record<string, number>;
  by_account: { account_id: number; account_name: string; count: number; last_synced_at: string | null }[];
  last_synced_at: string | null;
}

export interface SuspendPreviewResult {
  total_count: number;
  by_store: { store_name: string; count: number }[];
  w_codes: string[];
}

export interface SuspendResult {
  success_count: number;
  fail_count: number;
  errors: { product_no: string; error: string }[];
}

// ── 계정 ──

export async function getAccounts(): Promise<SmartStoreAccount[]> {
  const { data } = await api.get<SmartStoreAccount[]>('/smartstore/accounts/');
  return data;
}

export async function createAccount(payload: Partial<SmartStoreAccount> & {
  login_pw?: string; commerce_api_key?: string; commerce_secret_key?: string;
}): Promise<{ id: number }> {
  const { data } = await api.post('/smartstore/accounts/', payload);
  return data;
}

export async function updateAccount(id: number, payload: Partial<SmartStoreAccount> & {
  login_pw?: string; commerce_api_key?: string; commerce_secret_key?: string;
}): Promise<void> {
  await api.patch(`/smartstore/accounts/${id}/`, payload);
}

export async function deleteAccount(id: number): Promise<void> {
  await api.delete(`/smartstore/accounts/${id}/`);
}

// ── 대시보드 ──

export async function getDashboard(params: {
  start?: string;
  end?: string;
  account_id?: number[];
}): Promise<DashboardResponse> {
  const { data } = await api.get<DashboardResponse>('/smartstore/dashboard/', { params });
  return data;
}

// ── 상품 목록 ──

export async function getProducts(params: {
  account_id?: number | string;
  page?: number;
  per_page?: number;
  status?: string;
  search?: string;
  ownerclan_soldout?: string;
}): Promise<ProductListResponse> {
  const { data } = await api.get<ProductListResponse>('/smartstore/products/', { params });
  return data;
}

export async function syncProducts(account_id: number): Promise<{ synced: number; total_from_api: number; store_name: string; synced_at: string }> {
  const { data } = await api.post('/smartstore/products/sync/', { account_id });
  return data;
}

export async function getProductStats(account_id?: number | string): Promise<ProductStats> {
  const { data } = await api.get<ProductStats>('/smartstore/product-stats/', {
    params: account_id ? { account_id } : {},
  });
  return data;
}

// ── 클린위반 ──

export interface CleanViolationSummary {
  account_id: number;
  account_name: string;
  total: number;
  types: Record<string, number>;
}

export interface CleanViolationItem {
  id: number;
  violation_date: string;
  violation_type: string;
  product_name: string;
  product_id: string;
  nv_mid: string;
  note: string;
}

export interface CleanViolationTypeSummary {
  violation_type: string;
  count: number;
  problem: string;
  solution: string;
}

export interface CleanViolationDetail {
  account_id: number;
  total: number;
  violations: CleanViolationItem[];
  type_summary: CleanViolationTypeSummary[];
}

export async function getCleanViolations(): Promise<CleanViolationSummary[]> {
  const { data } = await api.get<CleanViolationSummary[]>('/smartstore/clean-violations/');
  return data;
}

export async function getCleanViolationDetail(accountId: number): Promise<CleanViolationDetail> {
  const { data } = await api.get<CleanViolationDetail>(`/smartstore/clean-violations/${accountId}/`);
  return data;
}

export async function downloadProductExcel(params: {
  account_ids?: number[];
  statuses?: string[];
  w_only?: boolean;
}): Promise<void> {
  const sp = new URLSearchParams();
  params.account_ids?.forEach(id => sp.append('account_ids', String(id)));
  params.statuses?.forEach(s => sp.append('statuses', s));
  if (params.w_only) sp.append('w_only', '1');

  const { data, headers } = await api.get(`/smartstore/products/excel/?${sp.toString()}`, {
    responseType: 'blob',
  });
  const cd = headers['content-disposition'] || '';
  const match = cd.match(/filename\*?=(?:UTF-8'')?(.+)/i);
  const filename = match ? decodeURIComponent(match[1]) : '스마트스토어_상품목록.xlsx';
  const url = URL.createObjectURL(data as Blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function previewSuspend(
  productIds: number[], selectAll: boolean,
  filters: { account_id: number; status?: string; search?: string; ownerclan_soldout?: boolean },
): Promise<SuspendPreviewResult> {
  const { data } = await api.post<SuspendPreviewResult>('/smartstore/products/suspend-preview/', {
    product_ids: productIds, select_all: selectAll, filters,
  });
  return data;
}

export async function suspendProducts(
  productIds: number[], selectAll: boolean,
  filters: { account_id: number; status?: string; search?: string; ownerclan_soldout?: boolean },
): Promise<SuspendResult> {
  const { data } = await api.post<SuspendResult>('/smartstore/products/suspend/', {
    product_ids: productIds, select_all: selectAll, filters,
  });
  return data;
}
