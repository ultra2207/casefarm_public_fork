"use client";

import React, { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ExternalLink, Search } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Define types
interface Account {
  id: string;
  name: string;
  hasPrime: boolean;
  passesCount: number;
  walletBalance: number;
  currency: string;
}

interface Notification {
  id: number | string;
  title: string;
  message: string;
  time: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
}

// Constants
const PRIME_PRICE = 229999;
const PASS_PRICE = 244999;
const MAX_PASSES = 5;
const SAM_URL = "https://www.google.com"; // Placeholder for SAM

// Mock data for accounts with realistic usernames
const accountsData: Account[] = [
  { id: '1', name: 'alice', hasPrime: false, passesCount: 0, walletBalance: 1500000, currency: 'IDR' },
  { id: '2', name: 'bob', hasPrime: true, passesCount: 5, walletBalance: 3000000, currency: 'IDR' },
  { id: '3', name: 'charlie', hasPrime: true, passesCount: 3, walletBalance: 1000000, currency: 'IDR' },
  { id: '4', name: 'dave', hasPrime: false, passesCount: 0, walletBalance: 500000, currency: 'IDR' },
  { id: '5', name: 'eve', hasPrime: true, passesCount: 2, walletBalance: 2000000, currency: 'IDR' },
];

const BuyPrimePage: React.FC = () => {
  // State
  const [accounts, setAccounts] = useState<Account[]>(accountsData);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredAccounts, setFilteredAccounts] = useState<Account[]>([]);
  const [displayedAccounts, setDisplayedAccounts] = useState<{account: Account, isEligible: boolean}[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<Account[]>([]);
  const [targetPasses, setTargetPasses] = useState<number>(5); // Default target passes
  const [showAllAccounts, setShowAllAccounts] = useState<boolean>(false); // New state for showing all accounts

  // Format currency
  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Calculate what's needed to reach target passes and the cost
  const calculatePurchaseInfo = (account: Account) => {
    // If account already has Prime and passesCount >= targetPasses, return null (not eligible)
    if (account.hasPrime && account.passesCount >= targetPasses) return null;

    let passesToBuy = targetPasses - account.passesCount;
    if (passesToBuy <= 0) return null; // Already has enough passes

    let needsPrime = !account.hasPrime;
    let totalCost = 0;

    if (needsPrime) {
      totalCost = PRIME_PRICE + (passesToBuy * PASS_PRICE);
    } else {
      totalCost = passesToBuy * PASS_PRICE;
    }

    // Check if account has enough balance
    if (account.walletBalance < totalCost) return null;

    return {
      passesToBuy,
      totalCost,
      needsPrime
    };
  };

  // Calculate cost for ineligible accounts
  const calculateRequiredCost = (account: Account) => {
    let passesToBuy = targetPasses - account.passesCount;
    let needsPrime = !account.hasPrime;
    
    return needsPrime ? 
      PRIME_PRICE + (passesToBuy * PASS_PRICE) : 
      passesToBuy * PASS_PRICE;
  };

  // Check if an account needs upgrade but doesn't have enough balance
  const isIneligibleAccount = (account: Account) => {
    // If already has prime + target passes, it's not what we're looking for
    if (account.hasPrime && account.passesCount >= targetPasses) return false;
    
    // Calculate needed upgrades
    let totalCost = calculateRequiredCost(account);
    
    // If not enough balance, it's an ineligible account
    return account.walletBalance < totalCost;
  };

  // Filter and prepare accounts for display
  useEffect(() => {
    const searchFiltered = accounts.filter(account => 
      account.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    // Process accounts for display
    const processed = searchFiltered.map(account => {
      // Skip accounts that already have Prime and enough passes
      if (account.hasPrime && account.passesCount >= targetPasses) {
        return null;
      }
      
      // Check if account has enough balance for needed upgrades
      const purchaseInfo = calculatePurchaseInfo(account);
      const isEligible = purchaseInfo !== null;
      
      // For the main filtered list (eligible accounts only)
      if (isEligible) {
        return { account, isEligible: true };
      } else if (showAllAccounts && isIneligibleAccount(account)) {
        // Include ineligible accounts if showAllAccounts is true
        return { account, isEligible: false };
      }
      
      return null;
    }).filter(item => item !== null) as {account: Account, isEligible: boolean}[];
    
    setDisplayedAccounts(processed);
    
    // Maintain the original filtered accounts list for selection functionality
    setFilteredAccounts(searchFiltered.filter(account => calculatePurchaseInfo(account) !== null));
  }, [searchTerm, accounts, targetPasses, showAllAccounts]);

  // Toggle account selection
  const toggleAccountSelection = (account: Account, isEligible: boolean) => {
    if (!isEligible) return; // Prevent selection of ineligible accounts
    
    if (selectedAccounts.find(a => a.id === account.id)) {
      setSelectedAccounts(selectedAccounts.filter(a => a.id !== account.id));
    } else {
      setSelectedAccounts([...selectedAccounts, account]);
    }
  };

  // Generate action description for each account
  const getActionDescription = (account: Account, isEligible: boolean) => {
    if (!isEligible) {
      const totalCost = calculateRequiredCost(account);
      const shortfall = totalCost - account.walletBalance;
      return `Insufficient balance (needs ${formatCurrency(shortfall, account.currency)} more)`;
    }
    
    const purchaseInfo = calculatePurchaseInfo(account);
    if (!purchaseInfo) return "";

    if (purchaseInfo.needsPrime) {
      return purchaseInfo.passesToBuy > 0 
        ? `Get Prime + ${purchaseInfo.passesToBuy} more pass${purchaseInfo.passesToBuy !== 1 ? 'es' : ''} to reach ${targetPasses} total` 
        : `Get Prime only to reach requirements`;
    } else {
      return `Get ${purchaseInfo.passesToBuy} more pass${purchaseInfo.passesToBuy !== 1 ? 'es' : ''} to reach ${targetPasses} total`;
    }
  };

  // Handle DB update
  const handleUpdateDB = () => {
    alert(`Updating ${selectedAccounts.length} accounts to reach Prime + ${targetPasses} passes.`);
    // In a real implementation, this would call an API endpoint
    setSelectedAccounts([]);
  };

  // Sample notifications for the PageHeader
  const [notifications, setNotifications] = useState<Notification[]>([
    { id: 1, title: 'Update Available', message: 'New version of account manager', time: '10:15', type: 'info', read: false },
    { id: 2, title: 'Balance Alert', message: 'Account funds low', time: '09:30', type: 'warning', read: false }
  ]);
  const [unreadNotifications, setUnreadNotifications] = useState(2);

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
        title="Buy Prime & Passes"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      <div className="container mx-auto py-8 px-4">
        <Card className="max-w-4xl mx-auto">
          <CardHeader>
            <CardTitle className="text-2xl">Reach Prime + Target Passes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Prime and Passes Information */}
            <div className="space-y-2">
              <Label>Price Information:</Label>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">
                  Prime: {formatCurrency(PRIME_PRICE, 'IDR')}
                </Badge>
                <Badge variant="outline">
                  Pass: {formatCurrency(PASS_PRICE, 'IDR')}
                </Badge>
              </div>
              <div className="space-y-2">
                <Label htmlFor="targetPasses">Total Passes to Reach (not add):</Label>
                <Select 
                  value={targetPasses.toString()} 
                  onValueChange={(value) => setTargetPasses(Number(value))}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Select target passes" />
                  </SelectTrigger>
                  <SelectContent>
                    {[...Array(MAX_PASSES)].map((_, i) => (
                      <SelectItem key={i + 1} value={(i + 1).toString()}>
                        {i + 1} {i === 0 ? 'Pass' : 'Passes'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-sm text-muted-foreground">
                Goal: All accounts should have Prime and reach exactly {targetPasses} total passes (not adding {targetPasses} passes)
              </p>
            </div>

            {/* Search */}
            <div className="space-y-2">
              <Label htmlFor="search">Search Accounts:</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  type="text"
                  placeholder="Search by username..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>

            {/* Show All Accounts Option */}
            <div className="flex items-center space-x-2">
              <Checkbox 
                id="showAllAccounts" 
                checked={showAllAccounts} 
                onCheckedChange={() => setShowAllAccounts(!showAllAccounts)} 
              />
              <Label htmlFor="showAllAccounts" className="text-sm font-normal">
                Show accounts with insufficient balance (greyed out and unselectable)
              </Label>
            </div>

            {/* Account list */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <Label>Accounts ({displayedAccounts.length})</Label>
                {selectedAccounts.length > 0 && (
                  <Badge variant="secondary">{selectedAccounts.length} selected</Badge>
                )}
              </div>
              <div className="border rounded-md max-h-80 overflow-y-auto">
                {displayedAccounts.length === 0 ? (
                  <div className="p-4 text-center text-muted-foreground">
                    No accounts found
                  </div>
                ) : (
                  <div className="divide-y">
                    {displayedAccounts.map(({account, isEligible}) => {
                      const purchaseInfo = isEligible ? calculatePurchaseInfo(account) : null;
                      const totalCost = isEligible ? 
                        (purchaseInfo?.totalCost || 0) : 
                        calculateRequiredCost(account);

                      return (
                        <div
                          key={account.id}
                          className={`flex items-center justify-between p-3 ${
                            isEligible ? 'hover:bg-muted/50 cursor-pointer' : 'opacity-60 cursor-not-allowed'
                          } ${
                            selectedAccounts.some(a => a.id === account.id) ? 'bg-primary/10' : ''
                          }`}
                          onClick={() => isEligible && toggleAccountSelection(account, isEligible)}
                        >
                          <div className="flex items-center space-x-3">
                            <input
                              type="checkbox"
                              checked={selectedAccounts.some(a => a.id === account.id)}
                              disabled={!isEligible}
                              onChange={() => {}}
                              className="h-4 w-4"
                            />
                            <div>
                              <div className="font-medium">{account.name}</div>
                              <div className="text-sm text-muted-foreground">
                                Balance: {formatCurrency(account.walletBalance, account.currency)} | 
                                Prime: {account.hasPrime ? 'Yes' : 'No'} | 
                                Current Passes: {account.passesCount} of {targetPasses} needed | 
                                Cost: {formatCurrency(totalCost, account.currency)}
                              </div>
                              <div className={`text-xs ${isEligible ? 'text-primary' : 'text-red-500'} font-medium`}>
                                {getActionDescription(account, isEligible)}
                              </div>
                            </div>
                          </div>
                          <Badge>{account.currency}</Badge>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Instructions */}
            {selectedAccounts.length > 0 && (
              <Alert>
                <AlertDescription className="flex flex-col sm:flex-row sm:items-center gap-2">
                  <span>
                    Selected {selectedAccounts.length} account(s). Go to SAM (Standard Accounts Manager) to upgrade these accounts to reach exactly {targetPasses} total passes with Prime.
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(SAM_URL, '_blank')}
                    className="flex items-center gap-1 sm:ml-auto"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Open SAM
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full"
              onClick={handleUpdateDB}
              disabled={selectedAccounts.length === 0}
            >
              Update DB
            </Button>
          </CardFooter>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default BuyPrimePage;
