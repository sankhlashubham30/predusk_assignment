export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Document {
  id: number;
  original_filename: string;
  file_size: number;
  file_type: string;
  mime_type: string;
  created_at: string;
}

export interface JobResult {
  title: string;
  category: string;
  summary: string;
  keywords: string[];
  metadata: {
    filename: string;
    file_type: string;
    mime_type: string;
    file_size_bytes: number;
    word_count: number;
    char_count: number;
  };
  status: string;
  confidence_score: number;
  processing_version: string;
}

export interface Job {
  id: number;
  status: JobStatus;
  progress: number;
  current_step: string;
  error_message: string | null;
  retry_count: number;
  result: JobResult | null;
  reviewed_result: JobResult | null;
  is_reviewed: boolean;
  is_finalized: boolean;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  celery_task_id: string;
}

export interface JobListItem {
  id: number;
  document_id: number;
  status: JobStatus;
  progress: number;
  current_step: string;
  is_finalized: boolean;
  retry_count: number;
  queued_at: string;
  completed_at: string | null;
  original_filename: string;
  file_size: number;
  file_type: string;
}

export interface JobListResponse {
  items: JobListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DocumentDetailResponse {
  document: Document;
  job: Job;
}

export interface UploadResponse {
  uploaded: number;
  jobs: Array<{
    document_id: number;
    job_id: number;
    filename: string;
    status: string;
    celery_task_id: string;
  }>;
}

export interface ProgressEvent {
  event: string;
  job_id: number;
  document_id: number;
  progress: number;
  message: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

export interface ExportData {
  job_id: number;
  document_id: number;
  status: string;
  is_finalized: boolean;
  result: JobResult | null;
  exported_at: string;
}
