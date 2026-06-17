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
}

export interface GmarketMyListResponse {
  items: GmarketMyProduct[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
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
  dedup = false,
): Promise<GmarketMyListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (accountId) params.account_id = accountId;
  if (market) params.market = market;
  if (status) params.status = status;
  if (search) params.search = search;
  if (sort) { params.sort = sort; params.order = order; }
  if (dedup) params.dedup = 1;
  const { data } = await api.get<GmarketMyListResponse>(`${base}/products/`, { params });
  return data;
}

export async function exportGmarketMyProducts(
  accountId?: number, market?: string, status?: string, search?: string, dedup = false,
): Promise<Blob> {
  const params: Record<string, string | number> = { export: 1 };
  if (accountId) params.account_id = accountId;
  if (market) params.market = market;
  if (status) params.status = status;
  if (search) params.search = search;
  if (dedup) params.dedup = 1;
  const resp = await api.get(`${base}/products/`, { params, responseType: 'blob' });
  return resp.data as Blob;
}
