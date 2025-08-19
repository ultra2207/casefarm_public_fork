# CaseFarm API Client Documentation

This documentation covers how to use and extend the modular API client structure for your CaseFarm application.

## Architecture Overview

The API client is organized using a modular, domain-based structure that separates concerns and promotes maintainability:

```
lib/
├── api.ts              # Main API client with base functionality
├── types.ts            # Shared TypeScript interfaces
├── index.ts            # Main export file
└── utils/
    ├── accounts-api.ts     # Account-specific API calls
    ├── items-api.ts        # Item-specific API calls
    └── account-utils.ts    # Data transformation utilities
```

## Getting Started

### Basic Usage

Import the API clients in your components:

```typescript
// Import everything you need
import { accountsApi, itemsApi, convertApiAccountToAccount } from '@/lib';
import type { ApiAccount, Account } from '@/lib';

// Or import specific items
import { accountsApi } from '@/lib/utils/accounts-api';
import { convertApiAccountToAccount } from '@/lib/utils/account-utils';
```

### Example Component Usage

```typescript
import React, { useEffect, useState } from 'react';
import { accountsApi, convertApiAccountToAccount } from '@/lib';
import type { Account } from '@/lib';

export function AccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const apiAccounts = await accountsApi.getAccounts();
        const transformedAccounts = apiAccounts.map(convertApiAccountToAccount);
        setAccounts(transformedAccounts);
      } catch (error) {
        console.error('Failed to fetch accounts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAccounts();
  }, []);

  return (
    
      {loading ? (
        Loading accounts...
      ) : (
        
          {accounts.map(account => (
            {account.steam_username}
          ))}
        
      )}
    
  );
}
```

## API Methods Reference

### Accounts API

**Basic Operations:**
```typescript
// Get all accounts with pagination
const accounts = await accountsApi.getAccounts(0, 50);

// Get single account
const account = await accountsApi.getAccount(123);

// Create new account
const newAccount = await accountsApi.createAccount({
  steam_username: 'player123',
  email_id: 'player@example.com',
  prime: 1
});

// Update account
const updatedAccount = await accountsApi.updateAccount(123, {
  status: 'active',
  steam_balance: 25.50
});

// Delete account
await accountsApi.deleteAccount(123);
```

**Search and Filter Operations:**
```typescript
// Search accounts
const searchResults = await accountsApi.searchAccounts({
  steam_username: 'player',
  status: 'active',
  region: 'US',
  offset: 0,
  limit: 20
});

// Get accounts by status
const activeAccounts = await accountsApi.getAccountsByStatus('active');

// Get accounts by region
const usAccounts = await accountsApi.getAccountsByRegion('US');

// Get total count
const { total_accounts } = await accountsApi.getAccountsCount();
```

### Items API

```typescript
// Get all items
const items = await itemsApi.getItems();

// Get single item
const item = await itemsApi.getItem('asset_123');

// Get items by username
const playerItems = await itemsApi.getItemsByUsername('player123');

// Create new item
const newItem = await itemsApi.createItem({
  asset_id: 'asset_456',
  market_hash_name: 'AK-47 | Redline',
  steam_username: 'player123',
  marketable: 1,
  tradable: 1
});

// Update item
const updatedItem = await itemsApi.updateItem('asset_456', {
  tradable_after_unix: 1672531200
});

// Delete item
await itemsApi.deleteItem('asset_456');

// Get total count
const { total_items } = await itemsApi.getItemsCount();
```

## Data Transformation

The `account-utils.ts` provides conversion functions between API types and frontend types:

```typescript
// Convert API account to frontend account
const frontendAccount = convertApiAccountToAccount(apiAccount);

// Convert frontend account to API format for updates
const apiUpdateData = convertAccountToApiAccount(frontendAccount);

// Convert API item to frontend item
const frontendItem = convertApiItemToAccountItem(apiItem);
```

## Adding New Features

### Step 1: Add New API Endpoints

When your backend adds new endpoints, create a new API utility file:

**lib/utils/markets-api.ts:**
```typescript
import { apiClient } from '../api';
import type { ApiMarket, MarketCreate, MarketUpdate } from '../types';

export class MarketsApi {
  private client = apiClient;

  async getMarkets(offset: number = 0, limit: number = 100): Promise {
    return this.client.request(`/markets/?offset=${offset}&limit=${limit}`);
  }

  async getMarket(id: number): Promise {
    return this.client.request(`/markets/${id}`);
  }

  async createMarket(market: MarketCreate): Promise {
    return this.client.request('/markets/', {
      method: 'POST',
      body: JSON.stringify(market),
    });
  }

  async updateMarket(id: number, market: MarketUpdate): Promise {
    return this.client.request(`/markets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(market),
    });
  }

  async deleteMarket(id: number): Promise {
    return this.client.request(`/markets/${id}`, {
      method: 'DELETE',
    });
  }
}

export const marketsApi = new MarketsApi();
```

### Step 2: Add Types

Update **lib/types.ts:**
```typescript
export interface ApiMarket {
  id: number;
  name: string;
  description: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MarketCreate {
  name: string;
  description?: string;
  active?: boolean;
}

export interface MarketUpdate {
  name?: string;
  description?: string;
  active?: boolean;
}
```

### Step 3: Add Utilities (if needed)

Create **lib/utils/market-utils.ts** if you need data transformation:
```typescript
import type { ApiMarket } from '../types';

export interface Market {
  id: string;
  name: string;
  description: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export function convertApiMarketToMarket(apiMarket: ApiMarket): Market {
  return {
    id: String(apiMarket.id),
    name: apiMarket.name,
    description: apiMarket.description || '',
    isActive: apiMarket.active,
    createdAt: new Date(apiMarket.created_at),
    updatedAt: new Date(apiMarket.updated_at),
  };
}

export function convertMarketToApiMarket(market: Partial): Partial {
  return {
    name: market.name,
    description: market.description,
    active: market.isActive,
  };
}
```

### Step 4: Update Exports

Update **lib/index.ts:**
```typescript
export { apiClient } from './api';
export * from './types';
export { accountsApi } from './utils/accounts-api';
export { itemsApi } from './utils/items-api';
export { marketsApi } from './utils/markets-api'; // Add new export
export * from './utils/account-utils';
export * from './utils/market-utils'; // Add new utilities
```

## Error Handling

The base API client includes centralized error handling[4]. You can extend it for your specific needs:

```typescript
// In your components
try {
  const accounts = await accountsApi.getAccounts();
} catch (error) {
  if (error.message.includes('422')) {
    console.error('Validation error:', error);
    // Handle validation errors
  } else if (error.message.includes('401')) {
    console.error('Authentication error:', error);
    // Redirect to login
  } else {
    console.error('Unknown error:', error);
    // Show generic error message
  }
}
```

## Advanced Usage

### Custom Request Options

You can extend the base API client for custom headers or request options:

```typescript
// Custom API call with authentication
class AuthenticatedApi extends ApiClient {
  constructor(baseUrl: string, authToken: string) {
    super(baseUrl);
    this.authToken = authToken;
  }

  async authenticatedRequest(endpoint: string, options: RequestInit = {}): Promise {
    const authHeaders = {
      'Authorization': `Bearer ${this.authToken}`,
      ...options.headers,
    };

    return this.request(endpoint, {
      ...options,
      headers: authHeaders,
    });
  }
}
```

// Usage
const allAccounts = await fetchAllPages(
  (offset, limit) => accountsApi.getAccounts(offset, limit),
  50
);
```

## Best Practices

1. **Type Safety**: Always use TypeScript interfaces for API responses and requests[2]
2. **Error Handling**: Implement comprehensive error handling at the API client level[4]
3. **Separation of Concerns**: Keep API calls, data transformation, and UI logic separate
4. **Consistent Naming**: Use consistent naming conventions across your API methods

## Backend Integration

When adding new backend endpoints, follow this pattern in your FastAPI application:

```python
# routes/markets.py
from fastapi import APIRouter

router = APIRouter()

# server.py
from routes.markets import router as markets_router
app.include_router(markets_router, prefix="/markets", tags=["markets"])
```

This modular approach ensures your frontend and backend scale together while maintaining clean, maintainable code.