import api from './client';
import type { SellerAccount } from '../types';

export const getAccounts = () => api.get<SellerAccount[]>('/accounts/sellers/').then(r => r.data);
export const createAccount = (data: Partial<SellerAccount>) => api.post('/accounts/sellers/', data).then(r => r.data);
export const updateAccount = (id: number, data: Partial<SellerAccount>) => api.put(`/accounts/sellers/${id}/`, data).then(r => r.data);
export const deleteAccount = (id: number) => api.delete(`/accounts/sellers/${id}/`);
