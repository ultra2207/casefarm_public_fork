"use client";

import { useState, useEffect, useRef } from "react";
import { faker } from '@faker-js/faker';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Check, ChevronsUpDown, Search } from "lucide-react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Sample initial notifications
const initialNotifications = [
  { 
    id: 1, 
    title: 'Trading Started', 
    message: 'Items trading process has begun',
    time: '15:19', 
    type: 'info', 
    read: false 
  },
  { 
    id: 2, 
    title: 'Proxy Connection', 
    message: 'Successfully connected to proxy servers',
    time: '14:45', 
    type: 'success', 
    read: false 
  }
];

// Generate realistic account names using Faker.js
const generateSampleAccounts = () => {
  faker.seed(123); // Set seed for consistent results during development
  return Array.from({ length: 200 }, (_, i) => ({
    id: `account-${i}`,
    name: faker.person.fullName(),
  }));
};

const sampleAccounts = generateSampleAccounts();

export default function ItemsTraderPage() {
  // Notification state
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );

  // Trading configuration state
  const [selectedSenders, setSelectedSenders] = useState<string[]>([]);
  const [selectedReceiver, setSelectedReceiver] = useState<string>("");
  const [useProxies, setUseProxies] = useState(false);
  const [concurrency, setConcurrency] = useState<number | string>(1);
  
  // Progress tracking state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [startTime, setStartTime] = useState<Date | null>(null);
  const [estimatedTimeLeft, setEstimatedTimeLeft] = useState<string | null>(null);
  
  // UI state
  const [senderPopoverOpen, setSenderPopoverOpen] = useState(false);
  const [receiverSearchTerm, setReceiverSearchTerm] = useState("");
  
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // Handle marking all notifications as read
  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  // Handle concurrency input validation
  const handleConcurrencyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (isNaN(value)) {
      setConcurrency("");
    } else {
      setConcurrency(Math.min(1000, Math.max(1, value)));
    }
  };

  // Add log with timestamp
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prevLogs) => [...prevLogs, `[${timestamp}] ${message}`]);
  };

  // Filter accounts based on search term for receiver
  const filteredReceiverAccounts = sampleAccounts.filter(account =>
    account.name.toLowerCase().includes(receiverSearchTerm.toLowerCase())
  );

  // Toggle sender selection
  const toggleSenderAccount = (accountId: string) => {
    setSelectedSenders(current =>
      current.includes(accountId)
        ? current.filter(id => id !== accountId)
        : [...current, accountId]
    );
  };

  // Select all senders
  const selectAllSenders = () => {
    setSelectedSenders(sampleAccounts.map(account => account.id));
  };

  // Clear all sender selections
  const clearAllSenders = () => {
    setSelectedSenders([]);
  };

  // Check if all senders are selected
  const isAllSendersSelected = selectedSenders.length === sampleAccounts.length;
  const isSomeSendersSelected = selectedSenders.length > 0;

  // Simulate the trading process
  const startTrading = () => {
    if (selectedSenders.length === 0 || !selectedReceiver) {
      addLog("Error: Please select sender(s) and a receiver");
      return;
    }

    if (typeof concurrency !== 'number' || concurrency < 1) {
      addLog("Error: Please set a valid concurrency value (1-1000)");
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setStartTime(new Date());
    setLogs([`Started trading process with ${concurrency} concurrent operations`]);

    // Add notification
    const newNotification = {
      id: Date.now(),
      title: 'Trading Process',
      message: `Started trading from ${selectedSenders.length} sender(s) to receiver`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      type: 'info' as const,
      read: false
    };
    
    setNotifications(prev => [newNotification, ...prev]);
    setUnreadNotifications(prev => prev + 1);

    // Simulate progress updates
    const interval = setInterval(() => {
      setProgress((prevProgress) => {
        const newProgress = prevProgress + 1;
        
        // Estimate time left
        if (newProgress > 0 && startTime) {
          const elapsedMs = new Date().getTime() - startTime.getTime();
          const estimatedTotalMs = (elapsedMs / newProgress) * 100;
          const remainingMs = estimatedTotalMs - elapsedMs;
          
          // Format as mm:ss
          const minutes = Math.floor(remainingMs / 60000);
          const seconds = Math.floor((remainingMs % 60000) / 1000);
          setEstimatedTimeLeft(`${minutes}:${seconds.toString().padStart(2, '0')}`);
        }
        
        // Add a log entry occasionally
        if (newProgress % 10 === 0) {
          addLog(`Processed ${newProgress}% of transactions`);
        }
        
        // Finish process
        if (newProgress >= 100) {
          clearInterval(interval);
          setIsProcessing(false);
          addLog("Trading process completed successfully");
          
          // Add completion notification
          const completionNotification = {
            id: Date.now(),
            title: 'Trading Complete',
            message: 'Items trading process has completed successfully',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            type: 'success' as const,
            read: false
          };
          
          setNotifications(prev => [completionNotification, ...prev]);
          setUnreadNotifications(prev => prev + 1);
        }
        
        return newProgress > 100 ? 100 : newProgress;
      });
    }, 300);

    return () => clearInterval(interval);
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="Items Trader"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
        <Card>
          <CardHeader>
            <CardTitle>Trading Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Sender Selection */}
            <div className="space-y-2">
              <Label htmlFor="senders">Sender Accounts</Label>
              <Popover open={senderPopoverOpen} onOpenChange={setSenderPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between"
                    aria-expanded={senderPopoverOpen}
                  >
                    {selectedSenders.length > 0
                      ? `${selectedSenders.length} senders selected`
                      : "Select sender accounts"}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-full p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search accounts..." />
                    <CommandEmpty>No account found.</CommandEmpty>
                    <ScrollArea className="h-64">
                      <CommandGroup>
                        {/* Select All / Clear All Controls */}
                        <CommandItem
                          value="select-all-control"
                          onSelect={isAllSendersSelected ? clearAllSenders : selectAllSenders}
                          className="bg-muted/50"
                        >
                          <Check
                            className={`mr-2 h-4 w-4 ${
                              isAllSendersSelected ? "opacity-100" : "opacity-0"
                            }`}
                          />
                          {isAllSendersSelected ? "Clear All" : "Select All"}
                        </CommandItem>
                        
                        {/* Individual Account Items */}
                        {sampleAccounts.map((account) => (
                          <CommandItem
                            key={account.id}
                            value={account.name}
                            onSelect={() => toggleSenderAccount(account.id)}
                          >
                            <Check
                              className={`mr-2 h-4 w-4 ${
                                selectedSenders.includes(account.id)
                                  ? "opacity-100"
                                  : "opacity-0"
                              }`}
                            />
                            {account.name}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </ScrollArea>
                  </Command>
                </PopoverContent>
              </Popover>
              
              <div className="flex flex-wrap gap-2 mt-2">
                {selectedSenders.length > 0 && (
                  <>
                    {selectedSenders.slice(0, 5).map((id) => (
                      <Badge key={id} variant="secondary" className="px-2 py-1">
                        {sampleAccounts.find(a => a.id === id)?.name}
                      </Badge>
                    ))}
                    {selectedSenders.length > 5 && (
                      <Badge variant="outline">+{selectedSenders.length - 5} more</Badge>
                    )}
                  </>
                )}
              </div>
            </div>
            
            {/* Receiver Selection */}
            <div className="space-y-2">
              <Label htmlFor="receiver">Receiver Account</Label>
              <Select value={selectedReceiver} onValueChange={setSelectedReceiver}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select receiver account" />
                </SelectTrigger>
                <SelectContent>
                  <div className="px-2 py-2">
                    <div className="relative">
                      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search accounts..."
                        value={receiverSearchTerm}
                        onChange={(e) => setReceiverSearchTerm(e.target.value)}
                        className="pl-8 mb-2"
                      />
                    </div>
                  </div>
                  <ScrollArea className="h-64">
                    {filteredReceiverAccounts.length > 0 ? (
                      filteredReceiverAccounts.map((account) => (
                        <SelectItem key={account.id} value={account.id}>
                          {account.name}
                        </SelectItem>
                      ))
                    ) : (
                      <div className="px-2 py-2 text-sm text-muted-foreground">
                        No accounts found
                      </div>
                    )}
                  </ScrollArea>
                </SelectContent>
              </Select>
            </div>
            
            {/* Proxy Toggle */}
            <div className="flex items-center justify-between">
              <Label htmlFor="proxies">Use Proxies</Label>
              <Switch
                id="proxies"
                checked={useProxies}
                onCheckedChange={setUseProxies}
              />
            </div>
            
            {/* Concurrency Setting */}
            <div className="space-y-2">
              <Label htmlFor="concurrency">
                Concurrency (1-1000)
              </Label>
              <Input
                id="concurrency"
                type="number"
                min="1"
                max="1000"
                value={concurrency}
                onChange={handleConcurrencyChange}
              />
            </div>
            
            {/* Start Button */}
            <Button 
              className="w-full" 
              disabled={isProcessing}
              onClick={startTrading}
            >
              {isProcessing ? "Processing..." : "Start Trading"}
            </Button>
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
                  {startTime ? `Started: ${startTime.toLocaleTimeString()}` : "Not started"}
                </span>
                <span>
                  {estimatedTimeLeft ? `Est. time left: ${estimatedTimeLeft}` : ""}
                </span>
              </div>
              <Progress value={progress} className="h-2" />
              <div className="text-xs text-right text-muted-foreground">
                {progress}% Complete
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Logs</Label>
              <Card className="border border-muted">
                <ScrollArea className="h-[300px] w-full rounded-md p-4">
                  <div className="space-y-2 font-mono text-sm">
                    {logs.length > 0 ? (
                      logs.map((log, index) => (
                        <div key={index} className="break-all">
                          {log}
                        </div>
                      ))
                    ) : (
                      <div className="text-muted-foreground">
                        Logs will appear here once the process starts
                      </div>
                    )}
                    <div ref={logsEndRef} />
                  </div>
                </ScrollArea>
              </Card>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
