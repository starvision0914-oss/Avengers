import api from './client';

export const getCrawlerAccounts = (params?: Record<string, string>) => api.get('/cpc/crawler/accounts/', { params }).then(r => r.data);
export const createCrawlerAccount = (data: any) => api.post('/cpc/crawler/accounts/', data).then(r => r.data);
export const updateCrawlerAccount = (id: number, data: any) => api.put(`/cpc/crawler/accounts/${id}/`, data).then(r => r.data);
export const deleteCrawlerAccount = (id: number) => api.delete(`/cpc/crawler/accounts/${id}/`);
export const getCrawlerLogs = (params?: Record<string, string>) => api.get('/cpc/crawler/logs/', { params }).then(r => r.data);
export const triggerCrawl = (data: { platform: string; type: string; accounts?: string[] }) => api.post('/cpc/crawler/trigger/', data).then(r => r.data);
export const getGmarketSnapshots = (params?: Record<string, string>) => api.get('/cpc/gmarket-snapshots/', { params }).then(r => r.data);
export const getElevenCosts = (params?: Record<string, string>) => api.get('/cpc/eleven-costs/', { params }).then(r => r.data);
export const getGmarketGrades = (params?: Record<string, string>) => api.get('/cpc/gmarket-grades/', { params }).then(r => r.data);
export const getElevenGrades = (params?: Record<string, string>) => api.get('/cpc/eleven-grades/', { params }).then(r => r.data);
export const getGmarketSummary = (params?: Record<string, string>) => api.get('/cpc/gmarket-summary/', { params }).then(r => r.data);
export const getElevenSummary = (params?: Record<string, string>) => api.get('/cpc/eleven-summary/', { params }).then(r => r.data);
export const getGmarketAi = (params?: Record<string, string>) => api.get('/cpc/gmarket-ai/', { params }).then(r => r.data);
export const getSt11Campaigns = (params?: Record<string, string>) => api.get('/cpc/st11-campaigns/', { params }).then(r => r.data);
