import axios from 'axios';

export enum DownloadStatus {
  QUEUED = 'queued',
  DOWNLOADING = 'downloading',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface DownloadInfo {
  id: string;
  url: string;
  filename: string;
  dest_path: string;
  status: DownloadStatus;
  total_bytes: number;
  received_bytes: number;
  speed_bps: number;
  connections: number;
  adaptive: boolean;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface DownloadRequest {
  url: string;
  filename?: string;
  connections?: number;
  adaptive?: boolean;
}

export interface Settings {
  download_dir: string;
  default_connections: number;
  adaptive_default: boolean;
}

const api = axios.create({
  baseURL: '/api',
});

export const downloadsApi = {
  getAll: () => api.get<DownloadInfo[]>('/downloads'),
  get: (id: string) => api.get<DownloadInfo>(`/downloads/${id}`),
  create: (data: DownloadRequest) => api.post<{ id: string }>('/downloads', data),
  pause: (id: string) => api.post(`/downloads/${id}/pause`),
  resume: (id: string) => api.post(`/downloads/${id}/resume`),
  cancel: (id: string) => api.post(`/downloads/${id}/cancel`),
  remove: (id: string) => api.delete(`/downloads/${id}`),
};

export const settingsApi = {
  get: () => api.get<Settings>('/settings'),
  update: (data: Partial<Settings>) => api.patch<Settings>('/settings', data),
};

export default api;
