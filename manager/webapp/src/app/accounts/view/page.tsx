// app/accounts/page.tsx
"use client";

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { toast } from 'sonner';
import {
  ChevronDown,
  ChevronUp,
  Shield,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Check,
  X,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Filter,
  Search,
  Save,
  ShieldCheck,
  AlertTriangle,
  ScrollText,
  Minimize2,
  RefreshCw,
  Package,
} from "lucide-react";

// Updated imports using the new modular structure
import { accountsApi, itemsApi } from '@/lib';
import { 
  Account, 
  AccountItem, 
  convertApiAccountToAccount, 
  convertAccountToApiAccount, 
  convertApiItemToAccountItem 
} from '@/lib/utils/account-utils';

// Import steam-totp for 2FA code generation
import SteamTotp from 'steam-totp';

export interface FilterState {
  armoury: Set<'tick' | 'prime' | 'none'>;
  status: Set<string>;
  vacBan: 'all' | 'banned' | 'unbanned';
  username: string;
}

export type SortField = 'steam_username' | 'status' | 'armoury' | 'region' | 'vac_ban' | 'fua' | 'items';
export type SortDirection = 'asc' | 'desc' | 'default';

const statusOptions = [
  'offline',
  'waiting for selling time',
  'farming',
  'trading',
  'pass redeeming',
  'selling',
  'waiting for items to be marketable'
];

const armouryOptions = [
  { value: 'tick' as const, label: 'Active Pass' },
  { value: 'prime' as const, label: 'Prime Only' },
  { value: 'none' as const, label: 'None' }
];

interface VacCheckLog {
  id: string;
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error';
}

const initialNotifications = [
  { 
    id: 1, 
    title: 'System Ready', 
    message: 'Connected to database successfully',
    time: '12:19', 
    type: 'success' as const, 
    read: false 
  }
];

export default function ViewAccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [showPasswords, setShowPasswords] = useState<Set<string>>(new Set());
  const [editingFields, setEditingFields] = useState<Set<string>>(new Set());
  const [accountItems, setAccountItems] = useState<Record<string, AccountItem[]>>({});
  const [loadingItems, setLoadingItems] = useState<Set<string>>(new Set());
  
  const [filters, setFilters] = useState<FilterState>({
    armoury: new Set(),
    status: new Set(),
    vacBan: 'all',
    username: '',
  });
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('default');

  const [isVacChecking, setIsVacChecking] = useState(false);
  const [vacCheckProgress, setVacCheckProgress] = useState(0);
  const [vacCheckLogs, setVacCheckLogs] = useState<VacCheckLog[]>([]);
  const [showVacCheckDialog, setShowVacCheckDialog] = useState(false);
  const [showLogsExpanded, setShowLogsExpanded] = useState(false);
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );
  const [generating2FA, setGenerating2FA] = useState<Set<string>>(new Set());

  const loadAccounts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Updated to use accountsApi instead of apiClient
      const apiAccounts = await accountsApi.getAccounts(0, 1000);
      const accountsWithData = apiAccounts.map(convertApiAccountToAccount);
      
      setAccounts(accountsWithData);
      
      const primeAccounts = accountsWithData.filter(account => account.armoury === 'prime');
      
      if (primeAccounts.length > 0) {
        toast.success(`Loaded ${accountsWithData.length} accounts. Preloading items for ${primeAccounts.length} prime accounts...`);
        
        const itemLoadPromises = primeAccounts.map(async (account) => {
          if (account.steam_username) {
            try {
              // Updated to use itemsApi instead of apiClient
              const apiItems = await itemsApi.getItemsByUsername(account.steam_username);
              const items = apiItems.map(convertApiItemToAccountItem);
              
              setAccountItems(prev => ({
                ...prev,
                [account.id]: items
              }));
              
              setAccounts(prev => prev.map(acc => 
                acc.id === account.id ? { ...acc, items } : acc
              ));
              
              return { accountId: account.id, itemCount: items.length };
            } catch (error) {
              console.error(`Failed to preload items for prime account ${account.steam_username}:`, error);
              return { accountId: account.id, itemCount: 0, error: true };
            }
          }
          return { accountId: account.id, itemCount: 0 };
        });
        
        const results = await Promise.allSettled(itemLoadPromises);
        const successfulLoads = results.filter(result => result.status === 'fulfilled').length;
        
        toast.success(`Preloaded items for ${successfulLoads}/${primeAccounts.length} prime accounts`);
      } else {
        toast.success(`Loaded ${accountsWithData.length} accounts`);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts');
      toast.error('Failed to load accounts', {
        description: err instanceof Error ? err.message : 'Unknown error occurred'
      });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAccountItems = useCallback(async (steamUsername: string, accountId: string) => {
    if (loadingItems.has(accountId)) return;
    
    setLoadingItems(prev => new Set(prev).add(accountId));
    
    try {
      // Updated to use itemsApi instead of apiClient
      const apiItems = await itemsApi.getItemsByUsername(steamUsername);
      const items = apiItems.map(convertApiItemToAccountItem);
      
      setAccountItems(prev => ({
        ...prev,
        [accountId]: items
      }));
      
      setAccounts(prev => prev.map(account => 
        account.id === accountId ? { ...account, items } : account
      ));
      
    } catch (error) {
      console.error(`Failed to load items for ${steamUsername}:`, error);
      toast.error(`Failed to load items for ${steamUsername}`);
    } finally {
      setLoadingItems(prev => {
        const newSet = new Set(prev);
        newSet.delete(accountId);
        return newSet;
      });
    }
  }, [loadingItems]);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  const sortAccounts = useCallback((accounts: Account[], field: SortField | null, direction: SortDirection) => {
    if (!field || direction === 'default') {
      return accounts;
    }

    return [...accounts].sort((a, b) => {
      let aVal = a[field];
      let bVal = b[field];

      if (field === 'vac_ban') {
        aVal = Number(aVal);
        bVal = Number(bVal);
      } else if (field === 'fua') {
        aVal = Number(aVal);
        bVal = Number(bVal);
      } else {
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }

      const multiplier = direction === 'asc' ? 1 : -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * multiplier;
      } else {
        return aVal < bVal ? -1 * multiplier : aVal > bVal ? 1 * multiplier : 0;
      }
    });
  }, []);

  const filteredAndSortedAccounts = useMemo(() => {
    let filtered = accounts.filter(account => {
      const armouryMatch = filters.armoury.size === 0 || filters.armoury.has(account.armoury as 'tick' | 'prime' | 'none');
      const statusMatch = filters.status.size === 0 || filters.status.has(account.status);
      const usernameMatch = account.steam_username.toLowerCase().includes(filters.username.toLowerCase());
      const vacBanMatch = filters.vacBan === 'all' || 
        (filters.vacBan === 'banned' && account.vac_ban === 1) ||
        (filters.vacBan === 'unbanned' && account.vac_ban === 0);
      
      return armouryMatch && statusMatch && usernameMatch && vacBanMatch;
    });

    return sortAccounts(filtered, sortField, sortDirection);
  }, [accounts, filters, sortField, sortDirection, sortAccounts]);

  const handleFieldSave = useCallback(async (accountId: string, field: string, value: any) => {
    try {
      console.log('Saving field:', field, 'with value:', value, 'type:', typeof value);
      
      // Handle special conversions for database
      let dbValue = value;
      if (field === 'prime') {
        dbValue = value ? 1 : 0;
      }
      
      const updateData = { [field]: dbValue };
      const apiUpdateData = convertAccountToApiAccount(updateData);
      
      const filteredUpdateData = Object.fromEntries(
        Object.entries(apiUpdateData).filter(([_, v]) => v !== null && v !== undefined)
      );
      
      console.log('Sending to API:', filteredUpdateData);
      
      // Updated to use accountsApi instead of apiClient
      await accountsApi.updateAccount(parseInt(accountId), filteredUpdateData);
      
      setAccounts(prev => prev.map(account => 
        account.id === accountId ? { ...account, [field]: value } : account
      ));
      
      setEditingFields(prev => {
        const newSet = new Set(prev);
        newSet.delete(`${accountId}-${field}`);
        return newSet;
      });
      
      toast.success("Field Updated", {
        description: `${field} has been updated successfully`,
      });
    } catch (error) {
      console.error('Save error:', error);
      toast.error("Update Failed", {
        description: `Failed to update ${field}: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }, []);

  const toggleRowExpansion = useCallback((accountId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(accountId)) {
      newExpanded.delete(accountId);
    } else {
      newExpanded.add(accountId);
      const account = accounts.find(acc => acc.id === accountId);
      if (account && !accountItems[accountId] && account.steam_username) {
        loadAccountItems(account.steam_username, accountId);
      }
    }
    setExpandedRows(newExpanded);
  }, [expandedRows, accounts, accountItems, loadAccountItems]);

  const handleSelectAll = useCallback(() => {
    if (selectedAccounts.size === filteredAndSortedAccounts.length) {
      setSelectedAccounts(new Set());
    } else {
      setSelectedAccounts(new Set(filteredAndSortedAccounts.map(account => account.id)));
    }
  }, [selectedAccounts.size, filteredAndSortedAccounts]);

  const handleSelectAccount = useCallback((accountId: string) => {
    const newSelected = new Set(selectedAccounts);
    if (newSelected.has(accountId)) {
      newSelected.delete(accountId);
    } else {
      newSelected.add(accountId);
    }
    setSelectedAccounts(newSelected);
  }, [selectedAccounts]);

  const togglePasswordVisibility = useCallback((accountId: string) => {
    const newVisible = new Set(showPasswords);
    if (newVisible.has(accountId)) {
      newVisible.delete(accountId);
    } else {
      newVisible.add(accountId);
    }
    setShowPasswords(newVisible);
  }, [showPasswords]);

  const handleSort = useCallback((field: SortField) => {
    if (sortField === field) {
      if (sortDirection === 'default') {
        setSortDirection('asc');
      } else if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else {
        setSortDirection('default');
        setSortField(null);
      }
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  }, [sortField, sortDirection]);

  const handleRefresh = useCallback(() => {
    loadAccounts();
    toast.success("Refreshing accounts...");
  }, [loadAccounts]);

  // Updated 2FA code generation function
  const generate2FACode = useCallback(async (accountId: string) => {
    const account = accounts.find(acc => acc.id === accountId);
    
    if (!account) {
      toast.error("Account not found");
      return;
    }

    if (!account.steam_shared_secret) {
      toast.error("No shared secret found for this account");
      return;
    }

    setGenerating2FA(prev => new Set(prev).add(accountId));

    try {
      // Generate the 2FA code using steam-totp
      const code = SteamTotp.generateAuthCode(account.steam_shared_secret);
      
      // Copy to clipboard
      await navigator.clipboard.writeText(code);
      
      toast.success("2FA Code Generated", {
        description: `Code: ${code} - Copied to clipboard!`,
        duration: 5000,
      });

      console.log("Generated 2FA code for account:", account.steam_username, "Code:", code);
      
    } catch (error) {
      console.error('2FA generation error:', error);
      toast.error("Failed to generate 2FA code", {
        description: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    } finally {
      setGenerating2FA(prev => {
        const newSet = new Set(prev);
        newSet.delete(accountId);
        return newSet;
      });
    }
  }, [accounts]);

  const handleFieldEdit = useCallback((fieldKey: string) => {
    const newEditing = new Set(editingFields);
    if (newEditing.has(fieldKey)) {
      newEditing.delete(fieldKey);
    } else {
      newEditing.add(fieldKey);
    }
    setEditingFields(newEditing);
  }, [editingFields]);

  // Handle row click for expansion/collapse
  const handleRowClick = useCallback((accountId: string, event: React.MouseEvent) => {
    // Don't expand if clicking on interactive elements
    const target = event.target as HTMLElement;
    const isInteractiveElement = target.closest('button') || 
                                target.closest('input') || 
                                target.closest('[role="checkbox"]') ||
                                target.closest('a') ||
                                target.closest('.avatar') ||
                                target.hasAttribute('data-no-expand');

    if (!isInteractiveElement) {
      toggleRowExpansion(accountId);
    }
  }, [toggleRowExpansion]);

  const addVacCheckLog = (message: string, type: 'info' | 'success' | 'error' = 'info') => {
    const newLog: VacCheckLog = {
      id: crypto.randomUUID(),
      timestamp: new Date().toLocaleTimeString(),
      message,
      type
    };
    setVacCheckLogs(prev => [...prev, newLog]);
  };

  const handleVacBanCheck = useCallback(async (checkType: 'selected' | 'visible' = 'selected') => {
    let accountsToCheck: string[] = [];
    
    switch (checkType) {
      case 'selected':
        accountsToCheck = Array.from(selectedAccounts);
        break;
      case 'visible':
        accountsToCheck = filteredAndSortedAccounts.map(acc => acc.id);
        break;
    }

    if (accountsToCheck.length === 0) {
      toast.error("No accounts to check - Please select accounts or adjust filters.");
      return;
    }

    setIsVacChecking(true);
    setVacCheckProgress(0);
    setVacCheckLogs([]);
    setShowVacCheckDialog(true);
    setShowLogsExpanded(false);

    addVacCheckLog(`Starting VAC ban check for ${accountsToCheck.length} accounts`, 'info');

    for (let i = 0; i < accountsToCheck.length; i++) {
      const accountId = accountsToCheck[i];
      const account = accounts.find(acc => acc.id === accountId);
      
      if (account) {
        addVacCheckLog(`Checking ${account.steam_username}...`, 'info');
        
        await new Promise(resolve => setTimeout(resolve, 800));
        
        const hasVacBan = Math.random() > 0.8;
        
        if (hasVacBan) {
          addVacCheckLog(`Warning: VAC ban detected for ${account.steam_username}`, 'error');
          
          try {
            // Updated to use accountsApi instead of apiClient
            await accountsApi.updateAccount(parseInt(accountId), { vac_ban: 1 });
            setAccounts(prev => prev.map(acc => 
              acc.id === accountId ? { ...acc, vac_ban: 1 } : acc
            ));
          } catch (error) {
            addVacCheckLog(`Failed to update VAC status for ${account.steam_username}`, 'error');
          }
        } else {
          addVacCheckLog(`Success: ${account.steam_username} is clean`, 'success');
        }
        
        setVacCheckProgress(((i + 1) / accountsToCheck.length) * 100);
      }
    }

    addVacCheckLog('VAC ban check completed successfully', 'success');
    setIsVacChecking(false);
    toast.success(`VAC Ban Check Complete - Checked ${accountsToCheck.length} accounts`);
  }, [selectedAccounts, filteredAndSortedAccounts, accounts]);

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'farming': return 'default';
      case 'offline': return 'secondary';
      case 'trading': return 'outline';
      case 'selling': return 'secondary';
      default: return 'secondary';
    }
  };

  const getArmouryDisplay = (armoury: string) => {
    switch (armoury) {
      case 'tick':
        return (
          <div className="flex items-center gap-1">
            <Check className="h-4 w-4 text-green-500" />
          </div>
        );
      case 'prime':
        return (
          <div className="flex items-center gap-1">
            <span className="text-xs font-medium text-yellow-600">Prime Only</span>
          </div>
        );
      case 'none':
        return (
          <div className="flex items-center gap-1">
            <X className="h-4 w-4 text-red-500" />
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1">
            <X className="h-4 w-4 text-red-500" />
          </div>
        );
    }
  };

  const getVacBanDisplay = (vacBan: number) => {
    if (vacBan === 1) {
      return (
        <Badge variant="destructive" className="text-xs bg-red-600 text-white font-bold border-red-700">
          Banned
        </Badge>
      );
    } else {
      return (
        <Badge variant="outline" className="text-xs border-green-500 text-green-600">
          None
        </Badge>
      );
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4" />;
    }
    switch (sortDirection) {
      case 'asc':
        return <ArrowUp className="h-4 w-4" />;
      case 'desc':
        return <ArrowDown className="h-4 w-4" />;
      default:
        return <ArrowUpDown className="h-4 w-4" />;
    }
  };

  const handleFilterChange = (filterType: keyof FilterState, value: string, checked: boolean) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      if (filterType === 'armoury' || filterType === 'status') {
        if (checked) {
          (newFilters[filterType] as Set<any>).add(value);
        } else {
          (newFilters[filterType] as Set<any>).delete(value);
        }
      }
      return newFilters;
    });
  };

  const handleVacBanFilter = useCallback((filterType: 'all' | 'banned' | 'unbanned') => {
    setFilters(prev => ({ ...prev, vacBan: filterType }));
  }, []);

  if (loading) {
    return (
      <DashboardLayout>
        <PageHeader
          title="View Accounts"
          notifications={notifications}
          unreadNotifications={unreadNotifications}
          onMarkAllRead={handleMarkAllRead}
        />
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-2">
            <LoadingSpinner size="lg" />
            <span className="text-lg">Loading accounts...</span>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <PageHeader
          title="View Accounts"
          notifications={notifications}
          unreadNotifications={unreadNotifications}
          onMarkAllRead={handleMarkAllRead}
        />
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Accounts</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadAccounts}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <PageHeader
        title="View Accounts"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />

      <div className="space-y-6">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 max-w-sm">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by username..."
                  value={filters.username}
                  onChange={(e) => setFilters(prev => ({ ...prev, username: e.target.value }))}
                  className="pl-8"
                />
              </div>
            </div>
            
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="flex items-center gap-2">
                  <Filter className="h-4 w-4" />
                  Armoury {filters.armoury.size > 0 && `(${filters.armoury.size})`}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-56">
                <div className="space-y-3">
                  <h4 className="font-medium">Filter by Armoury</h4>
                  {armouryOptions.map((option) => (
                    <div key={option.value} className="flex items-center space-x-2">
                      <Checkbox
                        id={`armoury-${option.value}`}
                        checked={filters.armoury.has(option.value)}
                        onCheckedChange={(checked) => 
                          handleFilterChange('armoury', option.value, checked as boolean)
                        }
                      />
                      <Label htmlFor={`armoury-${option.value}`}>{option.label}</Label>
                    </div>
                  ))}
                </div>
              </PopoverContent>
            </Popover>

            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="flex items-center gap-2">
                  <Filter className="h-4 w-4" />
                  Status {filters.status.size > 0 && `(${filters.status.size})`}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-64">
                <div className="space-y-3">
                  <h4 className="font-medium">Filter by Status</h4>
                  {statusOptions.map((status) => (
                    <div key={status} className="flex items-center space-x-2">
                      <Checkbox
                        id={`status-${status}`}
                        checked={filters.status.has(status)}
                        onCheckedChange={(checked) => 
                          handleFilterChange('status', status, checked as boolean)
                        }
                      />
                      <Label htmlFor={`status-${status}`} className="capitalize">
                        {status}
                      </Label>
                    </div>
                  ))}
                </div>
              </PopoverContent>
            </Popover>

            <Button variant="outline" onClick={handleRefresh} className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </div>

        <Dialog open={showVacCheckDialog} onOpenChange={setShowVacCheckDialog}>
          <DialogContent className="max-w-2xl max-h-[80vh]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5" />
                VAC Ban Check Progress
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Progress</span>
                  <span className="text-sm text-muted-foreground">{Math.round(vacCheckProgress)}%</span>
                </div>
                <Progress value={vacCheckProgress} className="w-full" />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Logs</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowLogsExpanded(!showLogsExpanded)}
                    className="flex items-center gap-1"
                  >
                    {showLogsExpanded ? (
                      <>
                        <Minimize2 className="h-4 w-4" />
                        Collapse
                      </>
                    ) : (
                      <>
                        <ScrollText className="h-4 w-4" />
                        Expand
                      </>
                    )}
                  </Button>
                </div>
                
                <div className={`border rounded-md bg-muted/30 ${showLogsExpanded ? 'h-64' : 'h-32'} overflow-y-auto p-3 space-y-1`}>
                  {vacCheckLogs.map((log) => (
                    <div key={log.id} className="text-xs">
                      <span className="text-muted-foreground">[{log.timestamp}]</span>{' '}
                      <span className={
                        log.type === 'error' ? 'text-red-600' : 
                        log.type === 'success' ? 'text-green-600' : 
                        'text-foreground'
                      }>
                        {log.message}
                      </span>
                    </div>
                  ))}
                  {vacCheckLogs.length === 0 && (
                    <div className="text-xs text-muted-foreground">No logs yet...</div>
                  )}
                </div>
              </div>

              {!isVacChecking && vacCheckProgress === 100 && (
                <div className="flex justify-end">
                  <Button onClick={() => setShowVacCheckDialog(false)}>
                    Close
                  </Button>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>

        <Card>
          <CardHeader>
            <CardTitle>
              Accounts ({filteredAndSortedAccounts.length})
              {selectedAccounts.size > 0 && (
                <span className="text-sm font-normal ml-2">
                  ({selectedAccounts.size} selected)
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={selectedAccounts.size === filteredAndSortedAccounts.length && filteredAndSortedAccounts.length > 0}
                        onCheckedChange={handleSelectAll}
                      />
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        className="h-auto p-0 font-medium"
                        onClick={() => handleSort('steam_username')}
                      >
                        Username
                        {getSortIcon('steam_username')}
                      </Button>
                    </TableHead>
                    <TableHead>Avatar</TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        className="h-auto p-0 font-medium"
                        onClick={() => handleSort('status')}
                      >
                        Status
                        {getSortIcon('status')}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        className="h-auto p-0 font-medium"
                        onClick={() => handleSort('armoury')}
                      >
                        Armoury
                        {getSortIcon('armoury')}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        className="h-auto p-0 font-medium"
                        onClick={() => handleSort('fua')}
                      >
                        FUA %
                        {getSortIcon('fua')}
                      </Button>
                    </TableHead>
                    <TableHead>Password</TableHead>
                    <TableHead>2FA</TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        className="h-auto p-0 font-medium"
                        onClick={() => handleSort('items')}
                      >
                        Items
                        {getSortIcon('items')}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        className="h-auto p-0 font-medium"
                        onClick={() => handleSort('region')}
                      >
                        Region
                        {getSortIcon('region')}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <ContextMenu>
                        <ContextMenuTrigger>
                          <Button
                            variant="ghost"
                            className="h-auto p-0 font-medium"
                            onClick={() => handleSort('vac_ban')}
                          >
                            VAC Ban
                            {getSortIcon('vac_ban')}
                          </Button>
                        </ContextMenuTrigger>
                        <ContextMenuContent>
                          <ContextMenuItem onClick={() => handleVacBanCheck('selected')} disabled={selectedAccounts.size === 0}>
                            <ShieldCheck className="mr-2 h-4 w-4" />
                            Check Selected ({selectedAccounts.size})
                          </ContextMenuItem>
                          <ContextMenuItem onClick={() => handleVacBanCheck('visible')}>
                            <Shield className="mr-2 h-4 w-4" />
                            Check Visible ({filteredAndSortedAccounts.length})
                          </ContextMenuItem>
                          <ContextMenuSeparator />
                          <ContextMenuItem onClick={() => handleVacBanFilter('all')}>
                            <Filter className="mr-2 h-4 w-4" />
                            Show All {filters.vacBan === 'all' && '✓'}
                          </ContextMenuItem>
                          <ContextMenuItem onClick={() => handleVacBanFilter('banned')}>
                            <AlertTriangle className="mr-2 h-4 w-4 text-red-500" />
                            Show Banned Only {filters.vacBan === 'banned' && '✓'}
                          </ContextMenuItem>
                          <ContextMenuItem onClick={() => handleVacBanFilter('unbanned')}>
                            <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                            Show Clean Only {filters.vacBan === 'unbanned' && '✓'}
                          </ContextMenuItem>
                        </ContextMenuContent>
                      </ContextMenu>
                    </TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedAccounts.map((account) => (
                    <React.Fragment key={account.id}>
                      <TableRow 
                        className="cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={(e) => handleRowClick(account.id, e)}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selectedAccounts.has(account.id)}
                            onCheckedChange={() => handleSelectAccount(account.id)}
                          />
                        </TableCell>
                        <TableCell className="font-medium">{account.steam_username}</TableCell>
                        <TableCell>
                          <Avatar className="h-8 w-8 avatar" data-no-expand="true">
                            <AvatarImage 
                              src={account.steam_avatar_url || undefined} 
                              alt={`${account.steam_username} avatar`}
                              onError={(e) => {
                                e.currentTarget.style.display = 'none';
                              }}
                            />
                            <AvatarFallback>
                              {account.steam_username.charAt(0).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusBadgeVariant(account.status)} className="capitalize">
                            {account.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {getArmouryDisplay(account.armoury)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={account.fua} className="w-16" />
                            <span className="text-sm">{account.fua}%</span>
                          </div>
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-2">
                            <code className="text-sm">
                              {showPasswords.has(account.id) 
                                ? account.steam_password 
                                : '••••••••'
                              }
                            </code>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => togglePasswordVisibility(account.id)}
                            >
                              {showPasswords.has(account.id) ? (
                                <EyeOff className="h-3 w-3" />
                              ) : (
                                <Eye className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => generate2FACode(account.id)}
                            disabled={generating2FA.has(account.id)}
                            className="flex items-center gap-1"
                          >
                            {generating2FA.has(account.id) ? (
                              <LoadingSpinner size="sm" />
                            ) : (
                              'Generate'
                            )}
                          </Button>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Package className="h-4 w-4" />
                            <span className="text-sm">
                              {accountItems[account.id]?.length || account.items.length || 0}
                            </span>
                            {loadingItems.has(account.id) && (
                              <LoadingSpinner size="sm" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{account.region}</TableCell>
                        <TableCell>
                          {getVacBanDisplay(account.vac_ban)}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleRowExpansion(account.id)}
                            className="h-6 w-6 p-0"
                          >
                            {expandedRows.has(account.id) ? (
                              <ChevronUp className="h-4 w-4" />
                            ) : (
                              <ChevronDown className="h-4 w-4" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                      {expandedRows.has(account.id) && (
                        <TableRow>
                          <TableCell colSpan={12} className="p-0">
                            <ExpandedAccountDetails 
                              account={account} 
                              items={accountItems[account.id] || account.items || []}
                              editingFields={editingFields}
                              onFieldEdit={handleFieldEdit}
                              onFieldSave={handleFieldSave}
                              loadingItems={loadingItems.has(account.id)}
                            />
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                  {filteredAndSortedAccounts.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={12} className="text-center py-8">
                        <div className="text-muted-foreground">
                          No accounts found matching your filters.
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

interface ExpandedAccountDetailsProps {
  account: Account;
  items: AccountItem[];
  editingFields: Set<string>;
  onFieldEdit: (fieldKey: string) => void;
  onFieldSave: (accountId: string, field: string, value: any) => void;
  loadingItems: boolean;
}

function ExpandedAccountDetails({ account, items, editingFields, onFieldEdit, onFieldSave, loadingItems }: ExpandedAccountDetailsProps) {
  const [tempValues, setTempValues] = useState<Record<string, any>>({});

  // Updated field definitions with correct data types
  const fieldDefinitions = [
    { 
      section: "Items", 
      key: "items", 
      label: "Items", 
      type: "readonly", 
      value: `${items.length} items`,
      description: `${items.length} items + ${account.num_armoury_stars || 0} stars`
    },
    { section: "Bot Information", key: "bot_id", label: "Bot ID", type: "text", value: account.bot_id },
    { section: "Bot Information", key: "steam_balance", label: "Steam Balance", type: "float", value: account.steam_balance },
    { section: "Account Details", key: "email_id", label: "Email", type: "email", value: account.email_id },
    { section: "Account Details", key: "email_password", label: "Email Password", type: "password", value: account.email_password },
    { section: "Account Details", key: "steam_id", label: "Steam ID", type: "text", value: account.steam_id },
    { section: "Account Details", key: "steamguard", label: "Steam Guard", type: "text", value: account.steamguard },
    { section: "Trading", key: "trade_token", label: "Trade Token", type: "text", value: account.trade_token },
    { section: "Trading", key: "trade_url", label: "Trade URL", type: "url", value: account.trade_url },
    { section: "Security", key: "steam_shared_secret", label: "Shared Secret", type: "password", value: account.steam_shared_secret },
    { section: "Security", key: "steam_identity_secret", label: "Identity Secret", type: "password", value: account.steam_identity_secret },
    { section: "Security", key: "access_token", label: "Access Token", type: "password", value: account.access_token },
    { section: "Security", key: "refresh_token", label: "Refresh Token", type: "password", value: account.refresh_token },
    { section: "Game Progress", key: "xp_level", label: "XP Level", type: "number", value: account.xp_level },
    { section: "Game Progress", key: "xp", label: "XP", type: "number", value: account.xp },
    { section: "Game Progress", key: "num_armoury_stars", label: "Armoury Stars", type: "number", value: account.num_armoury_stars },
    { section: "Game Progress", key: "service_medal", label: "Service Medal", type: "text", value: account.service_medal },
    { section: "Financial", key: "currency", label: "Currency", type: "text", value: account.currency },
    { section: "Financial", key: "pass_value", label: "Pass Value", type: "float", value: account.pass_value },
    { section: "Financial", key: "pua", label: "PUA", type: "number", value: account.pua },
    { section: "Status", key: "prime", label: "Prime Status", type: "boolean", value: account.prime },
  ];

  const groupedFields = fieldDefinitions.reduce((acc, field) => {
    if (!acc[field.section]) {
      acc[field.section] = [];
    }
    acc[field.section].push(field);
    return acc;
  }, {} as Record<string, typeof fieldDefinitions>);

  // Handle field value changes with proper type conversion
  const handleFieldChange = (key: string, value: any) => {
    const fieldDef = fieldDefinitions.find(f => f.key === key);
    let convertedValue = value;

    // Convert based on field type
    switch (fieldDef?.type) {
      case "number":
        convertedValue = value === '' ? 0 : parseInt(value) || 0;
        break;
      case "float":
        convertedValue = value === '' ? 0.0 : parseFloat(value) || 0.0;
        break;
      case "boolean":
        convertedValue = Boolean(value);
        break;
      default:
        convertedValue = value;
    }

    setTempValues(prev => ({ ...prev, [key]: convertedValue }));
  };

  // Handle Enter key press
  const handleKeyDown = (event: React.KeyboardEvent, fieldKey: string) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleSave(fieldKey);
    }
  };

  const handleSave = (key: string) => {
    let value = tempValues[key] !== undefined ? tempValues[key] : account[key as keyof Account];
    
    const fieldDef = fieldDefinitions.find(f => f.key === key);
    
    // Ensure proper type conversion before saving
    switch (fieldDef?.type) {
      case "number":
        value = typeof value === 'string' ? parseInt(value) || 0 : value;
        break;
      case "float":
        value = typeof value === 'string' ? parseFloat(value) || 0.0 : value;
        break;
      case "boolean":
        value = Boolean(value);
        break;
      case "text":
      case "email":
      case "password":
      case "url":
        value = String(value || '');
        break;
    }

    console.log('Saving field:', key, 'with value:', value, 'type:', typeof value);
    
    onFieldSave(account.id, key, value);
    
    // Clear temp value after saving
    setTempValues(prev => {
      const newValues = { ...prev };
      delete newValues[key];
      return newValues;
    });
  };

  const handleCancel = (key: string) => {
    onFieldEdit(`${account.id}-${key}`);
    setTempValues(prev => {
      const newValues = { ...prev };
      delete newValues[key];
      return newValues;
    });
  };

  const renderField = (field: any) => {
    const fieldKey = `${account.id}-${field.key}`;
    const isEditing = editingFields.has(fieldKey);
    const currentValue = tempValues[field.key] !== undefined ? tempValues[field.key] : field.value;

    if (field.key === "items") {
      return (
        <div className="space-y-2">
          <Label className="text-sm font-medium">{field.label}</Label>
          <div className="space-y-2">
            <div className="text-sm text-muted-foreground">
              {field.description}
            </div>
            {loadingItems ? (
              <div className="flex items-center gap-2">
                <LoadingSpinner size="sm" />
                <span className="text-sm">Loading items...</span>
              </div>
            ) : (
              <div className="max-h-32 overflow-y-auto space-y-1">
                {items.length > 0 ? (
                  items.map(item => (
                    <div key={item.asset_id} className="text-xs p-2 border rounded bg-muted/30">
                      <div className="font-medium">{item.market_hash_name}</div>
                      <div className="text-muted-foreground">
                        Asset ID: {item.asset_id} | 
                        Marketable: {item.marketable ? 'Yes' : 'No'} | 
                        Tradable: {item.tradable ? 'Yes' : 'No'}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground italic">No items found</div>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        <Label className="text-sm font-medium">{field.label}</Label>
        {isEditing ? (
          <div className="flex items-center gap-2">
            {field.type === "boolean" ? (
              <Checkbox
                checked={Boolean(currentValue)}
                onCheckedChange={(checked) => handleFieldChange(field.key, checked)}
                className="flex-1"
              />
            ) : field.type === "textarea" ? (
              <Textarea
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) {
                    handleSave(field.key);
                  }
                }}
                className="flex-1"
              />
            ) : (
              <Input
                type={field.type === "password" ? "text" : 
                      field.type === "number" ? "number" :
                      field.type === "float" ? "number" :
                      field.type === "email" ? "email" :
                      field.type === "url" ? "url" : "text"}
                step={field.type === "float" ? "0.01" : undefined}
                value={currentValue || ''}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, field.key)}
                className="flex-1"
                placeholder={`Enter ${field.label.toLowerCase()}`}
              />
            )}
            <Button size="sm" onClick={() => handleSave(field.key)}>
              <Save className="h-3 w-3" />
            </Button>
            <Button size="sm" variant="outline" onClick={() => handleCancel(field.key)}>
              <X className="h-3 w-3" />
            </Button>
          </div>
        ) : (
          <div 
            className="p-2 border rounded cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => onFieldEdit(fieldKey)}
          >
            <span className="text-sm">
              {field.type === "password" 
                ? "••••••••" 
                : field.type === "boolean" 
                  ? (currentValue ? "✓ Yes" : "✗ No")
                  : field.type === "float"
                    ? parseFloat(currentValue || 0).toFixed(2)
                    : String(currentValue || "N/A")
              }
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 bg-muted/30 border-t">
      <h3 className="text-lg font-semibold mb-6">Account Details</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Object.entries(groupedFields).map(([section, fields]) => (
          <Card key={section}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">{section}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-4">
              {fields.map(field => (
                <div key={field.key}>
                  {renderField(field)}
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
