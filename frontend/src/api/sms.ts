import api from './client';

// 수신 문자
export const getLatestSmsList = (params?: { limit?: number; since_id?: number }) =>
  api.get('/cpc/sms/latest/', { params }).then(r => r.data);

// 발송 (서버 → smsApp outbox)
export const createOutboxSms = (data: {
  phone_number: string;
  message: string;
  sender_phone?: string;
  template_id?: number | null;
}) => api.post('/cpc/sms/outbox/', data).then(r => r.data);

export const getOutboxPending = () => api.get('/cpc/sms/outbox/').then(r => r.data);

export const getOutboxHistory = (params?: { limit?: number; status?: string }) =>
  api.get('/cpc/sms/outbox/history/', { params }).then(r => r.data);

// 디바이스 (smsApp 폰)
export const getSmsDevices = () => api.get('/cpc/sms/devices/').then(r => r.data);

export const changeDevicePhone = (data: { old_phone: string; new_phone: string }) =>
  api.post('/cpc/sms/devices/change-number/', data).then(r => r.data);

// 폰 설정
export const getSmsPhoneSettings = () => api.get('/cpc/sms/phones/').then(r => r.data);
export const addSmsPhoneSetting = (data: { phone_number: string; name?: string }) =>
  api.post('/cpc/sms/phones/', data).then(r => r.data);
export const removeSmsPhoneSetting = (id: number) =>
  api.delete('/cpc/sms/phones/', { data: { id } }).then(r => r.data);
