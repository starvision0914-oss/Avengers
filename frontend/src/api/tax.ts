import api from './client';

export interface TaxVatAccount {
  group: string;
  rep_login_id: string;
  member_count: number;
  months: Record<string, number>;
  total: number;
}

export interface TaxVatSummary {
  year: number;
  progress: { collected: number; target: number; last_collected_at: string | null };
  accounts: TaxVatAccount[];
  monthly_totals: Record<string, number>;
  grand_total: number;
  vat_payable: number;
}

export async function getTaxVatSummary(year = 2026): Promise<TaxVatSummary> {
  const { data } = await api.get('/cpc/tax/vat/', { params: { year } });
  return data;
}
