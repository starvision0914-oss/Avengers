import api from './client';

export interface OwnerclanProductItem {
  id: number;
  product_code: string;
  product_name: string;
  orig_product_name: string;
  market_product_name: string;
  orig_market_product_name: string;
  ownerclan_price: number;
  orig_ownerclan_price: number;
  market_price: number;
  orig_market_price: number;
  consumer_price: number;
  orig_consumer_price: number;
  shipping_fee: number;
  orig_shipping_fee: number;
  return_fee: number;
  orig_return_fee: number;
  image_large: string;
  orig_image_large: string;
  image_small: string;
  sale_status: number;
  is_synced: number;
  category_code: string;
  category_name: string;
  manufacturer: string;
  origin: string;
  market_gmarket: string;
  market_auction: string;
  market_11st: string;
  market_coupang: string;
  market_smartstore: string;
  uploaded_at: string | null;
  synced_at: string | null;
  created_at: string;
}

export interface ProductListResponse {
  items: OwnerclanProductItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ProductDetail {
  id: number;
  product_code: string;
  sale_status: number;
  is_synced: number;
  synced_at: string | null;
  uploaded_at: string | null;
  changed_fields: string[];
  [key: string]: unknown;
}

export interface ProductStats {
  total: number;
  selling: number;
  soldout: number;
  discontinued: number;
  changed: number;
  unsynced: number;
}

export type ChangedFieldCounts = Record<string, number>;

export interface UploadTaskStart {
  task_id: number;
  status: string;
}

export interface UploadTaskStatus {
  task_id: number;
  status: 'pending' | 'running' | 'done' | 'error';
  result_data: {
    progress?: number;
    inserted?: number;
    updated?: number;
    skipped?: number;
    total_rows?: number;
    total?: number;
    error?: string;
    stage?: string;
  };
}

const base = '/keyword/products';

export type SortColumn = 'product_code' | 'category_code' | 'ownerclan_price' | 'market_price' | 'shipping_fee' | 'uploaded_at';
export type SortOrder = 'asc' | 'desc';

export async function fetchProducts(
  page = 1,
  perPage = 50,
  saleStatus?: number,
  isSynced?: number,
  search?: string,
  changedField?: string,
  sort?: SortColumn,
  order: SortOrder = 'asc',
  filterCol?: string,
  filterVals?: string[],
  codes?: string[],
): Promise<ProductListResponse> {
  const params: Record<string, string | number> = { page, per_page: perPage };
  if (saleStatus !== undefined) params.sale_status = saleStatus;
  if (isSynced !== undefined) params.is_synced = isSynced;
  if (search) params.search = search;
  if (changedField) params.changed_field = changedField;
  if (sort) { params.sort = sort; params.order = order; }
  if (codes && codes.length > 0) params.codes = codes.join(',');
  if (filterCol && filterVals && filterVals.length > 0) {
    params.filter_col = filterCol;
    params.filter_vals = filterVals.join('|');
  }
  const { data } = await api.get<ProductListResponse>(`${base}/`, { params });
  return data;
}

export async function fetchProductDetail(id: number): Promise<ProductDetail> {
  const { data } = await api.get<ProductDetail>(`${base}/${id}/`);
  return data;
}

export async function fetchStats(): Promise<ProductStats> {
  const { data } = await api.get<ProductStats>(`${base}/stats/`);
  return data;
}

export async function fetchChangedFieldCounts(): Promise<ChangedFieldCounts> {
  const { data } = await api.get<ChangedFieldCounts>(`${base}/changed-fields/`);
  return data;
}

export async function uploadExcel(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadTaskStart> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<UploadTaskStart>(`${base}/upload/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total && e.total > 0)
        onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function fetchUploadTask(taskId: number): Promise<UploadTaskStatus> {
  const { data } = await api.get<UploadTaskStatus>(`${base}/upload/`, { params: { task_id: taskId } });
  return data;
}

export async function uploadCsv(file: File, onProgress?: (pct: number) => void): Promise<{ updated: number }> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<{ updated: number }>(`${base}/csv-upload/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total && e.total > 0)
        onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function uploadSoldoutTxt(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<{ total_codes: number; ownerclan_matched: number; ownerclan_updated: number }> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post(`${base}/soldout-txt/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
    onUploadProgress: (e) => {
      if (onProgress && e.total && e.total > 0)
        onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function syncProducts(productIds?: number[]): Promise<{ synced: number }> {
  const { data } = await api.post<{ synced: number }>(`${base}/sync/`, {
    product_ids: productIds || null,
  });
  return data;
}

interface ExportParams {
  saleStatus?: number;
  isSynced?: number;
  search?: string;
  changedField?: string;
}

function _buildExportParams(p: ExportParams): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (p.saleStatus !== undefined) params.sale_status = p.saleStatus;
  if (p.isSynced !== undefined) params.is_synced = p.isSynced;
  if (p.search) params.search = p.search;
  if (p.changedField) params.changed_field = p.changedField;
  return params;
}

export async function downloadProductExcel(p: ExportParams, onProgress?: (pct: number) => void): Promise<void> {
  const resp = await api.get(`${base}/excel/`, {
    params: _buildExportParams(p),
    responseType: 'blob',
    onDownloadProgress: (e) => {
      if (onProgress) {
        if (e.total && e.total > 0) onProgress(Math.round((e.loaded / e.total) * 100));
        else onProgress(-1);
      }
    },
  });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const a = document.createElement('a');
  a.href = url;
  a.download = `ownerclan_products_${new Date().toISOString().slice(0, 10)}.xlsx`;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function fetchWCodes(p: ExportParams, onProgress?: (pct: number) => void): Promise<string[]> {
  const { data } = await api.get<{ codes: string[]; count: number }>(`${base}/wcodes/`, {
    params: _buildExportParams(p),
    onDownloadProgress: (e) => {
      if (onProgress) {
        if (e.total && e.total > 0) onProgress(Math.round((e.loaded / e.total) * 100));
        else onProgress(-1);
      }
    },
  });
  return data.codes;
}

export async function deleteAllProducts(): Promise<{ deleted: number }> {
  const { data } = await api.post(`${base}/delete-all/`, { confirm: 'DELETE_ALL' });
  return data;
}

export async function deleteProductsByIds(ids: number[]): Promise<{ deleted: number }> {
  const { data } = await api.post(`${base}/delete-ids/`, { ids });
  return data;
}

export async function dedupeByName(): Promise<{ deleted: number; higher_price_removed: number; same_price_removed: number }> {
  const { data } = await api.post(`${base}/dedupe/`, {});
  return data;
}

export type FilterableColumn = 'category_name' | 'category_code' | 'manufacturer' | 'origin' | 'shipping_type' | 'brand';

export interface DistinctValue {
  value: string;
  count: number;
}

export async function fetchDistinctValues(column: FilterableColumn): Promise<DistinctValue[]> {
  const { data } = await api.get<{ values: DistinctValue[] }>(`${base}/distinct/`, { params: { column } });
  return data.values;
}
