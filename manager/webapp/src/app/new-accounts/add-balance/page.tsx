"use client";

import React, { useState, useEffect } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Label } from "@/components/ui/label";
import { ExternalLink, RefreshCw, Key, Users, Search, X, Check } from "lucide-react";
import Image from "next/image";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Define proper TypeScript interfaces
interface ConversionRates {
  [key: string]: number;
}

interface Account {
  id: number;
  username: string;
  value: string;
  balance: number;
  avatar: string;
}

interface Notification {
  id: number;
  title: string;
  message: string;
  time: string;
  type: 'success' | 'info' | 'warning' | 'error';
  read: boolean;
}

// Sample notifications
const initialNotifications: Notification[] = [
  { id: 1, title: 'Balance Update', message: 'Your last balance update was successful', time: '12:19', type: 'success', read: false },
  { id: 2, title: 'Crypto Payment', message: 'Pending crypto payment detected', time: '11:45', type: 'info', read: false },
];

// Mock accounts data for selection
const availableAccounts: Account[] = [
  { id: 1, username: "GameMaster2025", value: "gamemaster2025", balance: 750000, avatar: "/avatar-placeholder.png" },
  { id: 2, username: "CS_Player42", value: "csplayer42", balance: 250000, avatar: "/avatar-placeholder.png" },
  { id: 3, username: "BombPlanter99", value: "bombplanter99", balance: 125000, avatar: "/avatar-placeholder.png" },
  { id: 4, username: "SniperElite", value: "sniperelite", balance: 500000, avatar: "/avatar-placeholder.png" },
  { id: 5, username: "RushBCyka", value: "rushbcyka", balance: 100000, avatar: "/avatar-placeholder.png" },
  { id: 6, username: "HeadshotKing", value: "headshotking", balance: 300000, avatar: "/avatar-placeholder.png" },
  { id: 7, username: "KnifeCollector", value: "knifecollector", balance: 1200000, avatar: "/avatar-placeholder.png" },
  { id: 8, username: "StratCaller", value: "stratcaller", balance: 180000, avatar: "/avatar-placeholder.png" },
];

export default function AddBalancePage() {
  // State for notifications
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState<number>(
    initialNotifications.filter(notification => !notification.read).length
  );

  // State for account selection
  const [selectedAccounts, setSelectedAccounts] = useState<Account[]>([availableAccounts[0]]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  
  // State for 2FA code generation
  const [selected2FAAccount, setSelected2FAAccount] = useState<number | null>(selectedAccounts[0]?.id || null);
  const [loading2FA, setLoading2FA] = useState<boolean>(false);
  const [twoFACode, setTwoFACode] = useState<string | null>(null);
  
  // State for balance
  const [inputAmount, setInputAmount] = useState<string>("");
  const [selectedCurrency, setSelectedCurrency] = useState<string>("IDR");
  const [usdEquivalent, setUsdEquivalent] = useState<number>(0);
  const [processingPayment, setProcessingPayment] = useState<boolean>(false);
  const [progressValue, setProgressValue] = useState<number>(0);
  const [conversionRates, setConversionRates] = useState<ConversionRates>({});
  const [isLoadingRates, setIsLoadingRates] = useState<boolean>(true);

  // Update selected2FAAccount when selectedAccounts changes
  useEffect(() => {
    if (selectedAccounts.length > 0 && !selectedAccounts.some(acc => acc.id === selected2FAAccount)) {
      setSelected2FAAccount(selectedAccounts[0].id);
      // Clear 2FA code when selected account changes
      setTwoFACode(null);
    }
  }, [selectedAccounts, selected2FAAccount]);

  // Fetch conversion rates from API
  useEffect(() => {
    const fetchConversionRates = async () => {
      setIsLoadingRates(true);
      try {
        // Simulating API call for demo purposes
        await new Promise(resolve => setTimeout(resolve, 1000));
        setConversionRates({
          IDR: 0.000064,
          INR: 0.012,
          USD: 1,
        });
      } catch (error) {
        console.error("Failed to fetch conversion rates:", error);
      } finally {
        setIsLoadingRates(false);
      }
    };
    
    fetchConversionRates();
  }, []);

  // Convert input to USD
  useEffect(() => {
    if (!isLoadingRates) {
      const numericAmount = parseFloat(inputAmount) || 0;
      const usdValue = numericAmount * (conversionRates[selectedCurrency] || 0);
      setUsdEquivalent(usdValue);
    }
  }, [inputAmount, selectedCurrency, conversionRates, isLoadingRates]);

  // Handle marking all notifications as read
  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  // Toggle account selection
  const toggleAccountSelection = (account: Account) => {
    if (selectedAccounts.some(acc => acc.id === account.id)) {
      setSelectedAccounts(selectedAccounts.filter(acc => acc.id !== account.id));
    } else {
      setSelectedAccounts([...selectedAccounts, account]);
    }
  };

  // Filter accounts based on search
  const filteredAccounts = availableAccounts.filter(account => 
    account.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Simulate processing payment
  const simulatePaymentProcessing = () => {
    setProcessingPayment(true);
    setProgressValue(0);
    
    const interval = setInterval(() => {
      setProgressValue(prev => {
        const newValue = prev + Math.random() * 10;
        if (newValue >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            setProcessingPayment(false);
            // Here you would update multiple user balances in the database
          }, 500);
          return 100;
        }
        return newValue;
      });
    }, 500);
  };

  // Generate 2FA code for a specific account
  const generate2FACode = () => {
    if (!selected2FAAccount) return;

    setLoading2FA(true);
    setTwoFACode(null);
    
    // Simulate API call to generate 2FA code
    setTimeout(() => {
      const code = Math.floor(100000 + Math.random() * 900000).toString();
      setTwoFACode(code);
      setLoading2FA(false);
    }, 1500);
  };

  // Calculate milestone progress for the first selected account
  const calculateMilestoneProgress = () => {
    if (isLoadingRates || !conversionRates[selectedCurrency] || selectedAccounts.length === 0) {
      return { currencyNeeded: 0, usdNeeded: 0 };
    }
    
    const account = selectedAccounts[0];
    const usdTarget = 5.05;
    const currentUsdBalance = account.balance * conversionRates.IDR;
    const usdNeeded = Math.max(0, usdTarget - currentUsdBalance);
    
    // Convert back to selected currency
    const currencyNeeded = usdNeeded / conversionRates[selectedCurrency];
    
    return {
      currencyNeeded: Math.ceil(currencyNeeded),
      usdNeeded
    };
  };

  // Calculate IDR needed for prime+ 5 passes
  const calculatePrimePassesNeeded = () => {
    if (selectedAccounts.length === 0) return 0;
    
    const account = selectedAccounts[0];
    const primePassesCost = 1454994; // in IDR
    return Math.max(0, primePassesCost - account.balance);
  };

  const milestone = calculateMilestoneProgress();
  const primePassesNeeded = calculatePrimePassesNeeded();

  return (
    <DashboardLayout>
      <PageHeader
        title="Add Balance"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <div className="flex flex-col xl:flex-row gap-6 p-6">
        {/* Main content */}
        <div className="flex-1">
          {/* Account Selection */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Select Accounts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Label htmlFor="account-search">Select accounts to add balance to</Label>
                
                {/* Search input */}
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-gray-400" />
                  </div>
                  <Input
                    id="account-search"
                    type="text"
                    placeholder="Search accounts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
                
                {/* Accounts list */}
                <div className="border rounded-md max-h-64 overflow-y-auto bg-background">
                  {filteredAccounts.length === 0 ? (
                    <div className="p-4 text-center text-muted-foreground">No accounts found</div>
                  ) : (
                    filteredAccounts.map((account) => {
                      const isSelected = selectedAccounts.some(acc => acc.id === account.id);
                      return (
                        <div 
                          key={account.id}
                          className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-muted border-b last:border-b-0 ${
                            isSelected ? 'bg-primary/10' : ''
                          }`}
                          onClick={() => toggleAccountSelection(account)}
                        >
                          <div className={`flex items-center justify-center w-5 h-5 rounded border ${
                            isSelected ? 'bg-primary border-primary text-primary-foreground' : 'border-gray-400'
                          }`}>
                            {isSelected && <Check className="h-3 w-3" />}
                          </div>
                          <div className="flex-1">{account.username}</div>
                          <div className="text-sm text-muted-foreground">
                            {account.balance.toLocaleString('en-US')} IDR
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
                
                {/* Selected accounts summary */}
                {selectedAccounts.length > 0 && (
                  <div className="mt-4">
                    <Label>Selected accounts ({selectedAccounts.length})</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedAccounts.map((account) => (
                        <div key={account.id} className="flex items-center gap-1 bg-muted px-2 py-1 rounded-md">
                          <span className="text-sm">{account.username}</span>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-5 w-5 p-0 ml-1 hover:bg-destructive/10"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleAccountSelection(account);
                            }}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Add Funds</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Amount input */}
                <div>
                  <Label htmlFor="amount">Amount (per account)</Label>
                  <div className="flex gap-4 mt-2">
                    <div className="flex-1">
                      <Input
                        id="amount"
                        type="number"
                        placeholder="Enter amount"
                        value={inputAmount}
                        onChange={(e) => setInputAmount(e.target.value)}
                      />
                    </div>
                    <Select
                      value={selectedCurrency}
                      onValueChange={setSelectedCurrency}
                    >
                      <SelectTrigger className="w-[100px]">
                        <SelectValue placeholder="IDR" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="IDR">IDR</SelectItem>
                        <SelectItem value="INR">INR</SelectItem>
                        <SelectItem value="USD">USD</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    Equivalent to ${usdEquivalent.toFixed(2)} USD per account
                  </p>
                  {selectedAccounts.length > 1 && (
                    <p className="text-sm font-medium mt-2">
                      Total: {(parseFloat(inputAmount) || 0) * selectedAccounts.length} {selectedCurrency} 
                      (${(usdEquivalent * selectedAccounts.length).toFixed(2)} USD)
                    </p>
                  )}
                </div>

                {/* Payment method selection */}
                <div>
                  <Label>Payment Method</Label>
                  <Tabs defaultValue="crypto" className="mt-2">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="crypto">Cryptocurrency</TabsTrigger>
                      <TabsTrigger value="inr">INR (Indian Rupee)</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="crypto" className="space-y-4 mt-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-base">Automated Payment</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm text-muted-foreground mb-4">
                              Process payment automatically through our secure payment gateway.
                            </p>
                            {processingPayment ? (
                              <div className="space-y-2">
                                <Progress value={progressValue} className="w-full" />
                                <p className="text-xs text-center text-muted-foreground">
                                  Processing payment for {selectedAccounts.length} account(s) ({Math.round(progressValue)}%)
                                </p>
                              </div>
                            ) : (
                              <Button onClick={simulatePaymentProcessing} className="w-full">
                                Process Payment
                              </Button>
                            )}
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-base">Manual Payment</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm text-muted-foreground mb-4">
                              Process payment manually through MooGold.
                            </p>
                            <div className="space-y-2">
                              <Button variant="outline" className="w-full" asChild>
                                <a href="https://moogold.com" target="_blank" rel="noopener noreferrer">
                                  Go to MooGold <ExternalLink className="ml-2 h-4 w-4" />
                                </a>
                              </Button>
                              <Button className="w-full">
                                I&apos;ve Completed Payment
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="inr" className="mt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Manual INR Payment</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground mb-4">
                            Please complete your payment manually through MooGold, then return here to update your balance.
                          </p>
                          <div className="space-y-2">
                            <Button variant="outline" className="w-full" asChild>
                              <a href="https://moogold.com" target="_blank" rel="noopener noreferrer">
                                Go to MooGold <ExternalLink className="ml-2 h-4 w-4" />
                              </a>
                            </Button>
                            <Button className="w-full">
                              I&apos;ve Completed Payment
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>
                  </Tabs>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Progress to Milestones */}
          {selectedAccounts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Progress to Milestones (For {selectedAccounts[0].username})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium mb-2">USD $5.05 Milestone</h3>
                    <Progress 
                      value={isLoadingRates ? 0 : (selectedAccounts[0].balance) * conversionRates.IDR / 5.05 * 100} 
                      className="mb-2" 
                    />
                    <p className="text-sm text-muted-foreground">
                      You need {milestone.currencyNeeded.toLocaleString('en-US')} {selectedCurrency} more to reach USD $5.05
                      (${milestone.usdNeeded.toFixed(2)} USD)
                    </p>
                  </div>

                  {selectedCurrency === 'IDR' && (
                    <div>
                      <h3 className="text-sm font-medium mb-2">Prime+ 5 Passes</h3>
                      <Progress 
                        value={((selectedAccounts[0].balance) / 1454994) * 100} 
                        className="mb-2" 
                      />
                      <p className="text-sm text-muted-foreground">
                        You need {primePassesNeeded.toLocaleString('en-US')} IDR more for Prime+ 5 Passes
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right side panel - 2FA and Account summary */}
        <div className="w-full xl:w-80">
          <Card>
            <CardContent className="p-6">
              <div className="flex flex-col items-center">
                {selectedAccounts.length > 0 && (
                  <>
                    {/* Account Summary Section */}
                    <div className="text-center w-full mb-6">
                      <p className="text-sm text-muted-foreground mb-1">Selected Accounts</p>
                      <p className="font-medium">{selectedAccounts.length} account(s)</p>
                      <div className="w-full pt-4 border-t mt-4">
                        <p className="text-sm text-muted-foreground mb-1">Total Balance</p>
                        <p className="font-bold text-xl">
                          {selectedAccounts.reduce((sum, acc) => sum + acc.balance, 0).toLocaleString('en-US')} IDR
                        </p>
                      </div>
                    </div>
                    
                    {/* 2FA Section */}
                    <div className="w-full border-t pt-6">
                      <Label htmlFor="2fa-account-select" className="mb-2 block">
                        Generate 2FA Code for Account
                      </Label>
                      
                      <Select
                        value={selected2FAAccount?.toString() || ""}
                        onValueChange={(value) => {
                          setSelected2FAAccount(Number(value));
                          setTwoFACode(null);
                        }}
                      >
                        <SelectTrigger className="w-full mb-4">
                          <SelectValue placeholder="Select account" />
                        </SelectTrigger>
                        <SelectContent>
                          {selectedAccounts.map(account => (
                            <SelectItem key={account.id} value={account.id.toString()}>
                              {account.username}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      
                      <Button 
                        variant="outline" 
                        className="w-full"
                        onClick={generate2FACode}
                        disabled={loading2FA || !selected2FAAccount}
                      >
                        {loading2FA ? (
                          <span className="flex items-center">
                            <RefreshCw className="animate-spin h-4 w-4 mr-2" />
                            Generating...
                          </span>
                        ) : (
                          <span className="flex items-center">
                            <Key className="h-4 w-4 mr-2" />
                            Generate 2FA Code
                          </span>
                        )}
                      </Button>
                      
                      {twoFACode && selected2FAAccount && (
                        <div className="mt-4 p-4 bg-muted rounded-md border">
                          <p className="text-sm text-muted-foreground mb-2">
                            2FA Code for {selectedAccounts.find(acc => acc.id === selected2FAAccount)?.username}:
                          </p>
                          <p className="font-mono font-bold text-center text-xl">{twoFACode}</p>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
