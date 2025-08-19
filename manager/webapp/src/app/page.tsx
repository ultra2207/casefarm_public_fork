"use client";

import React, { useState } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { 
  ChevronDown,
  Activity,
  Shield,
  Store,
  Repeat,
  Server,
  Info,
  AlertTriangle,
  AlertOctagon,
  ArrowRight,
  DollarSign} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Collapsible, 
  CollapsibleContent, 
  CollapsibleTrigger 
} from "@/components/ui/collapsible";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";

// Mock data for running modules
interface RunningModule {
  id: number;
  name: string;
  accounts: {
    username: string;
    status?: string;
  }[];
  latestLog: string;
  logLevel: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  timeAgo: string;
  status: 'success' | 'running' | 'error';
  logs: {
    message: string;
    level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
    time: string;
  }[];
  progress: number;
  startTime: string;
  estimatedTimeLeft: string;
}

// Mock data for bot activities
interface BotActivity {
  id: number;
  activity: string;
  count: number;
  icon: React.ReactNode;
  accounts: string[];
  logs?: string[];
  bots?: {
    name: string;
    progress: number;
    startTime: string;
    estimatedTimeLeft: string;
  }[];
}

// Mock scheduled events
interface ScheduledEvent {
  id: number;
  type: string;
  summary: string;
  accounts: {
    username: string;
    status?: string;
    type?: 'sender' | 'receiver';
  }[];
  time: string;
  formattedTime: string;
  details?: string;
  config?: {
    useSemaphore: boolean;
    useProxies: boolean;
    maxRetries: number;
    timeout: number;
  };
}

// Mock data for notification
interface Notification {
  id: number;
  title: string;
  message: string;
  time: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
}

// Mock running modules data with updated log format
const runningModules: RunningModule[] = [
  { 
    id: 1, 
    name: 'Steam Items Lister', 
    accounts: [
      { username: 'steam_user123' },
      { username: 'gaben_fan456' },
      { username: 'csgo_lover789' },
      { username: 'valve_player234' },
      { username: 'case_opener567' }
    ],
    latestLog: 'Total items listed on Steam Market: 5',
    logLevel: 'INFO',
    timeAgo: '2m ago',
    status: 'success',
    logs: [
      { message: 'Starting Steam Items Lister for 5 accounts', level: 'INFO', time: '12:30 PM' },
      { message: 'Connecting to Steam API', level: 'INFO', time: '12:31 PM' },
      { message: 'Connection successful', level: 'INFO', time: '12:32 PM' },
      { message: 'Fetching inventory items', level: 'INFO', time: '12:33 PM' },
      { message: 'Found 12 items eligible for listing', level: 'INFO', time: '12:34 PM' },
      { message: 'Starting listing process', level: 'INFO', time: '12:35 PM' },
      { message: 'Total items listed on Steam Market: 5', level: 'INFO', time: '12:36 PM' }
    ],
    progress: 100,
    startTime: '12:30 PM',
    estimatedTimeLeft: '0m'
  },
  { 
    id: 2, 
    name: 'Items Trader', 
    accounts: [
      { username: 'trader_pro456' }
    ],
    latestLog: 'Processing trade offers (2/5)',
    logLevel: 'INFO',
    timeAgo: '12m ago',
    status: 'running',
    logs: [
      { message: 'Starting Items Trader for trader_pro456', level: 'INFO', time: '12:20 PM' },
      { message: 'Checking for new trade offers', level: 'INFO', time: '12:21 PM' },
      { message: 'Found 5 new trade offers', level: 'INFO', time: '12:22 PM' },
      { message: 'Analyzing trade 1/5', level: 'INFO', time: '12:23 PM' },
      { message: 'Trade 1/5 accepted', level: 'INFO', time: '12:24 PM' },
      { message: 'Analyzing trade 2/5', level: 'INFO', time: '12:25 PM' },
      { message: 'Processing trade offers (2/5)', level: 'INFO', time: '12:26 PM' }
    ],
    progress: 40,
    startTime: '12:20 PM',
    estimatedTimeLeft: '8m'
  },
  { 
    id: 3, 
    name: 'Armoury Pass Farmer', 
    accounts: [
      { username: 'cs2_player789' }
    ],
    latestLog: 'Failed to purchase pass - insufficient funds',
    logLevel: 'ERROR',
    timeAgo: '19m ago',
    status: 'error',
    logs: [
      { message: 'Starting Armoury Pass Farmer for cs2_player789', level: 'INFO', time: '12:15 PM' },
      { message: 'Checking account balance', level: 'INFO', time: '12:16 PM' },
      { message: 'Current balance: $2.50', level: 'INFO', time: '12:17 PM' },
      { message: 'Balance may be insufficient for purchase', level: 'WARNING', time: '12:18 PM' },
      { message: 'Failed to purchase pass - insufficient funds', level: 'ERROR', time: '12:19 PM' }
    ],
    progress: 60,
    startTime: '12:15 PM',
    estimatedTimeLeft: 'Stopped'
  }
];

// Mock bot activities with accounts, logs and bot progress data
const botActivities: BotActivity[] = [
  { 
    id: 1, 
    activity: 'Bots Farming', 
    count: 15,
    icon: <Activity className="h-4 w-4 text-green-600 dark:text-green-400" />,
    accounts: [
      'farm_bot_01', 'farm_bot_02', 'farm_bot_03', 'farm_bot_04', 'farm_bot_05',
      'farm_bot_06', 'farm_bot_07', 'farm_bot_08', 'farm_bot_09', 'farm_bot_10',
      'farm_bot_11', 'farm_bot_12', 'farm_bot_13', 'farm_bot_14', 'farm_bot_15'
    ],
    logs: [
      'INFO | 12:10 PM | Started farming process | farm_bot_01',
      'INFO | 12:15 PM | Item drop received | farm_bot_03',
      'INFO | 12:20 PM | Level up detected | farm_bot_07',
      'INFO | 12:25 PM | Weekly drop limit reached | farm_bot_09'
    ],
    bots: [
      { name: 'farm_bot_01', progress: 85, startTime: '12:05 PM', estimatedTimeLeft: '10m' },
      { name: 'farm_bot_02', progress: 65, startTime: '12:10 PM', estimatedTimeLeft: '15m' },
      { name: 'farm_bot_03', progress: 92, startTime: '12:00 PM', estimatedTimeLeft: '5m' },
      { name: 'farm_bot_04', progress: 45, startTime: '12:15 PM', estimatedTimeLeft: '25m' },
      { name: 'farm_bot_05', progress: 70, startTime: '12:08 PM', estimatedTimeLeft: '12m' },
      { name: 'farm_bot_06', progress: 30, startTime: '12:20 PM', estimatedTimeLeft: '35m' },
      { name: 'farm_bot_07', progress: 60, startTime: '12:12 PM', estimatedTimeLeft: '18m' },
      { name: 'farm_bot_08', progress: 75, startTime: '12:07 PM', estimatedTimeLeft: '11m' },
      { name: 'farm_bot_09', progress: 95, startTime: '11:58 AM', estimatedTimeLeft: '2m' },
      { name: 'farm_bot_10', progress: 50, startTime: '12:14 PM', estimatedTimeLeft: '22m' },
      { name: 'farm_bot_11', progress: 40, startTime: '12:18 PM', estimatedTimeLeft: '28m' },
      { name: 'farm_bot_12', progress: 55, startTime: '12:13 PM', estimatedTimeLeft: '20m' },
      { name: 'farm_bot_13', progress: 20, startTime: '12:25 PM', estimatedTimeLeft: '40m' },
      { name: 'farm_bot_14', progress: 80, startTime: '12:06 PM', estimatedTimeLeft: '9m' },
      { name: 'farm_bot_15', progress: 35, startTime: '12:22 PM', estimatedTimeLeft: '30m' }
    ]
  },
  { 
    id: 2, 
    activity: 'Bots Selling Items', 
    count: 23,
    icon: <Store className="h-4 w-4 text-blue-600 dark:text-blue-400" />,
    accounts: Array(23).fill(0).map((_, i) => `seller_bot_${i+1}`),
    logs: [
      'INFO | 12:05 PM | Market analysis complete | seller_bot_1',
      'INFO | 12:12 PM | Listed 5 items on market | seller_bot_3',
      'INFO | 12:18 PM | Item sold for $3.45 | seller_bot_7',
      'WARNING | 12:22 PM | Market cooldown detected | seller_bot_12'
    ],
    bots: [
      { name: 'Combined Progress', progress: 62, startTime: '12:00 PM', estimatedTimeLeft: '25m' }
    ]
  },
  { 
    id: 3, 
    activity: 'Bots Sending Trades', 
    count: 12,
    icon: <Repeat className="h-4 w-4 text-purple-600 dark:text-purple-400" />,
    accounts: Array(12).fill(0).map((_, i) => `trade_bot_${i+1}`),
    logs: [
      'INFO | 12:00 PM | Trade offer sent | trade_bot_1',
      'INFO | 12:07 PM | Trade offer accepted | trade_bot_4',
      'ERROR | 12:16 PM | Trade declined | trade_bot_8',
      'INFO | 12:24 PM | New trade opportunity found | trade_bot_11'
    ],
    bots: [
      { name: 'Combined Progress', progress: 78, startTime: '12:02 PM', estimatedTimeLeft: '15m' }
    ]
  },
  { 
    id: 4, 
    activity: 'Bots Redeeming Passes', 
    count: 2,
    icon: <Shield className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
    accounts: ['redeem_bot_1', 'redeem_bot_2'],
    logs: [
      'INFO | 12:02 PM | Pass purchase successful | redeem_bot_1',
      'INFO | 12:08 PM | Pass redemption complete | redeem_bot_1',
      'INFO | 12:14 PM | Pass purchase successful | redeem_bot_2',
      'WARNING | 12:22 PM | Redemption cooldown in effect | redeem_bot_2'
    ],
    bots: [
      { name: 'redeem_bot_1', progress: 90, startTime: '12:00 PM', estimatedTimeLeft: '3m' },
      { name: 'redeem_bot_2', progress: 45, startTime: '12:14 PM', estimatedTimeLeft: '12m' }
    ]
  },
  { 
    id: 5, 
    activity: 'Bots Waiting for Balance', 
    count: 12,
    icon: <DollarSign className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />,
    accounts: Array(12).fill(0).map((_, i) => `balance_bot_${i+1}`),
    logs: [
      'WARNING | 12:18 PM | Insufficient balance detected | balance_bot_3',
      'WARNING | 12:20 PM | Waiting for balance top-up | balance_bot_7',
      'INFO | 12:23 PM | Balance check scheduled | balance_bot_11',
      'WARNING | 12:25 PM | Low balance threshold reached | balance_bot_1'
    ],
    bots: Array(12).fill(0).map((_, i) => ({
      name: `balance_bot_${i+1}`,
      progress: 0,
      startTime: '12:30 PM',
      estimatedTimeLeft: '--'
    }))
  },
  { 
    id: 6, 
    activity: 'Bots Waiting for VM Availability', 
    count: 2,
    icon: <Server className="h-4 w-4 text-red-600 dark:text-red-400" />,
    accounts: ['vm_bot_1', 'vm_bot_2'],
    logs: [
      'WARNING | 12:16 PM | No available VM slots | vm_bot_1',
      'INFO | 12:19 PM | Queued for next available VM | vm_bot_1',
      'WARNING | 12:21 PM | VM resource limit reached | vm_bot_2',
      'INFO | 12:24 PM | Monitoring VM availability | vm_bot_2'
    ],
    bots: [
      { name: 'vm_bot_1', progress: 0, startTime: '12:28 PM', estimatedTimeLeft: '--' },
      { name: 'vm_bot_2', progress: 0, startTime: '12:29 PM', estimatedTimeLeft: '--' }
    ]
  }
];



// Mock scheduled events
const scheduledEvents: ScheduledEvent[] = [
  { 
    id: 1, 
    type: 'Selling', 
    summary: 'Listing CS2 cases on Steam Market',
    accounts: [
      { username: 'steam_user123' },
      { username: 'gaben_fan456' },
      { username: 'csgo_lover789' }
    ],
    time: '14:30', 
    formattedTime: '2:30 PM', 
    details: 'Selling 5 Cases, 2 Stickers on Steam Market with preferred pricing using dynamic algorithm based on current market trends',
    config: {
      useSemaphore: true,
      useProxies: true,
      maxRetries: 3,
      timeout: 30
    }
  },
  { 
    id: 2, 
    type: 'Trading', 
    summary: 'Processing pending trade offers',
    accounts: [
      { username: 'sender1', type: 'sender' },
      { username: 'sender2', type: 'sender' },
      { username: 'sender3', type: 'sender' },
      { username: 'trader_pro456', type: 'receiver' }
    ],
    time: '15:45', 
    formattedTime: '3:45 PM', 
    details: 'Accepting trade offers for 3 Skins',
    config: {
      useSemaphore: true,
      useProxies: false,
      maxRetries: 5,
      timeout: 45
    }
  },
  { 
    id: 3, 
    type: 'Farm Job', 
    summary: 'Auto-farming operation passes',
    accounts: [
      { username: 'cs2_player789' },
      { username: 'valve_player234' }
    ],
    time: '16:15', 
    formattedTime: '4:15 PM', 
    details: 'Armoury Pass Farming - Operation Riptide',
    config: {
      useSemaphore: false,
      useProxies: true,
      maxRetries: 2,
      timeout: 60
    }
  },
  { 
    id: 4, 
    type: 'Balance Add', 
    summary: 'Adding funds to wallet',
    accounts: [
      { username: 'case_opener567' }
    ],
    time: '17:00', 
    formattedTime: '5:00 PM', 
    details: 'Adding wallet funds via PayPal for upcoming case purchases',
    config: {
      useSemaphore: false,
      useProxies: false,
      maxRetries: 1,
      timeout: 20
    }
  },
];

// Mock notifications
const initialNotifications: Notification[] = [
  { id: 1, title: 'Low Balance Warning', message: 'Account cs2_player789 is running low on funds', time: '12:19', type: 'warning', read: false },
  { id: 2, title: 'Trade Completed', message: 'Trade offer with user XYZ was completed successfully', time: '11:45', type: 'success', read: false },
  { id: 3, title: 'System Update', message: 'Farmageddon updated to version 1.2.3', time: '09:30', type: 'info', read: true },
  { id: 4, title: 'Error Detected', message: 'Failed to connect to Steam API. Retrying...', time: '08:15', type: 'error', read: true },
];

// Helper function to determine the log level icon
const getLogLevelIcon = (level: string) => {
  switch (level) {
    case 'INFO':
      return <Info className="h-4 w-4 text-blue-500" />;
    case 'WARNING':
      return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    case 'ERROR':
      return <AlertOctagon className="h-4 w-4 text-red-500" />;
    case 'DEBUG':
      return <Server className="h-4 w-4 text-gray-500" />;
    default:
      return <Info className="h-4 w-4 text-blue-500" />;
  }
};

export default function Dashboard() {
  const [expandedLog, setExpandedLog] = useState<number | null>(null);
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);
  const [expandedActivity, setExpandedActivity] = useState<number | null>(null);
  const [expandedAccounts, setExpandedAccounts] = useState<number | null>(null);
  
  // State for notifications with PageHeader component
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );

  // Handle marking all notifications as read
  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  return (
    <DashboardLayout>
      <PageHeader 
        title="Overview" 
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />

      {/* Main grid layout: Bot activities on left, Orchestrator Logs on right */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Bot Activities - Left Column */}
        <Card className="dark:bg-gray-800">
          <CardHeader>
            <CardTitle>Bot Activities</CardTitle>
            <CardDescription>Current bot operations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {botActivities.map((activity) => (
              <div 
                key={activity.id} 
                className="p-3 border rounded-md bg-white dark:bg-slate-900 transition-colors"
              >
                {/* Activity header - always visible */}
                <div 
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => {
                    setExpandedActivity(expandedActivity === activity.id ? null : activity.id);
                    setExpandedAccounts(null); // Close accounts list when clicking to expand activity
                  }}
                >
                  <div className="flex items-center gap-2">
                    {/* Modified icon container with matching background color */}
                    <div className="h-8 w-8 rounded-full bg-white dark:bg-slate-900 flex items-center justify-center">
                      {/* Apply text color directly to the icon */}
                      <span className="text-slate-600 dark:text-slate-400">
                        {activity.icon}
                      </span>
                    </div>
                    
                    <div className="relative inline-block">
                      <Button 
                        variant="ghost" 
                        className="h-auto px-3 py-1.5 font-medium rounded-md hover:bg-slate-50 dark:hover:bg-slate-800"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (expandedAccounts === activity.id) {
                            setExpandedAccounts(null);
                          } else {
                            setExpandedAccounts(activity.id);
                            setExpandedActivity(null); // Close activity details when showing accounts
                          }
                        }}
                      >
                        <span className="whitespace-nowrap">{activity.count} {activity.activity}</span>
                      </Button>
                    </div>
                  </div>
                  
                  <ChevronDown 
                    className={`h-4 w-4 transition-transform ${expandedActivity === activity.id ? 'rotate-180' : ''}`}
                  />
                </div>
                
                {/* Accounts popover - only shows when accounts button is clicked */}
                {expandedAccounts === activity.id && (
                  <div className="mt-2 border-t pt-2">
                    <div className="p-2 font-medium text-sm mb-1">
                      {activity.activity} Accounts
                    </div>
                    {/* Replaced ScrollArea with div with explicit overflow-y: auto */}
                    <div className="max-h-[150px] min-h-[40px] overflow-y-auto">
                      {activity.accounts.map((account, idx) => (
                        <div key={idx} className="p-2 text-sm border-b last:border-0 hover:bg-slate-100 dark:hover:bg-slate-800">
                          {account}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Progress bars - only shows when activity is expanded */}
                {expandedActivity === activity.id && !expandedAccounts && (
                  <div className="mt-2 border-t pt-2">
                    {/* Replaced ScrollArea with div with explicit overflow-y: auto */}
                    <div className="max-h-[180px] min-h-[40px] overflow-y-auto">
                      {activity.activity.includes('Selling') || activity.activity.includes('Trades') ? (
                        // Combined progress bar for selling/trading activities
                        <div className="p-2">
                          <div className="text-xs mb-2">Combined progress for all {activity.accounts.length} bots:</div>
                          {activity.bots?.map((bot, idx) => (
                            <div key={idx} className="mb-4">
                              <div className="flex justify-between items-center text-xs mb-1">
                                <span>Started: {bot.startTime}</span>
                                <span>Est. remaining: {bot.estimatedTimeLeft}</span>
                              </div>
                              <Progress value={bot.progress} className="h-1.5" />
                            </div>
                          ))}
                        </div>
                      ) : (
                        // Individual progress bars for farming/other activities
                        <div className="p-2">
                          {activity.bots?.map((bot, idx) => (
                            <div key={idx} className="mb-4">
                              <div className="font-medium text-xs mb-1">{bot.name}</div>
                              <div className="flex justify-between items-center text-xs mb-1">
                                <span>Started: {bot.startTime}</span>
                                <span>Est. remaining: {bot.estimatedTimeLeft}</span>
                              </div>
                              <Progress value={bot.progress} className="h-1.5" />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
        
        {/* Orchestrator Logs - Right Column (spans 2 columns) */}
        <Card className="md:col-span-2 dark:bg-gray-800">
          <CardHeader>
            <CardTitle>Orchestrator Logs</CardTitle>
            <CardDescription>Currently running modules</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {runningModules.map((module) => (
                <Collapsible 
                  key={module.id}
                  open={expandedLog === module.id}
                  onOpenChange={() => setExpandedLog(expandedLog === module.id ? null : module.id)}
                >
                  <div 
                    className={`border rounded-md transition-colors
                      ${module.status === 'running' ? 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800' : 
                        module.status === 'error' ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800' : 
                        'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800'}`}
                  >
                    <CollapsibleTrigger asChild>
                      <div className="p-4 cursor-pointer">
                        {/* Module name with accounts */}
                        <div className="flex flex-wrap items-center justify-between mb-3">
                          <div className="font-medium text-base">{module.name}</div>
                          <div className="flex items-center">
                            <Popover>
                              <PopoverTrigger asChild>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-7 text-xs"
                                  onClick={(e) => e.stopPropagation()} // Stop event propagation here
                                >
                                  {module.accounts.length > 1 ? 
                                    `${module.accounts.length} Accounts` : 
                                    module.accounts[0].username}
                                  <ChevronDown className="ml-1 h-3 w-3" />
                                </Button>
                              </PopoverTrigger>
                              {module.accounts.length > 0 && (
                                <PopoverContent className="w-60 p-0" align="end">
                                  <div className="p-2 font-medium text-sm border-b">
                                    Account List
                                  </div>
                                  <ScrollArea className="h-[200px]">
                                    {module.accounts.map((account, idx) => (
                                      <div key={idx} className="p-2 text-sm border-b last:border-0 hover:bg-slate-100 dark:hover:bg-slate-800">
                                        {account.username}
                                        {account.status && (
                                          <span className="text-xs text-muted-foreground ml-2">({account.status})</span>
                                        )}
                                      </div>
                                    ))}
                                  </ScrollArea>
                                </PopoverContent>
                              )}
                            </Popover>
                          </div>
                        </div>
                        
                        {/* Log message with level and time */}
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center">
                            {getLogLevelIcon(module.logLevel)}
                            <div className="text-sm ml-2">{module.latestLog}</div>
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">{module.timeAgo}</div>
                        </div>
                        
                        {/* Progress bar at bottom with times at each end */}
                        <div className="flex items-center gap-2">
                          <Progress value={module.progress} className="h-1.5" />
                        </div>
                        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
                          <div>Started: {module.startTime}</div>
                          <div>Est. remaining: {module.estimatedTimeLeft}</div>
                        </div>
                      </div>
                    </CollapsibleTrigger>
                    
                    <CollapsibleContent>
                      <div className="border-t p-4 bg-slate-800 text-slate-100 rounded-b-md font-mono text-sm">
                        <ScrollArea className="h-[200px]">
                          <div className="space-y-1">
                            {module.logs.map((log, index) => (
                              <div key={index} className="flex gap-2">
                                <span className={`
                                  ${log.level === 'INFO' ? 'text-blue-400' : 
                                    log.level === 'WARNING' ? 'text-amber-400' : 
                                    log.level === 'ERROR' ? 'text-red-400' : 
                                    'text-gray-400'}
                                `}>
                                  {log.level}
                                </span>
                                <span className="text-slate-400">|</span>
                                <span className="text-slate-400">{log.time}</span>
                                <span className="text-slate-400">|</span>
                                <span>{log.message}</span>
                              </div>
                            ))}
                          </div>
                        </ScrollArea>
                      </div>
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Scheduled Events */}
      <div className="mb-6">
        {/* Orchestrator Scheduled Events */}
        <Card className="mb-6 dark:bg-gray-800">
          <CardHeader>
            <CardTitle>Orchestrator Scheduled Events</CardTitle>
            <CardDescription>Upcoming operations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {scheduledEvents.map((event) => (
                <Collapsible 
                  key={event.id}
                  open={expandedEvent === event.id}
                  onOpenChange={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
                >
                  <CollapsibleTrigger asChild>
                    <div className={`p-3 border rounded-md ${expandedEvent === event.id ? 'rounded-b-none border-b-0' : ''} bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors flex items-center justify-between`}>
                      <div className="flex items-center gap-3 flex-grow">
                        <Badge variant={
                          event.type === 'Selling' ? 'default' :
                          event.type === 'Trading' ? 'secondary' :
                          event.type === 'Farm Job' ? 'outline' : 'destructive'
                        }>
                          {event.type}
                        </Badge>
                        
                        <span className="font-medium">
                          {event.summary}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 flex-shrink-0">
                        <span className="text-sm font-semibold">
                          {event.formattedTime}
                        </span>
                        <ChevronDown className={`h-4 w-4 transition-transform ${expandedEvent === event.id ? 'rotate-180' : ''}`} />
                      </div>
                    </div>
                  </CollapsibleTrigger>
                  
                  <CollapsibleContent>
                    <div className="p-4 border border-t-0 rounded-t-none rounded-b-md bg-white dark:bg-slate-900">
                      {/* Top row with accounts and scheduled time */}
                      <div className="flex flex-wrap md:flex-nowrap justify-between mb-4 gap-4">
                        <div className="w-full md:w-auto">
                          {event.type === 'Trading' ? (
                            <div className="flex flex-row items-center space-x-4">
                              <div>
                                <h4 className="text-sm font-semibold mb-2">Sending Accounts:</h4>
                                <Popover>
                                  <PopoverTrigger asChild>
                                    <Button variant="outline" size="sm" className="h-8">
                                      {event.accounts.filter(acc => acc.type === 'sender').length} Sending Accounts
                                      <ChevronDown className="ml-1 h-3 w-3" />
                                    </Button>
                                  </PopoverTrigger>
                                  <PopoverContent className="w-60 p-0">
                                    <div className="p-2 font-medium text-sm border-b">
                                      Sending Accounts
                                    </div>
                                    <ScrollArea className="h-[150px]">
                                      {event.accounts
                                        .filter(acc => acc.type === 'sender')
                                        .map((account, idx) => (
                                          <div key={idx} className="p-2 text-sm border-b last:border-0 hover:bg-slate-100 dark:hover:bg-slate-800">
                                            {account.username}
                                          </div>
                                      ))}
                                    </ScrollArea>
                                  </PopoverContent>
                                </Popover>
                              </div>
                              
                              <div className="flex items-center">
                                <ArrowRight className="h-5 w-5" />
                              </div>
                              
                              <div>
                                <h4 className="text-sm font-semibold mb-2">Receiving Account:</h4>
                                <div className="text-sm p-2 bg-white dark:bg-slate-900 rounded border">
                                  {event.accounts.find(acc => acc.type === 'receiver')?.username}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div>
                              <h4 className="text-sm font-semibold mb-2">Accounts:</h4>
                              <Popover>
                                <PopoverTrigger asChild>
                                  <Button variant="outline" size="sm" className="h-8">
                                    {event.accounts.length} Accounts
                                    <ChevronDown className="ml-1 h-3 w-3" />
                                  </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-60 p-0">
                                  <div className="p-2 font-medium text-sm border-b">
                                    Account List
                                  </div>
                                  <ScrollArea className="h-[150px]">
                                    {event.accounts.map((account, idx) => (
                                      <div key={idx} className="p-2 text-sm border-b last:border-0 hover:bg-slate-100 dark:hover:bg-slate-800">
                                        {account.username}
                                      </div>
                                    ))}
                                  </ScrollArea>
                                </PopoverContent>
                              </Popover>
                            </div>
                          )}
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Scheduled Time:</h4>
                          <div className="text-sm p-2 bg-white dark:bg-slate-900 rounded border">
                            {event.formattedTime}
                          </div>
                        </div>
                      </div>
                      
                      {/* Bottom row with details and config */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Details:</h4>
                          <div className="text-sm p-3 bg-white dark:bg-slate-900 rounded border min-h-[80px] overflow-auto">
                            {event.details || 'No additional details available'}
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Config:</h4>
                          <div className="bg-white dark:bg-slate-900 rounded border p-3">
                            <div className="space-y-3">
                              <div className="flex items-center justify-between">
                                <label className="text-sm">Use Semaphore</label>
                                <Switch checked={event.config?.useSemaphore} />
                              </div>
                              <div className="flex items-center justify-between">
                                <label className="text-sm">Use Proxies</label>
                                <Switch checked={event.config?.useProxies} />
                              </div>
                              <div className="flex items-center justify-between">
                                <label className="text-sm">Max Retries</label>
                                <div className="bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded text-sm">
                                  {event.config?.maxRetries}
                                </div>
                              </div>
                              <div className="flex items-center justify-between">
                                <label className="text-sm">Timeout (seconds)</label>
                                <div className="bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded text-sm">
                                  {event.config?.timeout}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="mt-4 flex justify-end space-x-2">
                        <Button size="sm" variant="outline">Edit</Button>
                        <Button size="sm" variant="destructive">Cancel</Button>
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
