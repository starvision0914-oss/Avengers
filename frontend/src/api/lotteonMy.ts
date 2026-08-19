import api from './client';

export interface LotteonMyProduct {
  id: number;
  login_id: string;
  seller_name: string;
  product_no: string;
  product_name: string;
  sale_price: number;
  stock_quantity: number | null;
  status_type: string;
  status_label: string;
  seller_product_code: string;
  category: string;
  product_image_url: string;
  synced_at: string | null;
}

export interface LotteonMyListResponse {
  items: LotteonMyProduct[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface LotteonAccount {
  account_id: number;
  login_id: string;
  seller_name: string;
  product_count: number;
  has_api_key: boolean;
}

export async function fetchLotteonMyAccounts(): Promise<LotteonAccount[]> {
  const { data } = await api.get<{ id: number; login_id: string; store_name: string; product_count: number; has_api_key: boolean }[]>('/lotteon/accounts/');
  return data.map(a => ({
    account_id: a.id, login_id: a.login_id, seller_name: a.store_name,
    product_count: a.product_count, has_api_key: a.has_api_key,
  }));
}

export async function fetchLotteonMyProducts(
  page = 1, perPage = 50, accountId?: number,
  status?: string, search?: string, sort?: string, order: 'asc' | 'desc' = 'asc',
): Promise<LotteonMyListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (accountId) params.account_id = accountId;
  if (status) params.status = status;
  if (search) params.search = search;
  if (sort) { params.sort = sort; params.order = order; }
  const { data } = await api.get<LotteonMyListResponse>('/lotteon/my/products/', { params });
  return data;
}
