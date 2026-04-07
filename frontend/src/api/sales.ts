import api from './client';

export const getSalesRecords = (params?: Record<string, string>) => api.get('/sales/records/', { params }).then(r => r.data);
export const createSalesRecord = (data: any) => api.post('/sales/records/', data).then(r => r.data);
export const updateSalesRecord = (id: number, data: any) => api.put(`/sales/records/${id}/`, data).then(r => r.data);
export const deleteSalesRecord = (id: number) => api.delete(`/sales/records/${id}/`);
export const uploadCSV = (formData: FormData) => api.post('/sales/upload/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
export const getSalesSummary = (params?: Record<string, string>) => api.get('/sales/summary/', { params }).then(r => r.data);
export const getUploadLogs = () => api.get('/sales/upload-logs/').then(r => r.data);
