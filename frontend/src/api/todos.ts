import api from './client';

export const getMembers = () => api.get('/todos/members/').then(r => r.data);
export const createMember = (data: any) => api.post('/todos/members/', data).then(r => r.data);
export const getProjects = () => api.get('/todos/projects/').then(r => r.data);
export const createProject = (data: any) => api.post('/todos/projects/', data).then(r => r.data);
export const updateProject = (id: number, data: any) => api.put(`/todos/projects/${id}/`, data).then(r => r.data);
export const deleteProject = (id: number) => api.delete(`/todos/projects/${id}/`);
export const getTasks = (params?: Record<string, string>) => api.get('/todos/tasks/', { params }).then(r => r.data);
export const createTask = (data: any) => api.post('/todos/tasks/', data).then(r => r.data);
export const updateTask = (id: number, data: any) => api.put(`/todos/tasks/${id}/`, data).then(r => r.data);
export const moveTask = (id: number, data: any) => api.patch(`/todos/tasks/${id}/move/`, data).then(r => r.data);
export const deleteTask = (id: number) => api.delete(`/todos/tasks/${id}/`);
export const getComments = (taskId: number) => api.get(`/todos/tasks/${taskId}/comments/`).then(r => r.data);
export const createComment = (taskId: number, data: any) => api.post(`/todos/tasks/${taskId}/comments/`, data).then(r => r.data);
