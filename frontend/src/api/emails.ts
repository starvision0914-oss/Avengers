import api from './client';

export const getEmailAccounts = () => api.get('/emails/accounts/').then(r => r.data);
export const createEmailAccount = (data: any) => api.post('/emails/accounts/', data).then(r => r.data);
export const updateEmailAccount = (id: number, data: any) => api.put(`/emails/accounts/${id}/`, data).then(r => r.data);
export const deleteEmailAccount = (id: number) => api.delete(`/emails/accounts/${id}/`);
export const getEmailMessages = (params?: Record<string, string>) => api.get('/emails/messages/', { params }).then(r => r.data);
export const getEmailMessage = (id: number) => api.get(`/emails/messages/${id}/`).then(r => r.data);
export const updateEmailMessage = (id: number, data: any) => api.patch(`/emails/messages/${id}/`, data).then(r => r.data);
export const syncEmail = (accountId: number) => api.post('/emails/sync/', { account_id: accountId }).then(r => r.data);
export const sendEmail = (data: any) => api.post('/emails/send/', data).then(r => r.data);
export const getLabels = () => api.get('/emails/labels/').then(r => r.data);
