export interface AiAdStatus {
  btn?: 'ON' | 'OFF';
  actual?: 'ON' | 'OFF';
  actual_status?: 'ON' | 'OFF';
  actual_reason?: string;
  button_status?: 'ON' | 'OFF';
  reason?: string;
  budget?: string;
  start?: string | null;
  start_date?: string | null;
}

export interface SellerRow {
  seller_id: string;
  seller_alias: string;
  balance: number;
  monthly_sales: number;
  cpc_spend: number;
  ai_spend: number;
  prime_spend: number;
  ad_total: number;
  server_fee_date: string | null;
  sales: number;
  sales_count: number;
  cost: number;
  cost_count: number;
  profit: number;
  last_tx: string | null;
  ai_status: AiAdStatus | null;
  cpc_status: { cpc1_on: number; cpc1_off: number; cpc2_on: number; cpc2_off: number } | null;
  grade_info: {
    max_item_count: number | null;
    seller_grade: string | null;
    approval_status: string | null;
    contact_expiry: string | null;
    collected_at: string | null;
  } | null;
  cpp_bid_info?: {
    bid_start: string;
    bid_end: string;
    event_time: string;
  } | null;
}

export interface TotalsSummary {
  cpc_spend: number;
  ai_spend: number;
  prime_spend: number;
  ad_total: number;
  balance?: number;
  sales: number;
  sales_count: number;
  cost: number;
  cost_count: number;
  profit: number;
  net_profit: number;
}

export interface DailySummaryResponse {
  date: string;
  sellers: SellerRow[];
  totals: TotalsSummary;
}

export interface TimeseriesRow {
  id: string;
  ts: string;
  cpc: number;
  ai: number;
  prime: number;
}

export interface SalesTimeseriesRow {
  id: string;
  ts: string;
  sales: number;
}

export interface TimeseriesResponse {
  date: string;
  data: TimeseriesRow[];
  sales: SalesTimeseriesRow[];
}

export interface Last15MinResponse {
  cpc_delta: number;
  ai_delta: number;
  prime_delta: number;
  ad_delta: number;
  sales_delta: number;
}

export type TelegramMode = 'off' | 'change' | '15m' | '1h';
export type PeriodMode = 'daily' | 'monthly' | 'yearly' | 'range';

export interface AiHistoryRow {
  event_time: string;
  history_type: string;
  detail: string;
  group_name: string;
}

export interface AdCostRow {
  time: string;
  category: string;
  description: string;
  amount: number;
  product_name: string | null;
}

export interface AiSummaryItem {
  id: number;
  gmarket_id: string;
  seller_id: string;
  group_name: string;
  button_status: 'ON' | 'OFF';
  actual_status: 'ON' | 'OFF';
  actual_reason: string;
  start_date: string | null;
  end_date: string | null;
  daily_budget: string;
  budget_mgmt: string;
  operation_status: string;
  click_count: number;
  avg_click_cost: number;
  ad_product_count: string;
  total_product_count: string;
  updated_at: string;
}

export interface SellerGradeItem {
  gmarket_id: string;
  seller_id: string;
  seller_grade: string;
  max_item_count: number;
  approval_status: string;
  contact_expiry: string | null;
  collected_at: string;
}

export interface Cpc2HistoryRow {
  gmarket_id: string;
  action: string;
  cpc2_before: number;
  cpc2_after: number;
  source: string;
  event_time: string;
}

export interface SellerOrderRow {
  order_date: string;
  site_name: string;
  order_status: string;
  quantity: number;
  payment_price: number;
  settlement_price: number;
  cost: number;
  profit: number;
  receiver_name: string;
  order_option: string;
  bid_number: string;
  product_name: string;
  product_seller_code: string;
}

export interface SellerOrdersResponse {
  orders: SellerOrderRow[];
  summary: {
    count: number;
    total_qty: number;
    total_payment: number;
    total_settle: number;
    total_cost: number;
    total_profit: number;
  };
}
