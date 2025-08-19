"use client";

import React, { useState } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { AlertTriangle, ExternalLink, DollarSign, Check, Clock, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';

// Types
interface MarketItem {
  id: string;
  name: string;
  sellPrice: number;
  buyPrice: number;
  condition: string;
  float: number;
  selected: boolean;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  message: string;
  platform: 'csfloat';
}

interface Notification {
  id: number | string;
  title: string;
  message: string;
  time: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
}

// Mock Data
const mockCSFloatItems: MarketItem[] = [
  { id: '1', name: 'AK-47 | Redline', sellPrice: 45.30, buyPrice: 40.25, condition: 'Field-Tested', float: 0.25, selected: false },
  { id: '2', name: 'AWP | Dragon Lore', sellPrice: 2850.00, buyPrice: 2500.00, condition: 'Battle-Scarred', float: 0.68, selected: false },
  { id: '3', name: 'M4A4 | Howl', sellPrice: 1200.50, buyPrice: 1050.30, condition: 'Minimal Wear', float: 0.12, selected: false },
  { id: '4', name: 'Karambit | Fade', sellPrice: 890.25, buyPrice: 780.50, condition: 'Factory New', float: 0.03, selected: false },
  { id: '5', name: 'Glock-18 | Fade', sellPrice: 320.10, buyPrice: 290.75, condition: 'Factory New', float: 0.02, selected: false },
  { id: '6', name: 'USP-S | Kill Confirmed', sellPrice: 95.60, buyPrice: 85.25, condition: 'Minimal Wear', float: 0.11, selected: false },
  { id: '7', name: 'Desert Eagle | Blaze', sellPrice: 245.30, buyPrice: 215.80, condition: 'Factory New', float: 0.01, selected: false },
  { id: '8', name: 'P250 | Whiteout', sellPrice: 65.40, buyPrice: 58.20, condition: 'Minimal Wear', float: 0.08, selected: false },
  { id: '9', name: 'StatTrak™ M4A1-S | Hyper Beast', sellPrice: 180.75, buyPrice: 165.30, condition: 'Field-Tested', float: 0.22, selected: false },
];

const mockLogs: LogEntry[] = [
  {
    id: '1',
    timestamp: '12:15 PM',
    level: 'INFO',
    message: 'Starting CSFloat operations for cs2_player789',
    platform: 'csfloat'
  },
  {
    id: '2',
    timestamp: '12:16 PM',
    level: 'INFO',
    message: 'Checking account balance',
    platform: 'csfloat'
  },
  {
    id: '3',
    timestamp: '12:17 PM',
    level: 'INFO',
    message: 'Current balance: $1,250.75',
    platform: 'csfloat'
  },
  {
    id: '4',
    timestamp: '12:18 PM',
    level: 'SUCCESS',
    message: 'Successfully connected to CSFloat API',
    platform: 'csfloat'
  },
  {
    id: '5',
    timestamp: '12:19 PM',
    level: 'INFO',
    message: 'Retrieving item listings',
    platform: 'csfloat'
  },
];

const initialNotifications: Notification[] = [
  { 
    id: 1, 
    title: 'CSFloat Connection', 
    message: 'Successfully connected to CSFloat API',
    time: '22:45', 
    type: 'success', 
    read: false 
  },
  { 
    id: 2, 
    title: 'Item Listed', 
    message: 'AK-47 Redline listed on CSFloat',
    time: '22:44', 
    type: 'info', 
    read: false 
  },
  { 
    id: 3, 
    title: 'Trade Completed', 
    message: 'AWP Dragon Lore trade offer accepted',
    time: '22:43', 
    type: 'success', 
    read: true 
  }
];

const buyOrderSteps = [
  { id: 1, label: 'Purchase Intention', description: 'Order received' },
  { id: 2, label: 'Sending Trades', description: 'Initiating trade offers' },
  { id: 3, label: 'Trades Confirmed', description: 'Trade offers accepted' },
  { id: 4, label: 'Money Debited', description: 'Payment processed' },
];

export default function CSFloatPage() {
  // Notification state
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );

  // Item selection state
  const [items, setItems] = useState<MarketItem[]>(mockCSFloatItems);
  const [orderType, setOrderType] = useState<'buy' | 'sell'>('sell');
  const [progress, setProgress] = useState<number>(0);
  const [isSelling, setIsSelling] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Logs state
  const [showLogs, setShowLogs] = useState(false);
  
  // Calculate totals
  const totalSell = items.reduce((acc, item) => acc + (item.selected ? item.sellPrice : 0), 0);
  const totalBuy = items.reduce((acc, item) => acc + (item.selected ? item.buyPrice : 0), 0);

  // Handle notifications
  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  // Withdrawal handler
  const handleWithdraw = () => {
    window.open('https://csfloat.com/profile/withdraw', '_blank');
  };

  // Item selection handlers
  const toggleItemSelection = (id: string) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { ...item, selected: !item.selected } : item
    ));
  };

  const selectAllItems = (select: boolean) => {
    setItems(prev => prev.map(item => ({ ...item, selected: select })));
  };

  // Sell handler
  const handleSell = () => {
    setIsSelling(true);
    setCurrentStep(1);
    
    if (orderType === 'sell') {
      // Simulate sell order progress
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setIsSelling(false);
            return 100;
          }
          return prev + 10;
        });
      }, 500);
    } else {
      // Simulate buy order steps
      let step = 1;
      const interval = setInterval(() => {
        step++;
        setCurrentStep(step);
        if (step >= buyOrderSteps.length) {
          clearInterval(interval);
          setIsSelling(false);
        }
      }, 1500);
    }
  };

  // Helper functions for logs
  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'ERROR': return 'text-red-400';
      case 'WARNING': return 'text-yellow-400';
      case 'SUCCESS': return 'text-green-400';
      default: return 'text-gray-400';
    }
  };

  // Order Progress Bar Component
  const OrderProgressBar = ({ currentStep }: { currentStep: number }) => {
    const progressPercentage = (currentStep / buyOrderSteps.length) * 100;

    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Highest Buy Order Progress</span>
            <span>Step {currentStep}/{buyOrderSteps.length}</span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
        </div>

        <div className="space-y-3">
          {buyOrderSteps.map((step, index) => (
            <div key={step.id} className="flex items-center gap-3">
              <div className={`
                flex items-center justify-center w-8 h-8 rounded-full border-2 
                ${currentStep > step.id 
                  ? 'bg-green-600 border-green-600 text-white' 
                  : currentStep === step.id 
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-gray-700 border-gray-600 text-gray-400'
                }
              `}>
                {currentStep > step.id ? (
                  <Check className="h-4 w-4" />
                ) : currentStep === step.id ? (
                  <Clock className="h-4 w-4" />
                ) : (
                  <span className="text-xs font-medium">{step.id}</span>
                )}
              </div>
              <div className="flex-1">
                <div className={`font-medium ${
                  currentStep >= step.id ? 'text-gray-100' : 'text-gray-500'
                }`}>
                  {step.label}
                </div>
                <div className="text-sm text-gray-400">{step.description}</div>
              </div>
              {index < buyOrderSteps.length - 1 && (
                <ArrowRight className="h-4 w-4 text-gray-500" />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="CSFloat"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />

      <div className="space-y-6">
        {/* Disclaimer Section */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm text-gray-300">
                This CSFloat integration is not yet implemented. Visit the official site:
                <a 
                  href="https://csfloat.com/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 ml-1 text-blue-400 hover:text-blue-300"
                >
                  CSFloat <ExternalLink className="h-3 w-3" />
                </a>
              </p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex justify-between items-center">
              <CardTitle>CSFloat Items</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Highest Buy Order</span>
                <Switch 
                  checked={orderType === 'sell'}
                  onCheckedChange={(checked) => setOrderType(checked ? 'sell' : 'buy')}
                />
                <span className="text-sm font-medium">Lowest Sell Order</span>
              </div>
            </div>
            
            {/* Balance and Totals */}
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 mt-3">
              <div className="grid grid-cols-3 gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-green-400" />
                    <div>
                      <p className="text-xs text-gray-400">Current Balance</p>
                      <p className="font-semibold text-gray-100">$1,250.75</p>
                    </div>
                  </div>
                  <Button 
                    onClick={handleWithdraw}
                    size="sm"
                    variant="outline"
                    className="gap-1 ml-2"
                  >
                    Withdraw <ExternalLink className="h-3 w-3" />
                  </Button>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Total Lowest Sell Order Value</p>
                  <p className="font-semibold text-green-400">${totalSell.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Total Highest Buy Order Value</p>
                  <p className="font-semibold text-blue-400">${totalBuy.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            <div className="space-y-4">
              {/* Item Selection Controls */}
              <div className="flex justify-between items-center">
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => selectAllItems(true)}
                >
                  Select All
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => selectAllItems(false)}
                >
                  Clear Selection
                </Button>
              </div>

              {/* Items Grid */}
              <div className="grid grid-cols-3 gap-4">
                {items.map((item) => (
                  <Card key={item.id} className="p-3">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        checked={item.selected}
                        onCheckedChange={() => toggleItemSelection(item.id)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{item.name}</div>
                        <div className="flex gap-2 items-center mt-1">
                          <Badge variant="secondary" className="text-xs">
                            {item.condition}
                          </Badge>
                          <span className="text-xs text-gray-400">Float: {item.float}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">
                          ${orderType === 'sell' ? item.sellPrice.toFixed(2) : item.buyPrice.toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-400">
                          {orderType === 'sell' ? 'Lowest Sell' : 'Highest Buy'}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
              
              {/* Action Button */}
              <div className="pt-3">
                <Button 
                  className="w-full" 
                  disabled={!items.some(item => item.selected) || isSelling}
                  onClick={handleSell}
                >
                  {isSelling ? 'Processing...' : orderType === 'sell' ? 'Place Lowest Sell Orders' : 'Place Highest Buy Orders'}
                </Button>
              </div>
              
              {/* Progress Display */}
              {isSelling && (
                <div className="mt-4">
                  {orderType === 'sell' ? (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Processing Lowest Sell Orders</span>
                        <span>{Math.round(progress / 10)}/{items.filter(i => i.selected).length} items</span>
                      </div>
                      <Progress value={progress} className="h-2" />
                    </div>
                  ) : (
                    <OrderProgressBar currentStep={currentStep} />
                  )}
                </div>
              )}
              
              {/* Logs Section */}
              <div className="mt-4 pt-4 border-t border-gray-700">
                <Button 
                  onClick={() => setShowLogs(!showLogs)}
                  variant="ghost"
                  className="w-full flex justify-between items-center"
                >
                  <span>View Logs</span>
                  {showLogs ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </Button>
                
                {showLogs && (
                  <div className="mt-3 bg-gray-900 border border-gray-700 rounded-md p-3 font-mono text-xs overflow-auto max-h-60">
                    {mockLogs.map((log) => (
                      <div key={log.id} className="flex gap-2">
                        <span className={getLevelColor(log.level)}>{log.level}</span>
                        <span className="text-gray-400">|</span>
                        <span className="text-gray-400">{log.timestamp}</span>
                        <span className="text-gray-400">|</span>
                        <span className="text-gray-200">{log.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
