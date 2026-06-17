export interface St11SellerRow {
  seller_id: string;
  seller_alias: string;
  balance: number;
  cpc_spend: number;
  ad_total: number;
  last_tx: string | null;
  charge: number;
  tx_count: number;
  cost_type?: string;
  crawling_status?: string;
  fail_count?: number;
  no_api?: boolean;
  last_otp_at?: string | null;
  grade?: number | null;
  grade_message?: string | null;
  // 오피스 현황
  cash?: number;
  point?: number;
  ad_balance?: number;
  products?: number;
  product_limit?: number;
  available?: number;
  overdue?: number;
  undelivered?: number;
  draft?: number;
  fulfillment?: string;
  shipping?: string;
  inquiry?: string;
  office_collected_at?: string | null;
  // 매출/구매가/순수익 (매출데이터 기준)
  sales?: number;
  cost?: number;
  prod_profit?: number;
  server_fee?: number;
  reward?: number;
  net_profit?: number;
  sales_count?: number;
}

export interface St11TotalsSummary {
  cpc_spend: number;
  ad_total: number;
  charge: number;
  balance: number;
  seller_count: number;
  // 오피스 합계
  cash: number;
  point: number;
  products: number;
  product_limit: number;
  available: number;
  sales: number;
  cost: number;
  server_fee: number;
  reward: number;
  net_profit: number;
}

export interface St11UnmatchedShop {
  name: string;
  sales: number;
  cost: number;
  net_profit: number;
  count: number;
}

export interface St11Unmatched {
  sales: number;
  cost: number;
  net_profit: number;
  count: number;
  shops: St11UnmatchedShop[];
}

export interface St11SummaryResponse {
  date: string;
  sellers: St11SellerRow[];
  totals: St11TotalsSummary;
  unmatched?: St11Unmatched;
  last_collected_at: string | null;
}

export interface St11TimeseriesRow {
  id: string;
  ts: string;
  cpc: number;
}

export interface St11Last15MinResponse {
  cpc_delta: number;
  ad_delta: number;
  sales_delta: number;
}

export interface St11CostRow {
  time: string;
  category: string;
  description: string;
  amount: number;
}
