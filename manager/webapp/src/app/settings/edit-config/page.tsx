"use client";

import React, { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboardlayout';
import { PageHeader } from '@/components/pageheader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { AlertCircle, Save } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from "sonner";

// Define type for config keys based on YAML structure
type ConfigKey = 'USE_PROXIES' | 'STEAM_ITEMS_LISTER_MULTIPLIER' | 'MAX_CLEANUP_ATTEMPTS' | 
  'INITIAL_CLEANUP_PRICE_MULTIPLIER' | 'CLEANUP_PRICE_DECREMENT' | 'ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS' | 
  'MAX_ITEMS_LIMIT' | 'SELLING_TIME_WAIT' | 'NUM_PASSES_REQUIRED' | 'N_EPOCHS' | 'MARKET_HASH_NAME_DEFAULT' | 
  'MAX_SPLITS' | 'OUTPUT_CHUNK_LENGTH_DEFAULT' | 'MANUAL_ITEMS_SENDER_MULTIPLIER' | 'MAIN_ACCOUNT_TRADE_URL' | 
  'ACCOUNT_INVENTORY_SEMAPHORE_MANUAL_SENDER' | 'ITEMS_DATA_UPDATER_ACCOUNTS_SEMAPHORE' | 
  'PERCENTAGE_OF_LOWEST_BUY_THRESHOLD' | 'OUTDATED_TIME_SECONDS' | 'OUTDATED_TIME_SECONDS_MAIN' | 
  'threshold_calculator_setup_cost' | 'threshold_calculator_batch_passes_cost' | 'threshold_calculator_profit_scenario1' | 
  'threshold_calculator_profit_scenario2' | 'threshold_calculator_weekly_bonus' | 'threshold_calculator_farming_hours' | 
  'threshold_calculator_simulation_years';

// Default constants matching the YAML structure
const defaultConstants = {
  USE_PROXIES: true,
  STEAM_ITEMS_LISTER_MULTIPLIER: 1,
  MAX_CLEANUP_ATTEMPTS: 5,
  INITIAL_CLEANUP_PRICE_MULTIPLIER: 0.985,
  CLEANUP_PRICE_DECREMENT: 0.02,
  ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS: 10,
  MAX_ITEMS_LIMIT: 0,
  SELLING_TIME_WAIT: 25,
  NUM_PASSES_REQUIRED: 5,
  N_EPOCHS: 50,
  MARKET_HASH_NAME_DEFAULT: "Fever Case",
  MAX_SPLITS: 5,
  OUTPUT_CHUNK_LENGTH_DEFAULT: 24,
  MANUAL_ITEMS_SENDER_MULTIPLIER: 1,
  MAIN_ACCOUNT_TRADE_URL: "https://steamcommunity.com/tradeoffer/new/?partner=1597113567&token=zXZIog_y",
  ACCOUNT_INVENTORY_SEMAPHORE_MANUAL_SENDER: 5,
  ITEMS_DATA_UPDATER_ACCOUNTS_SEMAPHORE: 5,
  PERCENTAGE_OF_LOWEST_BUY_THRESHOLD: 0.99,
  OUTDATED_TIME_SECONDS: 120,
  OUTDATED_TIME_SECONDS_MAIN: 20,
  threshold_calculator_setup_cost: 1190,
  threshold_calculator_batch_passes_cost: 6275,
  threshold_calculator_profit_scenario1: 1190,
  threshold_calculator_profit_scenario2: 1360,
  threshold_calculator_weekly_bonus: 50,
  threshold_calculator_farming_hours: 15,
  threshold_calculator_simulation_years: 3
};

// Config keys organized by category
const configGroups = {
  "Global": ["USE_PROXIES"],
  "Steam Items Lister": [
    "STEAM_ITEMS_LISTER_MULTIPLIER",
    "MAX_CLEANUP_ATTEMPTS",
    "INITIAL_CLEANUP_PRICE_MULTIPLIER",
    "CLEANUP_PRICE_DECREMENT",
    "ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS",
    "MAX_ITEMS_LIMIT",
    "SELLING_TIME_WAIT",
    "NUM_PASSES_REQUIRED"
  ],
  "Schedule Generator": [
    "N_EPOCHS",
    "MARKET_HASH_NAME_DEFAULT",
    "MAX_SPLITS",
    "OUTPUT_CHUNK_LENGTH_DEFAULT"
  ],
  "Manual Items Sender": [
    "MANUAL_ITEMS_SENDER_MULTIPLIER",
    "MAIN_ACCOUNT_TRADE_URL",
    "ACCOUNT_INVENTORY_SEMAPHORE_MANUAL_SENDER"
  ],
  "Items Data Updater": [
    "ITEMS_DATA_UPDATER_ACCOUNTS_SEMAPHORE"
  ],
  "Price Utils": [
    "PERCENTAGE_OF_LOWEST_BUY_THRESHOLD",
    "OUTDATED_TIME_SECONDS",
    "OUTDATED_TIME_SECONDS_MAIN"
  ],
  "Threshold Calculator": [
    "threshold_calculator_setup_cost",
    "threshold_calculator_batch_passes_cost",
    "threshold_calculator_profit_scenario1",
    "threshold_calculator_profit_scenario2",
    "threshold_calculator_weekly_bonus",
    "threshold_calculator_farming_hours",
    "threshold_calculator_simulation_years"
  ]
};

const configKeys = Object.keys(defaultConstants) as ReadonlyArray<ConfigKey>;

// Sample notifications for the PageHeader
const initialNotifications = [
  { id: 1, title: 'Config Editor Loaded', message: 'Configuration editor loaded successfully', time: '17:50', type: 'success' as const, read: false },
];

export default function EditConfigPage() {
  // State for notifications
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );

  // State for config editor
  const [constants, setConstants] = useState<Record<string, any>>(defaultConstants);
  const [configLoaded, setConfigLoaded] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [configTab, setConfigTab] = useState<string>("Global");
  const [logs, setLogs] = useState<string[]>([]);
  
  // Function to add logs
  const addLog = (message: string) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  // Load config from API endpoint
  useEffect(() => {
    const loadConfig = async () => {
      try {
        // Fetch configuration from our API endpoint
        const response = await fetch('/api/config');
        if (!response.ok) {
          throw new Error(`Failed to load configuration: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Only extract the keys we're interested in
        const filteredData: Record<string, any> = { ...defaultConstants };
        
        // Only update keys that exist in the response
        (configKeys as ReadonlyArray<ConfigKey>).forEach(key => {
          if (data[key] !== undefined) {
            // Handle different types appropriately
            if (typeof defaultConstants[key] === 'boolean') {
              filteredData[key] = data[key] === true || data[key] === 'True';
            } else if (typeof defaultConstants[key] === 'number') {
              filteredData[key] = Number(data[key]);
            } else {
              filteredData[key] = data[key];
            }
          }
        });
        
        setConstants(filteredData);
        setConfigLoaded(true);
        addLog("Configuration loaded successfully from YAML file");
        toast.success("Configuration loaded successfully");
      } catch (error) {
        console.error("Failed to load config:", error);
        addLog("Failed to load configuration. Using defaults.");
        toast.error("Failed to load configuration. Using defaults.");
        setConstants(defaultConstants);
        setConfigLoaded(true);
      }
    };
    
    loadConfig();
  }, []);

  // Handle marking all notifications as read
  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  // Handle updating configuration values
  const handleConfigChange = (key: string, value: any) => {
    setConstants(prev => ({
      ...prev,
      [key]: value
    }));
    addLog(`Updated ${key} to ${value}`);
  };

  // Save configuration changes
  const handleSaveConfig = async () => {
    setIsSaving(true);
    addLog("Saving configuration...");
    
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(constants),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to save configuration: ${response.status}`);
      }
      
      addLog("Configuration saved successfully");
      toast.success("Configuration saved successfully");
    } catch (error) {
      console.error("Failed to save config:", error);
      addLog(`Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
      toast.error("Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  };

  // Reset configuration to defaults
  const handleResetConfig = () => {
    setConstants({...defaultConstants});
    addLog("Configuration reset to defaults");
    toast.info("Configuration reset to defaults");
  };

  // Format a config key for display
  const formatConfigKey = (key: string): string => {
    return key
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  // Render input based on value type
  const renderConfigInput = (key: string, value: any) => {
    if (typeof value === 'boolean') {
      return (
        <div className="flex items-center space-x-2">
          <Switch 
            id={key} 
            checked={value} 
            onCheckedChange={(checked) => handleConfigChange(key, checked)}
          />
          <Label htmlFor={key}>{value ? 'Enabled' : 'Disabled'}</Label>
        </div>
      );
    } else if (typeof value === 'number') {
      return (
        <Input 
          id={key}
          type="number" 
          value={value} 
          onChange={(e) => handleConfigChange(key, parseFloat(e.target.value))}
          className="w-full"
        />
      );
    } else {
      return (
        <Input 
          id={key}
          type="text" 
          value={value as string} 
          onChange={(e) => handleConfigChange(key, e.target.value)}
          className="w-full"
        />
      );
    }
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="Edit Configuration"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle>Global Constants Editor</CardTitle>
            <CardDescription>
              Edit application configuration values (config.yaml)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!configLoaded ? (
              <div className="flex justify-center items-center p-8">
                <div className="animate-pulse text-center">
                  <p>Loading configuration...</p>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Configuration Editor</AlertTitle>
                  <AlertDescription>
                    Changes will not take effect until you save. Be careful when modifying these values as they can affect system behavior.
                  </AlertDescription>
                </Alert>
                
                <Tabs value={configTab} onValueChange={setConfigTab} className="w-full">
                  <TabsList className="flex flex-wrap h-auto">
                    {Object.keys(configGroups).map((group) => (
                      <TabsTrigger key={group} value={group} className="m-1">
                        {group}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                  
                  {Object.entries(configGroups).map(([group, keys]) => (
                    <TabsContent key={group} value={group} className="space-y-4 pt-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {keys.map((key) => (
                          <Card key={key} className="overflow-hidden">
                            <CardHeader className="bg-secondary/30 py-2">
                              <CardTitle className="text-md font-medium">{formatConfigKey(key)}</CardTitle>
                              <CardDescription>
                                {key === 'NUM_PASSES_REQUIRED' && 
                                  'Number of passes required to be bought after items lister runs'}
                                {key === 'USE_PROXIES' && 
                                  'Enable or disable usage of proxy servers'}
                              </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-4">
                              <div className="space-y-2">
                                {renderConfigInput(key, constants[key])}
                                {typeof constants[key] === 'number' && (
                                  <p className="text-xs text-muted-foreground">
                                    Default: {defaultConstants[key as keyof typeof defaultConstants]}
                                  </p>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </TabsContent>
                  ))}
                </Tabs>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button 
              variant="outline" 
              onClick={handleResetConfig}
              disabled={!configLoaded || isSaving}
            >
              Reset to Defaults
            </Button>
            <Button 
              onClick={handleSaveConfig}
              disabled={!configLoaded || isSaving}
            >
              {isSaving ? (
                <>
                  <span className="animate-pulse mr-2">Saving...</span>
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Configuration
                </>
              )}
            </Button>
          </CardFooter>
        </Card>
        
        <div className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Activity Log</CardTitle>
              <CardDescription>Recent configuration activity</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-secondary/50 rounded-md p-4 h-[200px] overflow-y-auto font-mono text-sm">
                {logs.map((log, index) => (
                  <div key={index} className="py-1 border-b border-secondary last:border-0">
                    {log}
                  </div>
                ))}
                {logs.length === 0 && (
                  <div className="text-muted-foreground italic">No logs to display</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
