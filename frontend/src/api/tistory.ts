import api from './client';

export interface TistoryAccount {
  id: number;
  login_id: string;
  blog_name: string;
  display_name: string;
  is_active: boolean;
  cookie_saved_at: string | null;
  memo?: string;
}

export interface TistoryPost {
  id: number;
  title: string;
  status: string;
  account_id: number | null;
  account_name: string;
  published_url: string;
  created_at: string;
}

export interface TistoryPostDetail {
  id: number;
  title: string;
  content: string;
  tags: string;
  category: string;
  status: string;
  error_message: string;
  published_url: string;
  account_id: number | null;
}

export async function getTistoryAccounts(): Promise<TistoryAccount[]> {
  const { data } = await api.get('/tistory/accounts/');
  return data;
}

export async function createTistoryAccount(payload: {
  login_id: string; login_pw: string; blog_name: string; display_name?: string; memo?: string;
}): Promise<{ id: number }> {
  const { data } = await api.post('/tistory/accounts/', payload);
  return data;
}

export async function updateTistoryAccount(id: number, payload: Partial<{
  login_id: string; login_pw: string; blog_name: string; display_name: string; memo: string; is_active: boolean;
}>): Promise<void> {
  await api.patch(`/tistory/accounts/${id}/`, payload);
}

export async function deleteTistoryAccount(id: number): Promise<void> {
  await api.delete(`/tistory/accounts/${id}/`);
}

export async function getTistoryPosts(): Promise<TistoryPost[]> {
  const { data } = await api.get('/tistory/posts/');
  return data;
}

export async function getTistoryPostDetail(id: number): Promise<TistoryPostDetail> {
  const { data } = await api.get(`/tistory/posts/${id}/`);
  return data;
}

export async function createTistoryPost(payload: {
  account_id: number; title: string; content: string; tags?: string; category?: string;
}): Promise<{ id: number }> {
  const { data } = await api.post('/tistory/posts/', payload);
  return data;
}

export async function publishTistoryPost(id: number, mode: 'draft' | 'publish'): Promise<{ ok?: boolean; status?: string; error?: string }> {
  try {
    const { data } = await api.post(`/tistory/posts/${id}/publish/`, { mode });
    return data;
  } catch (e: any) {
    return { error: e?.response?.data?.error || '요청 실패' };
  }
}

export async function generateTistoryPost(payload: {
  keyword: string; account_id: number; category?: string; extra_context?: string;
}): Promise<{ id: number; title: string; content: string; tags: string; error?: string }> {
  try {
    const { data } = await api.post('/tistory/posts/generate/', payload);
    return data;
  } catch (e: any) {
    return { id: 0, title: '', content: '', tags: '', error: e?.response?.data?.error || '생성 실패' };
  }
}
