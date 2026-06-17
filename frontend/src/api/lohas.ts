import api from './client';

export interface LohasJob {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'stopped';
  started_at: number;
  finished_at: number | null;
  returncode: number | null;
  log_count: number;
  logs: string[];
}

export const startRestock = async (user: string, password: string, codes: string) => {
  const { data } = await api.post<LohasJob>('/lohas/restock/', { user, password, codes });
  return data;
};

export const listCategories = async (user: string, password: string) => {
  const { data } = await api.post<LohasJob>('/lohas/bulk-edit/list-categories/', { user, password });
  return data;
};

export const runBulkEdit = async (
  user: string,
  password: string,
  mode: '1.0' | '2.0',
  categories: string[],
) => {
  const { data } = await api.post<LohasJob>('/lohas/bulk-edit/run/', {
    user,
    password,
    mode,
    categories,
  });
  return data;
};

export const getJob = async (jobId: string, since = 0) => {
  const { data } = await api.get<LohasJob>(`/lohas/jobs/${jobId}/`, { params: { since } });
  return data;
};

export const stopJob = async (jobId: string) => {
  const { data } = await api.post<LohasJob>(`/lohas/jobs/${jobId}/stop/`);
  return data;
};

export const parseCategoriesFromLogs = (logs: string[]): string[] | null => {
  for (const line of logs) {
    const m = line.match(/^CATEGORIES:\s*(.*)$/);
    if (m) {
      try {
        const arr = JSON.parse(m[1]);
        if (Array.isArray(arr)) return arr as string[];
      } catch {
        return null;
      }
    }
  }
  return null;
};
