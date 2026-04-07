import api from './client';

export const getDailyCosts = (params?: Record<string, string>) => api.get('/cpc/daily/', { params }).then(r => r.data);
export const createDailyCost = (data: any) => api.post('/cpc/daily/', data).then(r => r.data);
export const updateDailyCost = (id: number, data: any) => api.put(`/cpc/daily/${id}/`, data).then(r => r.data);
export const deleteDailyCost = (id: number) => api.delete(`/cpc/daily/${id}/`);
export const getDeposits = (params?: Record<string, string>) => api.get('/cpc/deposits/', { params }).then(r => r.data);
export const createDeposit = (data: any) => api.post('/cpc/deposits/', data).then(r => r.data);
export const getTransactions = (params?: Record<string, string>) => api.get('/cpc/transactions/', { params }).then(r => r.data);
export const createTransaction = (data: any) => api.post('/cpc/transactions/', data).then(r => r.data);
export const getSummary = (date?: string) => api.get('/cpc/summary/', { params: { date } }).then(r => r.data);
export const getChart = (params?: Record<string, string>) => api.get('/cpc/chart/', { params }).then(r => r.data);
