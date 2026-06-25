import api from './client';

export interface NaverBlogAccount {
  id: number;
  login_id: string;
  blog_id: string;
  display_name: string;
  memo: string;
  has_pw: boolean;
  is_active: boolean;
  display_order: number;
}

export interface NaverKeyword {
  id: number;
  keyword: string;
  category: string;
  search_pc: number;
  search_mobile: number;
  search_total: number;
  blog_count: number;
  competition: 'low' | 'mid' | 'high' | '';
  priority: number;
  is_active: boolean;
  trend_data: { period: string; ratio: number }[] | null;
  last_collected: string | null;
  post_count: number;
}

export interface NaverBlogPost {
  id: number;
  title: string;
  keyword: string;
  account: string;
  status: 'draft' | 'ready' | 'published' | 'failed';
  tags: string;
  content_length: number;
  published_url: string;
  published_at: string | null;
  created_at: string;
}

export interface NaverBlogPostDetail extends NaverBlogPost {
  content: string;
  error_message: string;
  account: any;
}

export interface BlogDashboard {
  total_keywords: number;
  total_accounts: number;
  post_status: Record<string, number>;
  competition_dist: Record<string, number>;
  has_api_key: boolean;
  has_naver_key: boolean;
  recent_posts: {
    id: number; title: string; account: string;
    keyword: string; published_at: string | null; url: string;
  }[];
}

export interface BlogSetting {
  gemini_api_key: string;
  has_gemini: boolean;
  naver_client_id: string;
  has_naver: boolean;
}

// 대시보드
export const getBlogDashboard = () =>
  api.get<BlogDashboard>('/naver-blog/dashboard/').then(r => r.data);

// 설정
export const getBlogSetting = () =>
  api.get<BlogSetting>('/naver-blog/settings/').then(r => r.data);
export const saveBlogSetting = (d: Partial<{ gemini_api_key: string; naver_client_id: string; naver_client_secret: string }>) =>
  api.post('/naver-blog/settings/', d).then(r => r.data);

// 계정
export const getBlogAccounts = () =>
  api.get<NaverBlogAccount[]>('/naver-blog/accounts/').then(r => r.data);
export const createBlogAccount = (d: Partial<NaverBlogAccount> & { login_pw?: string }) =>
  api.post('/naver-blog/accounts/', d).then(r => r.data);
export const updateBlogAccount = (id: number, d: Partial<NaverBlogAccount> & { login_pw?: string }) =>
  api.patch(`/naver-blog/accounts/${id}/`, d).then(r => r.data);
export const deleteBlogAccount = (id: number) =>
  api.delete(`/naver-blog/accounts/${id}/`).then(r => r.data);

// 키워드
export const getKeywords = (params?: { q?: string; competition?: string; active?: string }) =>
  api.get<NaverKeyword[]>('/naver-blog/keywords/', { params }).then(r => r.data);
export const addKeywords = (keywords: string, category?: string, priority?: number) =>
  api.post('/naver-blog/keywords/', { keywords, category, priority }).then(r => r.data);
export const updateKeyword = (id: number, d: Partial<NaverKeyword>) =>
  api.patch(`/naver-blog/keywords/${id}/`, d).then(r => r.data);
export const deleteKeyword = (id: number) =>
  api.delete(`/naver-blog/keywords/${id}/`).then(r => r.data);
export const collectKeywords = (keywords?: string) =>
  api.post('/naver-blog/keywords/collect/', { keywords }).then(r => r.data);

// 포스트
export const getPosts = (params?: { status?: string; account_id?: number }) =>
  api.get<NaverBlogPost[]>('/naver-blog/posts/', { params }).then(r => r.data);
export const getPostDetail = (id: number) =>
  api.get<NaverBlogPostDetail>(`/naver-blog/posts/${id}/`).then(r => r.data);
export const updatePost = (id: number, d: Partial<NaverBlogPostDetail>) =>
  api.patch(`/naver-blog/posts/${id}/`, d).then(r => r.data);
export const deletePost = (id: number) =>
  api.delete(`/naver-blog/posts/${id}/`).then(r => r.data);
export const publishPost = (id: number) =>
  api.post(`/naver-blog/posts/${id}/publish/`).then(r => r.data);

// 제미나이 글 생성 (multipart)
export const generatePostGemini = (
  keyword: string, category: string, context: string,
  accountId: number | '', images: File[], status: string
) => {
  const form = new FormData();
  form.append('keyword', keyword);
  form.append('category', category);
  form.append('context', context);
  form.append('status', status);
  if (accountId) form.append('account_id', String(accountId));
  images.forEach(img => form.append('images', img));
  return api.post('/naver-blog/posts/generate/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 90000,
  }).then(r => r.data);
};

// 수동 생성
export const createManualPost = (d: {
  title: string; content: string; tags: string;
  keyword: string; account_id: number | null; status: string;
}) => api.post('/naver-blog/posts/manual/', d).then(r => r.data);
