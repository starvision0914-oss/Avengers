import api from './client';
import type { UploadTaskStart, UploadTaskStatus } from './ownerclan';

export interface MyProductItem {
  id: number;
  my_product_code: string;
  source_product_code: string;
  is_modified: number;
  product_name: string;
  market_product_name: string;
  ownerclan_price: number;
  market_price: number;
  shipping_fee: number;
  return_fee: number;
  image_large: string;
  image_small: string;
  category_code: string;
  category_name: string;
  manufacturer: string;
  origin: string;
  market_gmarket: string;
  market_auction: string;
  market_11st: string;
  market_coupang: string;
  market_smartstore: string;
  copied_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MyProductListResponse {
  items: MyProductItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface MyProductDetail {
  id: number;
  my_product_code: string;
  source_product_code: string;
  is_modified: number;
  copied_at: string | null;
  source: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface DistinctValue { value: string; count: number; }
export type FilterableColumn = 'category_name' | 'category_code' | 'manufacturer' | 'origin' | 'shipping_type' | 'brand';
export type MySortColumn = 'my_product_code' | 'source_product_code' | 'category_code' | 'ownerclan_price' | 'market_price' | 'shipping_fee' | 'copied_at';
export type SortOrder = 'asc' | 'desc';

const base = '/ownerclan/my';

export async function fetchMyProducts(
  page = 1, perPage = 50,
  search?: string,
  isModified?: number,
  sort?: MySortColumn,
  order: SortOrder = 'asc',
  filterCol?: string,
  filterVals?: string[],
  codes?: string[],
): Promise<MyProductListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (search) params.search = search;
  if (isModified !== undefined) params.is_modified = isModified;
  if (sort) { params.sort = sort; params.order = order; }
  if (filterCol && filterVals && filterVals.length > 0) {
    params.filter_col = filterCol;
    params.filter_vals = filterVals.join('|');
  }
  if (codes && codes.length > 0) params.codes = codes.join(',');
  const { data } = await api.get<MyProductListResponse>(`${base}/products/`, { params });
  return data;
}

export async function fetchMyProductDetail(id: number): Promise<MyProductDetail> {
  const { data } = await api.get<MyProductDetail>(`${base}/products/${id}/`);
  return data;
}

export async function updateMyProduct(id: number, fields: Record<string, string>): Promise<{ updated: number; fields?: string[] }> {
  const { data } = await api.patch(`${base}/products/${id}/`, fields);
  return data;
}

export async function deleteMyProduct(id: number): Promise<{ deleted: number }> {
  const { data } = await api.delete(`${base}/products/${id}/`);
  return data;
}

export async function copyFromReserve(sourceCodes: string[], workspace?: string): Promise<{ created: number; errors: string[] }> {
  const params = workspace === 'processing' ? { workspace } : {};
  const { data } = await api.post(`${base}/copy/`, { source_product_codes: sourceCodes }, { params });
  return data;
}

export async function deleteAllMyProducts(): Promise<{ deleted: number }> {
  const { data } = await api.post(`${base}/products/delete-all/`, { confirm: 'DELETE_ALL' });
  return data;
}

export async function deleteMyProductsByIds(ids: number[]): Promise<{ deleted: number }> {
  const { data } = await api.post(`${base}/products/delete-ids/`, { ids });
  return data;
}

export async function dedupeMyByName(): Promise<{ deleted: number; higher_price_removed: number; same_price_removed: number }> {
  const { data } = await api.post(`${base}/products/dedupe/`, {});
  return data;
}

export async function fetchMyDistinctValues(column: FilterableColumn): Promise<DistinctValue[]> {
  const { data } = await api.get<{ values: DistinctValue[] }>(`${base}/products/distinct/`, { params: { column } });
  return data.values;
}

interface MyExportParams {
  search?: string;
  isModified?: number;
  filterCol?: string;
  filterVals?: string[];
}

function _params(p: MyExportParams): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (p.search) params.search = p.search;
  if (p.isModified !== undefined) params.is_modified = p.isModified;
  if (p.filterCol && p.filterVals && p.filterVals.length > 0) {
    params.filter_col = p.filterCol;
    params.filter_vals = p.filterVals.join('|');
  }
  return params;
}

export async function fetchMyWCodes(p: MyExportParams): Promise<string[]> {
  const { data } = await api.get<{ codes: string[]; count: number }>(`${base}/products/wcodes/`, { params: _params(p) });
  return data.codes;
}

export async function downloadMyExcel(p: MyExportParams): Promise<void> {
  const resp = await api.get(`${base}/products/excel/`, {
    params: _params(p), responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const a = document.createElement('a');
  a.href = url;
  a.download = `my_products_${new Date().toISOString().slice(0, 10)}.xlsx`;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function uploadMyExcel(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadTaskStart> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<UploadTaskStart>('/ownerclan/my/products/upload/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total && e.total > 0)
        onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function fetchMyUploadTask(taskId: number): Promise<UploadTaskStatus> {
  const { data } = await api.get<UploadTaskStatus>('/ownerclan/my/products/upload/', {
    params: { task_id: taskId },
  });
  return data;
}
