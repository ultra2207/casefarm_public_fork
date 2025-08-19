const API_BASE_URL = 'http://127.0.0.1:8000';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        if (response.status === 422) {
          const errorBody = await response.text();
          console.error('422 Validation Error:', errorBody);
          console.error('Request payload:', options.body);
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Health check
  async healthCheck(): Promise<{ 
    status: string; 
    message: string; 
    log_file_exists: boolean;
    active_tasks: number;
    total_tasks: number;
    log_connections: number;
    progress_connections: number;
  }> {
    return this.request('/health');
  }

  // Root endpoint
  async getRoot(): Promise<{ message: string; version: string; docs: string; redoc: string }> {
    return this.request('/');
  }

  // Get WebSocket URL
  getWebSocketUrl(path: string): string {
    return `${this.baseUrl.replace('http', 'ws')}${path}`;
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
