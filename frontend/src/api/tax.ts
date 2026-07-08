import api from './client';

export interface TaxVatMember {
  platform: string;
  platform_label: string;
  login_id: string;
  seller_name: string;
  months: Record<string, number>;
  total: number;
}

export interface TaxVatAccount {
  group: string;
  rep_login_id: string;
  member_count: number;
  months: Record<string, number>;
  total: number;
  members: TaxVatMember[];
}

export interface TaxVatSummary {
  year: number;
  progress: { collected: number; target: number; last_collected_at: string | null };
  accounts: TaxVatAccount[];
  monthly_totals: Record<string, number>;
  grand_total: number;
  vat_payable: number;
}

export async function getTaxVatSummary(year = 2026, platform = '11st'): Promise<TaxVatSummary> {
  const { data } = await api.get('/cpc/tax/vat/', { params: { year, platform } });
  return data;
}

export type TaxVatCrawlStatus = Record<string, { busy: boolean }>;

export async function getTaxVatCrawlStatus(): Promise<TaxVatCrawlStatus> {
  const { data } = await api.get('/cpc/tax/vat/crawl/');
  return data;
}

export async function startTaxVatCrawl(platform: string, year: number): Promise<{ status: string; error?: string; platforms?: string[] }> {
  const { data } = await api.post('/cpc/tax/vat/crawl/', { platform, year });
  return data;
}
