import { apiClient } from '../api';
import type { ApiItem, ItemCreate, ItemUpdate } from '../types';

export class ItemsApi {
  private client = apiClient;

  async getItems(offset: number = 0, limit: number = 1000): Promise<ApiItem[]> {
    return this.client.request<ApiItem[]>(`/items/?offset=${offset}&limit=${limit}`);
  }

  async getItem(assetId: string): Promise<ApiItem> {
    return this.client.request<ApiItem>(`/items/${assetId}`);
  }

  async getItemsByUsername(steamUsername: string, offset: number = 0, limit: number = 1000): Promise<ApiItem[]> {
    return this.client.request<ApiItem[]>(`/items/by-username/${steamUsername}?offset=${offset}&limit=${limit}`);
  }

  async createItem(item: ItemCreate): Promise<ApiItem> {
    return this.client.request<ApiItem>('/items/', {
      method: 'POST',
      body: JSON.stringify(item),
    });
  }

  async updateItem(assetId: string, item: ItemUpdate): Promise<ApiItem> {
    return this.client.request<ApiItem>(`/items/${assetId}`, {
      method: 'PATCH',
      body: JSON.stringify(item),
    });
  }

  async deleteItem(assetId: string): Promise<{ ok: boolean }> {
    return this.client.request<{ ok: boolean }>(`/items/${assetId}`, {
      method: 'DELETE',
    });
  }

  async getItemsCount(): Promise<{ total_items: number }> {
    return this.client.request<{ total_items: number }>('/items/count');
  }
}

export const itemsApi = new ItemsApi();
