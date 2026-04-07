import api from './client';

export const getRooms = () => api.get('/messaging/rooms/').then(r => r.data);
export const createRoom = (data: any) => api.post('/messaging/rooms/', data).then(r => r.data);
export const getMessages = (roomId: number) => api.get(`/messaging/rooms/${roomId}/messages/`).then(r => r.data);
export const sendMessage = (roomId: number, data: any) => api.post(`/messaging/rooms/${roomId}/messages/`, data).then(r => r.data);
