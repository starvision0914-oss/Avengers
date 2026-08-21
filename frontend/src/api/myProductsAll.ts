import api from './client';

export interface MyProductAllItem {
  id: number;
  platform: '11st' | 'gmarket' | 'coupang' | 'smartstore' | 'lotteon';
  login_id: string;
  seller_name: string;
  is_focused: boolean | null;
  market: string | null;             // gmarket|auction (지마켓만)
  product_no: number | string;
  product_name: string;
  sale_price: number | null;         // 쿠팡은 판매가 데이터 없음(null)
  stock_quantity: number | null;     // 쿠팡은 재고 데이터 없음(null)
  status_type: string;
  status_label: string;
  seller_product_code: string;
  category: string;
  product_image_url: string;
  synced_at: string | null;
  purchase_cost: number | null;      // 11번가만
  cost_diff: number | null;          // 11번가만
  cost_pct?: number | null;          // 판매가/마켓가*100 (11번가·지마켓만)
}

export interface MyProductAllResponse {
  items: MyProductAllItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  needs_check_total: number | null;
  no_match_total: number | null;
}

export async function exportAllMyProducts(
  status?: string, search?: string,
  needsCheck?: boolean, noMatch?: boolean, needsCheckPct?: number,
): Promise<Blob> {
  const params: Record<string, string | number> = { export: '1' };
  if (status) params.status = status;
  if (search) params.search = search;
  if (needsCheck) params.needs_check = '1';
  if (noMatch) params.no_match = '1';
  if (needsCheckPct != null) params.needs_check_pct = needsCheckPct;
  const resp = await api.get('/cpc/my-products/', { params, responseType: 'blob' });
  return resp.data as Blob;
}

export async function fetchAllMyProducts(
  page = 1,
  perPage = 50,
  status?: string,
  search?: string,
  sort?: string,
  order?: 'asc' | 'desc',
  needsCheck?: boolean,
  dedup?: boolean,
  noMatch?: boolean,
  needsCheckPct?: number,
): Promise<MyProductAllResponse> {
  const { data } = await api.get<MyProductAllResponse>('/cpc/my-products/', {
    params: {
      page, per_page: perPage, status, search, sort, order,
      needs_check: needsCheck ? 1 : undefined,
      dedup: dedup ? 1 : undefined,
      no_match: noMatch ? 1 : undefined,
      needs_check_pct: needsCheckPct,
    },
  });
  return data;
}
