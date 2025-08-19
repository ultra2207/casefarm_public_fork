"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Check, ChevronsUpDown, Info, Loader2, AlertCircle, StopCircle } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Import API utilities
import { accountsApi, listingApi, useListingWebSocket } from "@/lib";
import type { ApiAccount } from "@/lib/types";

// ... (keeping all the existing types and constants the same)

// Notification types
type NotificationType = "info" | "success" | "warning" | "error";

interface Notification {
  id: number;
  title: string;
  message: string;
  time: string;
  type: NotificationType;
  read: boolean;
}

// Sample initial notifications
const initialNotifications: Notification[] = [
  { 
    id: 1, 
    title: 'Items Seller Configuration', 
    message: 'Default configuration loaded',
    time: '15:19', 
    type: 'info', 
    read: false 
  },
  { 
    id: 2, 
    title: 'System Update', 
    message: 'Steam API connection established',
    time: '14:45', 
    type: 'success', 
    read: false 
  }
];

// Define config keys as a tuple to maintain proper typing
const configKeys = [
  "STEAM_ITEMS_LISTER_MULTIPLIER",
  "MAX_CLEANUP_ATTEMPTS",
  "INITIAL_CLEANUP_PRICE_MULTIPLIER",
  "CLEANUP_PRICE_DECREMENT",
  "ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS",
  "MAX_ITEMS_LIMIT",
  "SELLING_TIME_WAIT"
] as const;

// Create a type from our config keys
type ConfigKey = typeof configKeys[number];

// Default constants as fallback with proper typing
const defaultConstants: Record<ConfigKey, number> = {
  STEAM_ITEMS_LISTER_MULTIPLIER: 1,
  MAX_CLEANUP_ATTEMPTS: 5,
  INITIAL_CLEANUP_PRICE_MULTIPLIER: 0.985,
  CLEANUP_PRICE_DECREMENT: 0.02,
  ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS: 10,
  MAX_ITEMS_LIMIT: 0,
  SELLING_TIME_WAIT: 25
};

// Descriptions for each setting with proper typing
const constantDescriptions: Record<ConfigKey, string> = {
  STEAM_ITEMS_LISTER_MULTIPLIER: "Multiplier should be set to 1 in production or 10 in testing",
  MAX_CLEANUP_ATTEMPTS: "How many times it tries to sell unsold items",
  INITIAL_CLEANUP_PRICE_MULTIPLIER: "The lower multiplier used for unsold items to sell them quickly",
  CLEANUP_PRICE_DECREMENT: "By what amount should multiplier go down every time",
  ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS: "What concurrency to use when getting inventories",
  MAX_ITEMS_LIMIT: "Max number of items each account should be allowed to sell, set to 0 for no limit",
  SELLING_TIME_WAIT: "How long program waits before checking if all items are sold in a round"
};

export default function ItemsSellerPage() {
  // Notification state
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState<number>(
    initialNotifications.filter(notification => !notification.read).length
  );

  // API data state
  const [accounts, setAccounts] = useState<ApiAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState<boolean>(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);

  // Seller configuration state
  const [selectedSellers, setSelectedSellers] = useState<string[]>([]);
  const [constants, setConstants] = useState<Record<ConfigKey, number>>(defaultConstants);
  const [configLoaded, setConfigLoaded] = useState<boolean>(false);
  
  // Task state
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  
  // Stop confirmation state
  const [showStopConfirmation, setShowStopConfirmation] = useState<boolean>(false);
  const [isStopping, setIsStopping] = useState<boolean>(false);
  
  // UI state
  const [sellerPopoverOpen, setSellerPopoverOpen] = useState<boolean>(false);
  
  // WebSocket integration - using the fixed hook
  const { progress, logs, isConnected, clearLogs, connectionError } = useListingWebSocket(currentTaskId);
  
  // Refs for auto-scroll
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Helper function to create notifications
  const createNotification = useCallback((
    title: string, 
    message: string, 
    type: NotificationType
  ): Notification => ({
    id: Date.now(),
    title,
    message,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    type,
    read: false
  }), []);

  // Helper function to add notification
  const addNotification = useCallback((notification: Notification) => {
    setNotifications(prev => [notification, ...prev]);
    setUnreadNotifications(prev => prev + 1);
  }, []);

  // Auto-scroll function with debouncing
  const scrollToBottom = useCallback(() => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    
    scrollTimeoutRef.current = setTimeout(() => {
      if (logsContainerRef.current) {
        logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
      }
    }, 100);
  }, []);

  // Handle WebSocket progress updates
  const handleProgressUpdate = useCallback((currentProgress: typeof progress) => {
    if (!currentProgress) return;
    
    if (currentProgress.type === 'completed') {
      const notification = createNotification(
        'Items Listing Complete',
        currentProgress.result 
          ? 'All items have been successfully listed' 
          : 'Listing completed with some errors',
        currentProgress.result ? 'success' : 'warning'
      );
      
      addNotification(notification);
      setCurrentTaskId(null);
      setIsStopping(false);
    } else if (currentProgress.type === 'error') {
      const errorMessage = currentProgress.error || 'Unknown error occurred';
      setTaskError(errorMessage);
      
      const notification = createNotification(
        'Items Listing Error',
        errorMessage,
        'error'
      );
      
      addNotification(notification);
      setCurrentTaskId(null);
      setIsStopping(false);
    } else if (currentProgress.type === 'stopped') {
      const notification = createNotification(
        'Items Listing Stopped',
        'The listing process has been stopped by user request',
        'warning'
      );
      
      addNotification(notification);
      setCurrentTaskId(null);
      setIsStopping(false);
    }
  }, [createNotification, addNotification]);

  // Handle marking all notifications as read
  const handleMarkAllRead = useCallback(() => {
    setNotifications(prev => prev.map(notification => ({
      ...notification,
      read: true
    })));
    setUnreadNotifications(0);
  }, []);

  // Update a constant value
  const updateConstant = useCallback((key: ConfigKey, value: string) => {
    let parsedValue: number;
    
    if (value === "") {
      parsedValue = 0;
    } else {
      parsedValue = parseFloat(value);
      if (isNaN(parsedValue)) {
        return;
      }
    }
    
    setConstants(prev => ({
      ...prev,
      [key]: parsedValue
    }));
  }, []);

  // Reset constants to default values
  const resetConstants = useCallback(() => {
    setConstants({ ...defaultConstants });
    console.log("Constants reset to default values");
    
    const notification = createNotification(
      'Configuration Reset',
      'Constants have been reset to default values',
      'info'
    );
    addNotification(notification);
  }, [createNotification, addNotification]);

  // Toggle seller selection
  const toggleSellerAccount = useCallback((accountId: string) => {
    setSelectedSellers(current =>
      current.includes(accountId)
        ? current.filter(id => id !== accountId)
        : [...current, accountId]
    );
  }, []);

  // Select all sellers
  const selectAllSellers = useCallback(() => {
    const activeAccounts = accounts.filter(account => 
      account.steam_username && 
      account.status !== 'disabled' &&
      account.status !== 'banned'
    );
    setSelectedSellers(activeAccounts.map(account => account.steam_username!));
  }, [accounts]);

  // Clear all seller selections
  const clearAllSellers = useCallback(() => {
    setSelectedSellers([]);
  }, []);

  // Start the actual listing process
  const startListing = useCallback(async () => {
    if (selectedSellers.length === 0) {
      setTaskError("Please select at least one seller account");
      
      const notification = createNotification(
        'Selection Required',
        'Please select at least one seller account',
        'warning'
      );
      addNotification(notification);
      return;
    }

    try {
      setTaskError(null);
      clearLogs();
      setIsStopping(false);
      
      console.log(`Starting listing process with ${selectedSellers.length} seller accounts`);

      const response = await listingApi.startListing(selectedSellers);
      setCurrentTaskId(response.task_id);

      const notification = createNotification(
        'Items Listing Started',
        `Started listing items from ${selectedSellers.length} account(s)`,
        'info'
      );
      addNotification(notification);
      
      console.log(`Task started with ID: ${response.task_id}`);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start listing process';
      setTaskError(errorMessage);
      console.error(`Error starting listing process: ${errorMessage}`);
      
      const notification = createNotification(
        'Listing Start Failed',
        errorMessage,
        'error'
      );
      addNotification(notification);
    }
  }, [selectedSellers, clearLogs, createNotification, addNotification]);

  // Stop the listing process
  const stopListing = useCallback(async () => {
    if (!currentTaskId) return;

    try {
      setIsStopping(true);
      setTaskError(null);
      
      console.log(`Stopping listing process with task ID: ${currentTaskId}`);

      await listingApi.stopListing(currentTaskId);

      const notification = createNotification(
        'Stop Request Sent',
        'Stop request has been sent. The process will stop after completing the current operation.',
        'info'
      );
      addNotification(notification);
      
      console.log(`Stop request sent for task: ${currentTaskId}`);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to stop listing process';
      setTaskError(errorMessage);
      setIsStopping(false);
      console.error(`Error stopping listing process: ${errorMessage}`);
      
      const notification = createNotification(
        'Stop Request Failed',
        errorMessage,
        'error'
      );
      addNotification(notification);
    }
  }, [currentTaskId, createNotification, addNotification]);

  // Handle stop button click (show confirmation)
  const handleStopClick = useCallback(() => {
    setShowStopConfirmation(true);
  }, []);

  // Handle stop confirmation
  const handleStopConfirm = useCallback(() => {
    setShowStopConfirmation(false);
    stopListing();
  }, [stopListing]);

  // Handle stop cancellation
  const handleStopCancel = useCallback(() => {
    setShowStopConfirmation(false);
  }, []);

  // Handle input change for config constants
  const handleConstantChange = useCallback((key: ConfigKey) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    updateConstant(key, e.target.value);
  }, [updateConstant]);

  // Handle seller account selection
  const handleSellerSelect = useCallback((username: string) => () => {
    toggleSellerAccount(username);
  }, [toggleSellerAccount]);

  // Handle popover state changes
  const handlePopoverChange = useCallback((open: boolean) => {
    setSellerPopoverOpen(open);
  }, []);

  // Auto-scroll when new logs arrive
  useEffect(() => {
    if (logs.length > 0) {
      scrollToBottom();
    }
    
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [logs.length, scrollToBottom]);

  // Load accounts from API
  useEffect(() => {
    let isMounted = true;
    
    const loadAccounts = async () => {
      try {
        setAccountsLoading(true);
        setAccountsError(null);
        
        const accountsData = await accountsApi.getAccounts(0, 500);
        
        if (isMounted) {
          setAccounts(accountsData);
          console.log(`Loaded ${accountsData.length} accounts from database`);
          
          const notification = createNotification(
            'Accounts Loaded',
            `Successfully loaded ${accountsData.length} accounts from database`,
            'success'
          );
          addNotification(notification);
        }
      } catch (error) {
        if (isMounted) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to load accounts';
          setAccountsError(errorMessage);
          console.error(`Error loading accounts: ${errorMessage}`);
          
          const notification = createNotification(
            'Account Loading Failed',
            errorMessage,
            'error'
          );
          addNotification(notification);
        }
      } finally {
        if (isMounted) {
          setAccountsLoading(false);
        }
      }
    };
    
    loadAccounts();
    
    return () => {
      isMounted = false;
    };
  }, [createNotification, addNotification]);

  // Load config from API endpoint
  useEffect(() => {
    let isMounted = true;
    
    const loadConfig = async () => {
      try {
        const response = await fetch('/api/config');
        if (!response.ok) {
          throw new Error(`Failed to load configuration: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (isMounted) {
          const filteredData: Record<ConfigKey, number> = { ...defaultConstants };
          
          (configKeys as ReadonlyArray<ConfigKey>).forEach(key => {
            if (data[key] !== undefined) {
              filteredData[key] = Number(data[key]);
            }
          });
          
          setConstants(filteredData);
          setConfigLoaded(true);
          console.log("Configuration loaded successfully from YAML file");
        }
      } catch (error) {
        if (isMounted) {
          console.error("Failed to load config:", error);
          console.log("Failed to load configuration. Using defaults.");
          setConstants(defaultConstants);
          setConfigLoaded(true);
          
          const notification = createNotification(
            'Configuration Warning',
            'Failed to load configuration. Using default values.',
            'warning'
          );
          addNotification(notification);
        }
      }
    };
    
    loadConfig();
    
    return () => {
      isMounted = false;
    };
  }, [createNotification, addNotification]);

  // Handle progress updates
  useEffect(() => {
    handleProgressUpdate(progress);
  }, [progress, handleProgressUpdate]);

  // Get active accounts for selection - memoize to prevent re-renders
  const selectableAccounts = useMemo(() => {
    return accounts.filter(account => 
      account.steam_username && 
      account.status !== 'disabled' &&
      account.status !== 'banned'
    );
  }, [accounts]);

  // Check if all sellers are selected
  const isAllSellersSelected = useMemo(() => {
    return selectedSellers.length === selectableAccounts.length && selectableAccounts.length > 0;
  }, [selectedSellers.length, selectableAccounts.length]);

  // Check if currently processing
  const isProcessing = useMemo(() => {
    return currentTaskId !== null && progress?.type !== 'completed' && progress?.type !== 'error' && progress?.type !== 'stopped';
  }, [currentTaskId, progress?.type]);

  // Get button text for seller selection
  const getSellerButtonText = useMemo(() => {
    if (accountsLoading) {
      return (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading accounts...
        </>
      );
    }
    
    if (selectedSellers.length > 0) {
      return `${selectedSellers.length} sellers selected`;
    }
    
    return "Select seller accounts";
  }, [accountsLoading, selectedSellers.length]);

  return (
    <DashboardLayout>
      <PageHeader
        title="Items Seller"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
        <Card>
          <CardHeader>
            <CardTitle>Selling Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Connection Status */}
            {isConnected && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Connected to real-time updates
                </AlertDescription>
              </Alert>
            )}

            {/* Error Display */}
            {(accountsError || taskError || connectionError) && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {accountsError || taskError || connectionError}
                </AlertDescription>
              </Alert>
            )}

            {/* Seller Selection */}
            <div className="space-y-2">
              <Label htmlFor="sellers">Seller Accounts</Label>
              <Popover open={sellerPopoverOpen} onOpenChange={handlePopoverChange}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between"
                    aria-expanded={sellerPopoverOpen}
                    disabled={accountsLoading || isProcessing}
                  >
                    {getSellerButtonText}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-full p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search accounts..." />
                    <CommandEmpty>
                      {accountsLoading ? "Loading..." : "No account found."}
                    </CommandEmpty>
                    <div className="max-h-64 overflow-auto">
                      <CommandGroup>
                        {/* Select All / Clear All Controls */}
                        {!accountsLoading && selectableAccounts.length > 0 && (
                          <CommandItem
                            value="select-all-control"
                            onSelect={isAllSellersSelected ? clearAllSellers : selectAllSellers}
                            className="bg-muted/50"
                          >
                            <Check
                              className={`mr-2 h-4 w-4 ${
                                isAllSellersSelected ? "opacity-100" : "opacity-0"
                              }`}
                            />
                            {isAllSellersSelected ? "Clear All" : "Select All"}
                          </CommandItem>
                        )}
                        
                        {/* Individual Account Items */}
                        {selectableAccounts.map((account) => (
                          <CommandItem
                            key={account.id}
                            value={account.steam_username!}
                            onSelect={handleSellerSelect(account.steam_username!)}
                          >
                            <Check
                              className={`mr-2 h-4 w-4 ${
                                selectedSellers.includes(account.steam_username!)
                                  ? "opacity-100"
                                  : "opacity-0"
                              }`}
                            />
                            <div className="flex flex-col">
                              <span>{account.steam_username}</span>
                              <span className="text-xs text-muted-foreground">
                                {account.status} • Level {account.xp_level} • {account.region}
                              </span>
                            </div>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </div>
                  </Command>
                </PopoverContent>
              </Popover>
              
              <div className="flex flex-wrap gap-2 mt-2">
                {selectedSellers.length > 0 && (
                  <>
                    {selectedSellers.slice(0, 5).map((username) => (
                      <Badge key={username} variant="secondary" className="px-2 py-1">
                        {username}
                      </Badge>
                    ))}
                    {selectedSellers.length > 5 && (
                      <Badge variant="outline">+{selectedSellers.length - 5} more</Badge>
                    )}
                  </>
                )}
              </div>
            </div>
            
            {/* Constants Configuration */}
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-medium">Steam Items Lister Constants</h3>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={resetConstants}
                  disabled={isProcessing}
                >
                  Reset to Defaults
                </Button>
              </div>
              
              <div className="space-y-4">
                {configKeys.map((key) => (
                  <div key={key} className="grid grid-cols-[1fr_1fr] gap-4 items-start">
                    <div className="space-y-2">
                      <Label htmlFor={key} className="flex items-center gap-1">
                        {key.split('_').map(word => word.charAt(0) + word.slice(1).toLowerCase()).join(' ')}
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <Info className="h-4 w-4 text-muted-foreground ml-1" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-sm">
                              {constantDescriptions[key]}
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </Label>
                      <Input
                        id={key}
                        type="number"
                        step={key === "INITIAL_CLEANUP_PRICE_MULTIPLIER" ? "0.001" : 
                             key === "CLEANUP_PRICE_DECREMENT" ? "0.01" : "1"}
                        min={key === "MAX_ITEMS_LIMIT" ? "0" : undefined}
                        value={constants[key]}
                        onChange={handleConstantChange(key)}
                        className="w-full"
                        disabled={isProcessing}
                      />
                    </div>
                    <div className="text-sm text-muted-foreground pt-8">
                      {constantDescriptions[key]}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Start/Stop Buttons */}
            <div className="flex gap-2">
              {!isProcessing ? (
                <Button 
                  className="flex-1" 
                  disabled={accountsLoading || selectedSellers.length === 0}
                  onClick={startListing}
                >
                  <Loader2 className="mr-2 h-4 w-4 animate-spin opacity-0" />
                  Start Listing Items
                </Button>
              ) : (
                <>
                  <Button 
                    className="flex-1" 
                    disabled
                    variant="secondary"
                  >
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </Button>
                  <Button 
                    variant="destructive"
                    onClick={handleStopClick}
                    disabled={isStopping}
                  >
                    {isStopping ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Stopping...
                      </>
                    ) : (
                      <>
                        <StopCircle className="mr-2 h-4 w-4" />
                        Stop
                      </>
                    )}
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
        
        {/* Progress and Logs Card */}
        <Card>
          <CardHeader>
            <CardTitle>Progress & Logs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>
                  {progress?.type === 'progress' ? `Processing: ${progress.message}` : 
                   isStopping ? "Stopping..." : "Waiting to start"}
                </span>
                <span>
                  {currentTaskId ? `Task: ${currentTaskId.slice(0, 8)}...` : ""}
                </span>
              </div>
              <Progress 
                value={progress?.percentage || 0} 
                className="h-2" 
              />
              <div className="text-xs text-right text-muted-foreground">
                {progress ? (
                  `${progress.current}/${progress.total} (${progress.percentage?.toFixed(1) || '0'}%)`
                ) : (
                  "0% Complete"
                )}
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <Label>Real-time Logs</Label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearLogs}
                  disabled={logs.length === 0}
                >
                  Clear Logs
                </Button>
              </div>
              
              {/* Fixed logs container without ScrollArea */}
              <div className="border border-muted rounded-md">
                <div 
                  ref={logsContainerRef}
                  className="h-[300px] w-full p-4 overflow-auto bg-background font-mono text-sm"
                >
                  <div className="space-y-1">
                    {!configLoaded && (
                      <div className="text-amber-600">
                        Loading configuration...
                      </div>
                    )}
                    {accountsLoading && (
                      <div className="text-blue-600">
                        Loading accounts from database...
                      </div>
                    )}
                    {logs.length > 0 ? (
                      logs.map((log, index) => (
                        <div 
                          key={index} 
                          className={`break-words ${
                            log.error ? 'text-red-600' : 
                            log.info ? 'text-blue-600' : 
                            log.separator ? 'text-yellow-600 font-bold' :
                            log.historical ? 'text-gray-500' : 'text-foreground'
                          }`}
                        >
                          {log.message}
                        </div>
                      ))
                    ) : (
                      <div className="text-muted-foreground">
                        {isConnected 
                          ? "Connected to real-time logs. Logs will appear here once the process starts."
                          : "Logs will appear here once the process starts"
                        }
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stop Confirmation Dialog */}
      <AlertDialog open={showStopConfirmation} onOpenChange={setShowStopConfirmation}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Stop Listing Process</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to stop the items listing process? 
              <br /><br />
              The process will stop gracefully after completing the current operation. 
              Any items that have already been listed will remain listed on the marketplace.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleStopCancel}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleStopConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Stop Process
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardLayout>
  );
}
