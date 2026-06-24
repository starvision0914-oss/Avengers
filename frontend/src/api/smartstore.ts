import api from './client';

export interface SmartStoreAccount {
  id: number;
  login_id: string;
  store_name: string;
  store_slug: string;
  display_name: string;
  memo: string;
  has_pw: boolean;
  is_active: boolean;
  display_order: number;
}

export interface DashboardSummary {
  total_sales: number;
  total_cancel: number;
  total_return: number;
  total_settlement: number;
  total_orders: number;
  total_ad_cost: number;
  total_clicks: number;
  total_conversion: number;
  roas: number | null;
}

export interface AccountRow {
  account_id: number;
  account_name: string;
  sales: number;
  settlement: number;
  orders: number;
  ad_cost: number;
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

export async function getAccounts(): Promise<SmartStoreAccount[]> {
  const { data } = await api.get<SmartStoreAccount[]>('/smartstore/accounts/');
  return data;
}

export async function createAccount(payload: Partial<SmartStoreAccount> & { login_pw?: string }): Promise<{ id: number }> {
  const { data } = await api.post('/smartstore/accounts/', payload);
  return data;
}

export async function updateAccount(id: number, payload: Partial<SmartStoreAccount> & { login_pw?: string }): Promise<void> {
  await api.patch(`/smartstore/accounts/${id}/`, payload);
}

export async function deleteAccount(id: number): Promise<void> {
  await api.delete(`/smartstore/accounts/${id}/`);
}

export async function getDashboard(params: {
  start?: string;
  end?: string;
  account_id?: number[];
}): Promise<DashboardResponse> {
  const { data } = await api.get<DashboardResponse>('/smartstore/dashboard/', { params });
  return data;
}
