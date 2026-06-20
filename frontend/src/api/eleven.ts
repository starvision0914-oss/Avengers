import api from './client';
import type { St11SummaryResponse, St11Last15MinResponse, St11CostRow } from '../types/st11';
import type { SalesTimeseriesRow } from '../types/cpc';

export async function getSt11Summary(
  date: string,
  range?: { start_date: string; end_date: string },
): Promise<St11SummaryResponse> {
  const params = range
    ? { date_from: range.start_date, date_to: range.end_date }
    : { date };
  const { data } = await api.get('/cpc/eleven-summary/', { params });
  const sellers = (data.sellers || []).map((s: any) => ({
    seller_id: s.seller_id,
    seller_alias: s.seller_alias || s.seller_id,
    balance: s.balance || 0,
    cpc_spend: s.cpc_spend || 0,
    ad_total: s.ad_total || s.cpc_spend || 0,
    last_tx: s.last_crawled_at || null,
    charge: s.charge || 0,
    tx_count: s.tx_count || 0,
    cost_type: s.cost_type || 'sellerpoint',
    crawling_status: s.crawling_status || '',
    fail_count: s.fail_count || 0,
    no_api: s.no_api || false,
    last_otp_at: s.last_otp_at || null,
    cookie_saved_at: s.cookie_saved_at || null,
    grade: s.grade ?? null,
    grade_message: s.grade_message || '',
    cash: s.cash || 0,
    point: s.point || 0,
    ad_balance: s.ad_balance || 0,
    products: s.products || 0,
    product_limit: s.product_limit || 0,
    available: s.available || 0,
    overdue: s.overdue || 0,
    undelivered: s.undelivered || 0,
    draft: s.draft || 0,
    fulfillment: s.fulfillment || '',
    shipping: s.shipping || '',
    inquiry: s.inquiry || '',
    office_collected_at: s.office_collected_at || null,
    sales: s.sales || 0,
    cost: s.cost || 0,
    prod_profit: s.prod_profit || 0,
    server_fee: s.server_fee || 0,
    reward: s.reward || 0,
    net_profit: s.net_profit || 0,
    sales_count: s.sales_count || 0,
  }));
  const t = data.totals || {};
  const totals = {
    cpc_spend: t.cpc_spend || 0,
    ad_total: t.ad_total || t.cpc_spend || 0,
    charge: t.charge || 0,
    balance: t.balance || 0,
    seller_count: t.seller_count || sellers.length,
    cash: t.cash || 0,
    point: t.point || 0,
    products: t.products || 0,
    product_limit: t.product_limit || 0,
    available: t.available || 0,
    sales: t.sales || 0,
    cost: t.cost || 0,
    server_fee: t.server_fee || 0,
    reward: t.reward || 0,
    net_profit: t.net_profit || 0,
  };
  return { date: data.date || date, sellers, totals, unmatched: data.unmatched || { sales: 0, count: 0, shops: [] }, last_collected_at: data.last_collected_at || null };
}

export async function getSt11Last15Min(): Promise<St11Last15MinResponse> {
  return { cpc_delta: 0, ad_delta: 0, sales_delta: 0 };
}

export async function getSt11Timeseries(
  date: string,
  ids: string[],
): Promise<{ date: string; data: any[]; sales: SalesTimeseriesRow[] }> {
  return { date, data: [], sales: [] };
}

export async function getSt11CostDetail(
  sellerId: string,
  date: string,
  range?: { start_date: string; end_date: string },
  kind?: string,
): Promise<St11CostRow[]> {
  const params: Record<string, string> = { seller_id: sellerId, platform: '11st' };
  if (kind) params.kind = kind;
  if (range) {
    params.date_from = range.start_date;
    params.date_to = range.end_date;
  } else {
    params.date = date;
  }
  const { data } = await api.get<{ rows: St11CostRow[] }>('/cpc/ad-detail/', { params });
  return data.rows;
}
