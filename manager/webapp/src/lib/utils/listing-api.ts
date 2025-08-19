import { useState, useCallback, useEffect, useRef } from 'react';
import { apiClient } from '../api';
import type { 
  StartListingRequest, 
  TaskResponse, 
  TaskData, 
  ProgressUpdate, 
  LogMessage,
  ErrorResponse,
  TaskDataResponse,
  DeleteResponse,
  StopListingResponse
} from '../types';

export class ListingApi {
  private apiClient: typeof apiClient;

  constructor(client: typeof apiClient) {
    this.apiClient = client;
  }

  // Start a new listing task
  async startListing(usernames: string[]): Promise<TaskResponse> {
    return this.apiClient.request<TaskResponse>('/start-listing', {
      method: 'POST',
      body: JSON.stringify({ usernames }),
    });
  }

  // Stop a running listing task
  async stopListing(taskId: string): Promise<StopListingResponse> {
    return this.apiClient.request<StopListingResponse>(`/tasks/${taskId}/stop`, {
      method: 'POST',
    });
  }

  // Get specific task status
  async getTaskStatus(taskId: string): Promise<TaskDataResponse> {
    return this.apiClient.request<TaskDataResponse>(`/tasks/${taskId}`);
  }

  // Get all tasks
  async getAllTasks(): Promise<Record<string, TaskData>> {
    return this.apiClient.request<Record<string, TaskData>>('/tasks');
  }

  // Delete a task
  async deleteTask(taskId: string): Promise<DeleteResponse> {
    return this.apiClient.request<DeleteResponse>(`/tasks/${taskId}`, {
      method: 'DELETE',
    });
  }

  // Utility method to check if response is an error
  isErrorResponse(response: any): response is ErrorResponse {
    return response && typeof response === 'object' && 'error' in response;
  }

  // Get WebSocket URL
  getWebSocketUrl(path: string): string {
    return this.apiClient.getWebSocketUrl(path);
  }
}

export const listingApi = new ListingApi(apiClient);

// Fixed WebSocket hook with proper cleanup and ref management
export const useListingWebSocket = (taskId: string | null) => {
  // Use refs for WebSocket connections to avoid re-creation
  const progressWsRef = useRef<WebSocket | null>(null);
  const logsWsRef = useRef<WebSocket | null>(null);
  const isConnectingRef = useRef(false);
  const isUnmountedRef = useRef(false);

  // State for UI
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Create progress WebSocket connection
  const createProgressConnection = useCallback((id: string) => {
    // Don't create if already connecting or if component is unmounted
    if (isConnectingRef.current || isUnmountedRef.current) {
      return;
    }

    // Close existing connection
    if (progressWsRef.current) {
      progressWsRef.current.close();
      progressWsRef.current = null;
    }

    try {
      isConnectingRef.current = true;
      setConnectionError(null);

      const ws = new WebSocket(listingApi.getWebSocketUrl(`/ws/progress/${id}`));
      progressWsRef.current = ws;

      ws.onopen = () => {
        if (!isUnmountedRef.current) {
          setIsConnected(true);
          setConnectionError(null);
          isConnectingRef.current = false;
        }
      };

      ws.onmessage = (event) => {
        if (!isUnmountedRef.current) {
          try {
            const data = JSON.parse(event.data);
            setProgress(data);
          } catch (error) {
            console.error('Failed to parse progress WebSocket message:', error);
          }
        }
      };

      ws.onerror = (error) => {
        if (!isUnmountedRef.current) {
          setIsConnected(false);
          setConnectionError('Progress WebSocket connection failed');
          isConnectingRef.current = false;
        }
        console.error('Progress WebSocket error:', error);
      };

      ws.onclose = (event) => {
        if (!isUnmountedRef.current) {
          setIsConnected(false);
          isConnectingRef.current = false;
          if (event.code !== 1000) {
            setConnectionError(`Progress WebSocket closed unexpectedly (${event.code})`);
          }
        }
        if (progressWsRef.current === ws) {
          progressWsRef.current = null;
        }
      };

    } catch (error) {
      isConnectingRef.current = false;
      if (!isUnmountedRef.current) {
        setConnectionError('Failed to create progress WebSocket connection');
      }
      console.error('Error creating progress WebSocket:', error);
    }
  }, []);

  // Create logs WebSocket connection
  const createLogsConnection = useCallback(() => {
    // Don't create if component is unmounted
    if (isUnmountedRef.current) {
      return;
    }

    // Close existing connection
    if (logsWsRef.current) {
      logsWsRef.current.close();
      logsWsRef.current = null;
    }

    try {
      const ws = new WebSocket(listingApi.getWebSocketUrl('/ws/logs'));
      logsWsRef.current = ws;

      ws.onopen = () => {
        console.log('Logs WebSocket connected');
      };

      ws.onmessage = (event) => {
        if (!isUnmountedRef.current) {
          try {
            const data = JSON.parse(event.data);
            setLogs(prev => [...prev, data]);
          } catch (error) {
            console.error('Failed to parse logs WebSocket message:', error);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('Logs WebSocket error:', error);
      };

      ws.onclose = (event) => {
        if (event.code !== 1000) {
          console.warn(`Logs WebSocket closed unexpectedly (${event.code})`);
        }
        if (logsWsRef.current === ws) {
          logsWsRef.current = null;
        }
      };

    } catch (error) {
      console.error('Error creating logs WebSocket:', error);
    }
  }, []);

  // Cleanup function
  const disconnect = useCallback(() => {
    if (progressWsRef.current) {
      progressWsRef.current.close();
      progressWsRef.current = null;
    }
    if (logsWsRef.current) {
      logsWsRef.current.close();
      logsWsRef.current = null;
    }
    setIsConnected(false);
    setConnectionError(null);
    isConnectingRef.current = false;
  }, []);

  // Clear logs function
  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Reconnect function
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(() => {
      if (!isUnmountedRef.current) {
        if (taskId) {
          createProgressConnection(taskId);
        }
        createLogsConnection();
      }
    }, 1000);
  }, [taskId, disconnect, createProgressConnection, createLogsConnection]);

  // Effect for taskId changes
  useEffect(() => {
    if (taskId && !isUnmountedRef.current) {
      createProgressConnection(taskId);
    }
  }, [taskId, createProgressConnection]);

  // Effect for logs connection - only connect once
  useEffect(() => {
    if (!isUnmountedRef.current) {
      createLogsConnection();
    }
  }, [createLogsConnection]);

  // Cleanup on unmount
  useEffect(() => {
    isUnmountedRef.current = false;
    
    return () => {
      isUnmountedRef.current = true;
      disconnect();
    };
  }, [disconnect]);

  return {
    progress,
    logs,
    isConnected,
    connectionError,
    disconnect,
    reconnect,
    clearLogs,
    // Computed values
    hasLogs: logs.length > 0,
    latestLog: logs[logs.length - 1] || null,
    isTaskCompleted: progress?.type === 'completed',
    isTaskErrored: progress?.type === 'error',
    isTaskStopped: progress?.type === 'stopped',
    isTaskRunning: progress?.type === 'progress'
  };
};

// Hook for managing multiple tasks
export const useListingTasks = () => {
  const [tasks, setTasks] = useState<Record<string, TaskData>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const allTasks = await listingApi.getAllTasks();
      setTasks(allTasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteTask = useCallback(async (taskId: string) => {
    try {
      const response = await listingApi.deleteTask(taskId);
      if (listingApi.isErrorResponse(response)) {
        throw new Error(response.error);
      }
      
      // Remove from local state
      setTasks(prev => {
        const newTasks = { ...prev };
        delete newTasks[taskId];
        return newTasks;
      });
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete task');
      return false;
    }
  }, []);

  const startListing = useCallback(async (usernames: string[]) => {
    setError(null);
    try {
      const response = await listingApi.startListing(usernames);
      await refreshTasks(); // Refresh to get the new task
      return response.task_id;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start listing');
      return null;
    }
  }, [refreshTasks]);

  const stopListing = useCallback(async (taskId: string) => {
    setError(null);
    try {
      const response = await listingApi.stopListing(taskId);
      if (listingApi.isErrorResponse(response)) {
        throw new Error(response.error);
      }
      await refreshTasks(); // Refresh to get updated task status
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop listing');
      return null;
    }
  }, [refreshTasks]);

  return {
    tasks,
    loading,
    error,
    refreshTasks,
    deleteTask,
    startListing,
    stopListing,
    // Computed values
    activeTasks: Object.values(tasks).filter(task => task.status === 'running'),
    completedTasks: Object.values(tasks).filter(task => task.status === 'completed'),
    erroredTasks: Object.values(tasks).filter(task => task.status === 'error'),
    stoppedTasks: Object.values(tasks).filter(task => task.status === 'stopped'),
    totalTasks: Object.keys(tasks).length
  };
};
