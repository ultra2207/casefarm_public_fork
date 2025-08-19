// Account and Item Types (User Provided)
export interface ApiAccount {
  id: number;
  steam_username: string | null;
  steam_password: string | null;
  email_id: string | null;
  email_password: string | null;
  prime: number | null;
  active_armoury_passes: number | null;
  steamguard: string | null;
  steam_balance: number | null;
  steam_shared_secret: string | null;
  steam_identity_secret: string | null;
  access_token: string | null;
  refresh_token: string | null;
  steam_id: number | null;
  trade_token: string | null;
  trade_url: string | null;
  steam_avatar_path: string | null;
  steam_avatar_url: string | null;
  bot_id: string | null;
  num_armoury_stars: number | null;
  xp_level: number;
  service_medal: string | null;
  status: string | null;
  xp: number;
  region: string | null;
  currency: string | null;
  pass_value: number;
  pua: number;
  fua: number;
  vac_ban: number;
}

export interface ApiItem {
  asset_id: string;
  market_hash_name: string;
  tradable_after_ist: string | null;
  tradable_after_unix: number | null;
  steam_username: string;
  marketable: number;
  tradable: number;
}

export interface AccountCreate {
  steam_username?: string;
  steam_password?: string;
  email_id?: string;
  email_password?: string;
  prime?: number;
  active_armoury_passes?: number;
  steamguard?: string;
  steam_balance?: number;
  steam_shared_secret?: string;
  steam_identity_secret?: string;
  access_token?: string;
  refresh_token?: string;
  steam_id?: number;
  trade_token?: string;
  trade_url?: string;
  steam_avatar_path?: string;
  bot_id?: string;
  num_armoury_stars?: number;
  xp_level?: number;
  service_medal?: string;
  status?: string;
  xp?: number;
  region?: string;
  currency?: string;
  pass_value?: number;
  pua?: number;
  fua?: number;
  vac_ban?: number;
}

export interface AccountUpdate {
  steam_username?: string;
  steam_password?: string;
  email_id?: string;
  email_password?: string;
  prime?: number;
  active_armoury_passes?: number;
  steamguard?: string;
  steam_balance?: number;
  steam_shared_secret?: string;
  steam_identity_secret?: string;
  access_token?: string;
  refresh_token?: string;
  steam_id?: number;
  trade_token?: string;
  trade_url?: string;
  steam_avatar_path?: string;
  bot_id?: string;
  num_armoury_stars?: number;
  xp_level?: number;
  service_medal?: string;
  status?: string;
  xp?: number;
  region?: string;
  currency?: string;
  pass_value?: number;
  pua?: number;
  fua?: number;
  vac_ban?: number;
}

export interface ItemCreate {
  asset_id: string;
  market_hash_name: string;
  tradable_after_ist?: string;
  tradable_after_unix?: number;
  steam_username: string;
  marketable?: number;
  tradable?: number;
}

export interface ItemUpdate {
  market_hash_name?: string;
  tradable_after_ist?: string;
  tradable_after_unix?: number;
  steam_username?: string;
  marketable?: number;
  tradable?: number;
}

// Legacy type aliases for backward compatibility
export type Account = ApiAccount;
export type Item = ApiItem;

// Listing API Types
export interface StartListingRequest {
  usernames: string[];
}

export interface TaskResponse {
  task_id: string;
  status: string;
}

export interface StopListingResponse {
  success: boolean;
  message: string;
  task_id?: string;
}

export interface TaskData {
  status: 'starting' | 'running' | 'completed' | 'error' | 'stopped';
  current: number;
  total: number;
  message: string;
  result?: boolean;
  error?: string;
  started_at: number;
  completed_at?: number;
  stopped_at?: number;
  percentage: number;
}

export interface ProgressUpdate {
  type: 'progress' | 'completed' | 'error' | 'stopped';
  task_id: string;
  current: number;
  total: number;
  message: string;
  percentage: number;
  result?: boolean;
  error?: string;
  stopped_reason?: string;
}

export interface LogMessage {
  type: 'log';
  message: string;
  timestamp: number;
  historical?: boolean;
  separator?: boolean;
  error?: boolean;
  info?: boolean;
}

export interface ErrorResponse {
  error: string;
  message?: string;
}

// WebSocket connection states
export type WebSocketState = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface ListingProgress {
  taskId: string;
  status: TaskData['status'];
  current: number;
  total: number;
  message: string;
  percentage: number;
  startedAt: number;
  completedAt?: number;
  stoppedAt?: number;
  error?: string;
  result?: boolean;
}

export interface ListingStats {
  activeTasks: number;
  totalTasks: number;
  logConnections: number;
  progressConnections: number;
  logFileExists: boolean;
}

// Health check response type
export interface HealthCheckResponse {
  status: string;
  message: string;
  log_file_exists: boolean;
  active_tasks: number;
  total_tasks: number;
  log_connections: number;
  progress_connections: number;
}

// API Response types for common patterns
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface SearchFilters {
  steam_username?: string;
  email_id?: string;
  status?: string;
  region?: string;
  offset?: number;
  limit?: number;
}

// Utility types
export type TaskId = string;
export type Username = string;
export type ProgressCallback = (current: number, total: number, message: string) => void;

// Response wrapper types
export type ApiResponse<T> = T | ErrorResponse;
export type TaskDataResponse = ApiResponse<TaskData>;
export type DeleteResponse = ApiResponse<{ message: string }>;
