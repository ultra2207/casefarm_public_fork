import { apiClient } from '../api';
import type { ApiAccount, AccountCreate, AccountUpdate } from '../types';

export class AccountsApi {
  private client = apiClient;

  async getAccounts(offset: number = 0, limit: number = 1000): Promise<ApiAccount[]> {
    return this.client.request<ApiAccount[]>(`/accounts/?offset=${offset}&limit=${limit}`);
  }

  async getAccount(id: number): Promise<ApiAccount> {
    return this.client.request<ApiAccount>(`/accounts/${id}`);
  }

  async createAccount(account: AccountCreate): Promise<ApiAccount> {
    return this.client.request<ApiAccount>('/accounts/', {
      method: 'POST',
      body: JSON.stringify(account),
    });
  }

  async updateAccount(id: number, account: AccountUpdate): Promise<ApiAccount> {
    return this.client.request<ApiAccount>(`/accounts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(account),
    });
  }

  async deleteAccount(id: number): Promise<{ ok: boolean }> {
    return this.client.request<{ ok: boolean }>(`/accounts/${id}`, {
      method: 'DELETE',
    });
  }

  async getAccountsCount(): Promise<{ total_accounts: number }> {
    return this.client.request<{ total_accounts: number }>('/accounts/count');
  }

  async searchAccounts(params: {
    steam_username?: string;
    email_id?: string;
    status?: string;
    region?: string;
    offset?: number;
    limit?: number;
  }): Promise<ApiAccount[]> {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, String(value));
      }
    });
    
    return this.client.request<ApiAccount[]>(`/accounts/search?${queryParams.toString()}`);
  }

  async getAccountsByStatus(status: string, offset: number = 0, limit: number = 1000): Promise<ApiAccount[]> {
    return this.client.request<ApiAccount[]>(`/accounts/by-status/${status}?offset=${offset}&limit=${limit}`);
  }

  async getAccountsByRegion(region: string, offset: number = 0, limit: number = 1000): Promise<ApiAccount[]> {
    return this.client.request<ApiAccount[]>(`/accounts/by-region/${region}?offset=${offset}&limit=${limit}`);
  }
}

export const accountsApi = new AccountsApi();
