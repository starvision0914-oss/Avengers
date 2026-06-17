import api from './client';

export interface OverviewMarket {
  key: string;
  label: string;
  color: string;
  ad_cost: number;
  cpc: number;
  ai: number;
  balance: number;
  accounts: number;
  normal: number;
  failed: number;
  cash?: number;
  point?: number;
  sales?: number;
  profit?: number;
  last_collected?: string | null;
}

export interface OverviewResponse {
  date: string;
  totals: {
    ad_cost: number;
    balance: number;
    accounts: number;
    normal: number;
    failed: number;
    sales: number;
    profit: number;
  };
  markets: OverviewMarket[];
  alerts: {
    failed_accounts: { platform: string; login_id: string; seller_name: string; status: string }[];
    low_balance: { platform: string; seller: string; balance: number }[];
    zero_ad: { platform: string; seller: string }[];
  };
  last_collected: string | null;
}

export async function getOverview(date?: string): Promise<OverviewResponse> {
  const { data } = await api.get('/cpc/overview/', { params: date ? { date } : {} });
  return data;
}
