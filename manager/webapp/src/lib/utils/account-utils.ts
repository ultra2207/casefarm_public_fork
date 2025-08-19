// lib/utils/account-utils.ts
import { ApiAccount, ApiItem } from '@/lib/types';

export interface Account {
  id: string;
  steam_username: string;
  steam_password: string;
  email_id: string;
  email_password: string;
  prime: string;
  armoury: string;
  steamguard: string;
  steam_balance: string;
  steam_shared_secret: string;
  steam_identity_secret: string;
  access_token: string;
  refresh_token: string;
  steam_id: number;
  trade_token: string;
  trade_url: string;
  steam_avatar_path: string;
  steam_avatar_url: string;
  bot_id: string;
  num_armoury_stars: number;
  xp_level: number;
  service_medal: string;
  status: string;
  xp: number;
  region: string;
  currency: string;
  pass_value: number;
  pua: number;
  fua: number;
  vac_ban: number;
  items: AccountItem[];
}

export interface AccountItem {
  asset_id: string;
  market_hash_name: string;
  tradable_after_ist: string | null;
  tradable_after_unix: number | null;
  steam_username: string;
  marketable: boolean;
  tradable: boolean;
}

export function convertApiAccountToAccount(apiAccount: ApiAccount): Account {
  // Convert active_armoury_passes to the appropriate armoury display value
  const getArmouryValue = (activePasses: number | null, prime: number | null): string => {
    const activePassesNum = activePasses || 0;
    
    if (activePassesNum > 0) {
      return 'tick';  // Has active armoury passes
    } else if (prime && prime !== 0) {
      return 'prime'; // Prime only, no active passes
    } else {
      return 'none';  // No passes and no prime
    }
  };

  return {
    id: String(apiAccount.id),
    steam_username: apiAccount.steam_username || '',
    steam_password: apiAccount.steam_password || '',
    email_id: apiAccount.email_id || '',
    email_password: apiAccount.email_password || '',
    prime: String(apiAccount.prime || ''),
    armoury: getArmouryValue(apiAccount.active_armoury_passes, apiAccount.prime),
    steamguard: apiAccount.steamguard || '',
    steam_balance: String(apiAccount.steam_balance || ''),
    steam_shared_secret: apiAccount.steam_shared_secret || '',
    steam_identity_secret: apiAccount.steam_identity_secret || '',
    access_token: apiAccount.access_token || '',
    refresh_token: apiAccount.refresh_token || '',
    steam_id: apiAccount.steam_id || 0,
    trade_token: apiAccount.trade_token || '',
    trade_url: apiAccount.trade_url || '',
    steam_avatar_path: apiAccount.steam_avatar_path || '',
    steam_avatar_url: apiAccount.steam_avatar_url || '',
    bot_id: apiAccount.bot_id || '',
    num_armoury_stars: apiAccount.num_armoury_stars || 0,
    xp_level: apiAccount.xp_level || 0,
    service_medal: apiAccount.service_medal || '',
    status: apiAccount.status || 'offline',
    xp: apiAccount.xp || 0,
    region: apiAccount.region || '',
    currency: apiAccount.currency || '',
    pass_value: apiAccount.pass_value || 0,
    pua: apiAccount.pua || 0,
    fua: apiAccount.fua || 0,
    vac_ban: apiAccount.vac_ban || 0,
    items: []
  };
}

export function convertAccountToApiAccount(account: Partial<Account>): Partial<ApiAccount> {
  const result: Partial<ApiAccount> = {
    steam_username: account.steam_username,
    steam_password: account.steam_password,
    email_id: account.email_id,
    email_password: account.email_password,
    // Convert prime to number (no trim needed since it's already boolean/number)
    prime: account.prime !== undefined && account.prime !== null ? Number(account.prime) : undefined,
    // Convert armoury enum to numeric active_armoury_passes
    active_armoury_passes: account.armoury === 'tick' ? 1 : 
                          account.armoury === 'prime' ? 0 : 
                          account.armoury === 'none' ? 0 : undefined,
    steamguard: account.steamguard,
    // Convert steam_balance to number (no trim needed since it's already number)
    steam_balance: account.steam_balance !== undefined && account.steam_balance !== null ? 
                   Number(account.steam_balance) : undefined,
    steam_shared_secret: account.steam_shared_secret,
    steam_identity_secret: account.steam_identity_secret,
    access_token: account.access_token,
    refresh_token: account.refresh_token,
    trade_token: account.trade_token,
    trade_url: account.trade_url,
    steam_avatar_path: account.steam_avatar_path,
    bot_id: account.bot_id,
    num_armoury_stars: account.num_armoury_stars,
    xp_level: account.xp_level,
    service_medal: account.service_medal,
    status: account.status,
    xp: account.xp,
    region: account.region,
    currency: account.currency,
    pass_value: account.pass_value,
    pua: account.pua,
    fua: account.fua,
    vac_ban: account.vac_ban,
  };

  return result;
}


export function convertApiItemToAccountItem(apiItem: ApiItem): AccountItem {
  return {
    asset_id: apiItem.asset_id,
    market_hash_name: apiItem.market_hash_name,
    tradable_after_ist: apiItem.tradable_after_ist,
    tradable_after_unix: apiItem.tradable_after_unix,
    steam_username: apiItem.steam_username,
    marketable: Boolean(apiItem.marketable),
    tradable: Boolean(apiItem.tradable),
  };
}
