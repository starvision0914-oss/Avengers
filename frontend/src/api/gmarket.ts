import api from './client';
import type {
  DailySummaryResponse, TimeseriesResponse, Last15MinResponse,
  AiSummaryItem, AiHistoryRow, AdCostRow, SellerGradeItem,
  Cpc2HistoryRow, SellerOrdersResponse,
} from '../types/cpc';

export async function getDailySummary(
  date: string,
  range?: { start_date: string; end_date: string },
): Promise<DailySummaryResponse> {
  const params = range
    ? { start_date: range.start_date, end_date: range.end_date }
    : { date };
  const { data } = await api.get<DailySummaryResponse>('/cpc/gmarket-summary/', { params });
  return data;
}

export async function getTimeseries(date: string, ids: string[]): Promise<TimeseriesResponse> {
  const { data } = await api.get<TimeseriesResponse>('/cpc/timeseries/', {
    params: { date, ids: ids.join(',') },
  });
  return data;
}

export async function getLast15Min(): Promise<Last15MinResponse> {
  return { cpc_delta: 0, ai_delta: 0, prime_delta: 0, ad_delta: 0, sales_delta: 0 };
}

export async function sendTelegram(date: string, force = false) {
  const { data } = await api.post<{ sent: boolean; detail: string; changed: boolean }>(
    '/cpc/telegram/send/', { date, force },
  );
  return data;
}

export async function getAdCostDetail(
  sellerId: string,
  date: string,
  range?: { start_date: string; end_date: string },
): Promise<AdCostRow[]> {
  const params: Record<string, string> = range
    ? { seller_id: sellerId, start_date: range.start_date, end_date: range.end_date, platform: 'gmarket' }
    : { seller_id: sellerId, date, platform: 'gmarket' };
  const { data } = await api.get<{ rows: AdCostRow[] }>('/cpc/ad-detail/', { params });
  return data.rows;
}

export async function getAiSummary(): Promise<AiSummaryItem[]> {
  const { data } = await api.get('/cpc/gmarket-ai/');
  const results = data.results || data;
  return Array.isArray(results) ? results : [];
}

export async function controlAiStream(
  ids: number[],
  action: 'on' | 'off' | 'off-on',
  onLog: (msg: string) => void,
): Promise<Record<string, string>> {
  const token = localStorage.getItem('access_token');
  const resp = await fetch('/api/cpc/ai/control/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ ids, action }),
  });
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let results: Record<string, string> = {};
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop()!;
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const d = JSON.parse(line);
        if (d.t === 'log') onLog(d.m);
        if (d.t === 'done') results = d.results;
      } catch { /* skip */ }
    }
  }
  return results;
}

export async function getAiHistory(sellerId: string): Promise<AiHistoryRow[]> {
  const { data } = await api.get('/cpc/ai-history/', {
    params: { gmarket_id: sellerId },
  });
  const results = data.results || data.history || data;
  return Array.isArray(results) ? results : [];
}

export async function getTgMode(): Promise<string> {
  try {
    const { data } = await api.get('/cpc/telegram/config/');
    const results = data.results || data;
    const cfg = Array.isArray(results) ? results[0] : results;
    return cfg?.mode || 'off';
  } catch {
    return 'off';
  }
}

export async function setTgMode(mode: string): Promise<string> {
  try {
    const { data: cfgData } = await api.get('/cpc/telegram/config/');
    const results = cfgData.results || cfgData;
    const cfg = Array.isArray(results) ? results[0] : results;
    if (cfg?.id) {
      await api.put(`/cpc/telegram/config/${cfg.id}/`, { ...cfg, mode });
    }
  } catch { /* ignore */ }
  return mode;
}

export async function fetchSellerGrades(): Promise<SellerGradeItem[]> {
  const { data } = await api.get('/cpc/gmarket-grades/');
  const results = data.results || data;
  return Array.isArray(results) ? results : [];
}

export async function getCpc2History(gmarketId?: string): Promise<Cpc2HistoryRow[]> {
  const params = gmarketId ? { gmarket_id: gmarketId } : {};
  const { data } = await api.get('/cpc/cpc2-history/', { params });
  const results = data.results || data;
  return Array.isArray(results) ? results : [];
}

export async function triggerCpc2Control(
  gmarketId: string,
  action: 'on' | 'off',
  onLog: (msg: string) => void,
): Promise<Record<string, unknown>> {
  const token = localStorage.getItem('access_token');
  const res = await fetch('/api/cpc/cpc2/control/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ gmarket_id: gmarketId, action }),
  });
  const reader = res.body?.getReader();
  if (!reader) return {};
  const decoder = new TextDecoder();
  let buf = '';
  let result: Record<string, unknown> = {};
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop() || '';
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const obj = JSON.parse(line);
        if (obj.t === 'log') onLog(obj.m);
        if (obj.t === 'done') { result = obj.result || {}; return result; }
      } catch { /* skip */ }
    }
  }
  return result;
}

export async function getSellerOrders(
  sellerAlias: string,
  siteName: string,
  date: string,
  range?: { start_date: string; end_date: string },
): Promise<SellerOrdersResponse> {
  const params: Record<string, string> = { seller_alias: sellerAlias, site_name: siteName };
  if (range) {
    params.start_date = range.start_date;
    params.end_date = range.end_date;
  } else {
    params.date = date;
  }
  try {
    const { data } = await api.get<SellerOrdersResponse>('/cpc/seller-orders/', { params });
    return data;
  } catch {
    return { orders: [], summary: { count: 0, total_qty: 0, total_payment: 0, total_settle: 0, total_cost: 0, total_profit: 0 } };
  }
}
