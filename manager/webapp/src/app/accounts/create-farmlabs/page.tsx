"use client";

import React, { useState } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { 
  Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle 
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from "@/components/ui/select";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";

// Mock data with updated status types and avatars
const mockAccounts = [
  { id: '1', name: 'Account1', level: 15, status: ['ready-armoury'], avatar: '/avatars/avatar1.png' },
  { id: '2', name: 'Account2', level: 32, status: ['ready-drop'], avatar: '/avatars/avatar2.png' },
  { id: '3', name: 'Account3', level: 8, status: ['ready-armoury', 'ready-drop'], avatar: '/avatars/avatar3.png' },
  { id: '4', name: 'Account4', level: 39, status: ['not-ready'], avatar: '/avatars/avatar4.png' },
  { id: '5', name: 'Account5', level: 22, status: ['banned'], avatar: '/avatars/avatar5.png' },
];

// Sample notifications for the PageHeader component
const initialNotifications = [
  { 
    id: 1, 
    title: 'Job Completed', 
    message: 'XP Farm job completed for 3 accounts',
    time: '14:32', 
    type: 'success', 
    read: false 
  },
  { 
    id: 2, 
    title: 'Account Update', 
    message: 'Account details updated successfully',
    time: '13:15', 
    type: 'info', 
    read: false 
  },
  { 
    id: 3, 
    title: 'Drop Detected', 
    message: 'A rare drop was detected on Account2',
    time: '11:50', 
    type: 'warning', 
    read: true 
  },
];

export default function FarmLabsJobsPage() {
  // Notification state for PageHeader
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
  
  // Account selection state
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("xp-farm");
  
  // Account filtering and display state
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('any');
  const [sortBy, setSortBy] = useState('name-asc');
  const [showAvatars, setShowAvatars] = useState(false);
  
  // XP Farm configs with defaults
  const [intensity, setIntensity] = useState("normal");
  const [mapGroup, setMapGroup] = useState("defusal-alpha");
  const [useBonusWeapons, setUseBonusWeapons] = useState(false);
  const [targetLevel, setTargetLevel] = useState(40);
  const [targetXp, setTargetXp] = useState(1);
  const [dropDetection, setDropDetection] = useState(false);
  
  // Claim Drop configs
  const [autoClaim, setAutoClaim] = useState(true);

  // Logs state
  const [logs, setLogs] = useState<Array<{id: number, timestamp: string, level: string, message: string, details?: string}>>([]);
  const [isLogsExpanded, setIsLogsExpanded] = useState(false);
  const [showLogsPopout, setShowLogsPopout] = useState(false);
  
  // Filter and sort accounts based on search term and filters
  const filteredAccounts = mockAccounts.filter(account => {
    // Search filter
    const matchesSearch = account.name.toLowerCase().includes(searchTerm.toLowerCase());
    
    // Status filter
    const matchesStatus = 
      statusFilter === 'any' || 
      (statusFilter === 'ready-armoury' && account.status.includes('ready-armoury')) ||
      (statusFilter === 'ready-drop' && account.status.includes('ready-drop')) ||
      (statusFilter === 'ready-both' && 
        account.status.includes('ready-armoury') && 
        account.status.includes('ready-drop')) ||
      (statusFilter === 'not-ready' && account.status.includes('not-ready')) ||
      (statusFilter === 'banned' && account.status.includes('banned'));
    
    return matchesSearch && matchesStatus;
  }).sort((a, b) => {
    // Sort accounts
    switch (sortBy) {
      case 'name-asc':
        return a.name.localeCompare(b.name);
      case 'name-desc':
        return b.name.localeCompare(a.name);
      case 'level-asc':
        return a.level - b.level;
      case 'level-desc':
        return b.level - a.level;
      default:
        return 0;
    }
  });
  
  const toggleAccount = (accountId: string) => {
    setSelectedAccounts(prev => 
      prev.includes(accountId) 
        ? prev.filter(id => id !== accountId)
        : [...prev, accountId]
    );
  };
  
  const toggleAll = () => {
    setSelectedAccounts(
      selectedAccounts.length === filteredAccounts.length 
        ? [] 
        : filteredAccounts.map(acc => acc.id)
    );
  };

  const addLog = (level: string, message: string, details?: string) => {
    const newLog = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toLocaleTimeString(),
      level,
      message,
      details
    };
    setLogs(prev => [...prev, newLog]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const toggleLogsExpansion = () => {
    setIsLogsExpanded(!isLogsExpanded);
  };

  const openLogsPopout = () => {
    setShowLogsPopout(true);
  };

  const closeLogsPopout = () => {
    setShowLogsPopout(false);
  };
  
  const handleRunJob = () => {
    // Add initial log
    addLog('info', `Starting ${selectedJob} job on ${selectedAccounts.length} accounts`, 
      `Selected accounts: ${selectedAccounts.map(id => mockAccounts.find(acc => acc.id === id)?.name).join(', ')}`);

    // Add a notification when job is run
    const newNotification = {
      id: Date.now(),
      title: 'Job Started',
      message: `Running ${selectedJob} on ${selectedAccounts.length} accounts`,
      time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
      type: 'info' as 'info' | 'success' | 'warning' | 'error',
      read: false
    };
    
    setNotifications([newNotification, ...notifications]);
    setUnreadNotifications(unreadNotifications + 1);

    // Simulate job progress with additional logs
    setTimeout(() => {
      addLog('info', 'Initializing job configuration...', `Job type: ${selectedJob}, Intensity: ${intensity}`);
    }, 1000);

    setTimeout(() => {
      addLog('warn', 'Connecting to game servers...', 'Establishing secure connections');
    }, 2000);

    setTimeout(() => {
      addLog('success', 'Job execution started successfully', 'All accounts are now processing');
    }, 3000);
    
    console.log(`Running ${selectedJob} on ${selectedAccounts.length} accounts`);
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'text-red-400';
      case 'warn': return 'text-yellow-400';
      case 'success': return 'text-green-400';
      case 'info': 
      default: return 'text-blue-400';
    }
  };

  const getLogLevelBg = (level: string) => {
    switch (level) {
      case 'error': return 'bg-red-900/20';
      case 'warn': return 'bg-yellow-900/20';
      case 'success': return 'bg-green-900/20';
      case 'info': 
      default: return 'bg-blue-900/20';
    }
  };

  const LogsContent = ({ inPopout = false }) => (
    <div className={`${inPopout ? 'h-full' : isLogsExpanded ? 'max-h-96' : 'max-h-48'} transition-all duration-300 overflow-hidden`}>
      <div className={`border rounded-md bg-gray-900 p-4 overflow-y-auto ${inPopout ? 'h-full' : 'h-full'}`}>
        {logs.length > 0 ? (
          <div className="space-y-2">
            {logs.map((log) => (
              <div key={log.id} className={`p-2 rounded text-sm ${getLogLevelBg(log.level)}`}>
                <div className="flex items-start space-x-2">
                  <span className="text-gray-400 text-xs font-mono min-w-[60px]">
                    {log.timestamp}
                  </span>
                  <span className={`text-xs font-semibold uppercase min-w-[60px] ${getLogLevelColor(log.level)}`}>
                    [{log.level}]
                  </span>
                  <span className="text-gray-100 flex-1">
                    {log.message}
                  </span>
                </div>
                {log.details && (
                  <div className="mt-1 ml-[124px] text-xs text-gray-400">
                    {log.details}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-sm text-center py-8">
            No logs yet. Run a job to see execution logs here.
          </div>
        )}
      </div>
    </div>
  );
  
  return (
    <DashboardLayout>
      <PageHeader
        title="FarmLabs Jobs"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <div className="container mx-auto py-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Account Selection Section */}
          <div className="md:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Select Accounts</CardTitle>
                <CardDescription>Filter and select accounts to run jobs on</CardDescription>
              </CardHeader>
              <CardContent>
                {/* Account Filter */}
                <div className="space-y-4">
                  <div>
                    <Input 
                      placeholder="Search accounts..." 
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="mb-4"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger>
                          <SelectValue placeholder="Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="any">Any Status</SelectItem>
                          <SelectItem value="ready-armoury">Ready for Armoury</SelectItem>
                          <SelectItem value="ready-drop">Ready for Drop</SelectItem>
                          <SelectItem value="ready-both">Ready for Both</SelectItem>
                          <SelectItem value="not-ready">Not Ready</SelectItem>
                          <SelectItem value="banned">Banned</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Select value={sortBy} onValueChange={setSortBy}>
                        <SelectTrigger>
                          <SelectValue placeholder="Sort by" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="name-asc">Name (A-Z)</SelectItem>
                          <SelectItem value="name-desc">Name (Z-A)</SelectItem>
                          <SelectItem value="level-asc">Level (Low-High)</SelectItem>
                          <SelectItem value="level-desc">Level (High-Low)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 pt-2">
                    <Switch 
                      id="show-avatars" 
                      checked={showAvatars}
                      onCheckedChange={setShowAvatars}
                    />
                    <Label htmlFor="show-avatars">Show Account Avatars</Label>
                  </div>
                </div>
                
                {/* Account Selection List */}
                <div className="mt-4">
                  <div className="flex items-center mb-2">
                    <Checkbox 
                      id="select-all" 
                      checked={selectedAccounts.length === filteredAccounts.length && filteredAccounts.length > 0} 
                      onCheckedChange={toggleAll}
                    />
                    <label htmlFor="select-all" className="ml-2 text-sm font-medium">
                      Select All ({filteredAccounts.length})
                    </label>
                  </div>
                  
                  <div className="border rounded-md max-h-[400px] overflow-y-auto">
                    {filteredAccounts.length > 0 ? filteredAccounts.map(account => (
                      <div 
                        key={account.id}
                        className="flex items-center justify-between p-3 border-b last:border-0"
                      >
                        <div className="flex items-center">
                          <Checkbox 
                            id={`account-${account.id}`}
                            checked={selectedAccounts.includes(account.id)}
                            onCheckedChange={() => toggleAccount(account.id)}
                          />
                          <label htmlFor={`account-${account.id}`} className="ml-2 flex items-center">
                            <div>
                              <div className="font-medium flex items-center">
                                {account.name}
                                {showAvatars && (
                                  <img 
                                    src={account.avatar} 
                                    alt="Avatar" 
                                    className="w-6 h-6 rounded-full ml-2" 
                                  />
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground">Level {account.level}</div>
                            </div>
                          </label>
                        </div>
                        <div className="flex space-x-1">
                          {account.status.map(stat => (
                            <span key={stat} className={`text-xs px-2 py-1 rounded-full ${
                              stat === 'ready-armoury' ? 'bg-blue-100 text-blue-800' : 
                              stat === 'ready-drop' ? 'bg-green-100 text-green-800' : 
                              stat === 'not-ready' ? 'bg-yellow-100 text-yellow-800' : 
                              'bg-red-100 text-red-800'
                            }`}>
                              {stat === 'ready-armoury' ? 'Armoury' : 
                              stat === 'ready-drop' ? 'Drop' :
                              stat === 'not-ready' ? 'Not Ready' :
                              'Banned'}
                            </span>
                          ))}
                        </div>
                      </div>
                    )) : (
                      <div className="p-4 text-center text-muted-foreground">
                        No accounts match the current filters
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <div className="text-sm text-muted-foreground">
                  {selectedAccounts.length} accounts selected
                </div>
              </CardFooter>
            </Card>
          </div>
          
          {/* Job Configuration Section */}
          <div className="md:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Configure Job</CardTitle>
                <CardDescription>Select a job and configure its settings</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="xp-farm" onValueChange={setSelectedJob}>
                  <TabsList className="grid grid-cols-5 mb-4">
                    <TabsTrigger value="xp-farm">XP Farm</TabsTrigger>
                    <TabsTrigger value="update-details">Update Details</TabsTrigger>
                    <TabsTrigger value="claim-medal">Claim Medal</TabsTrigger>
                    <TabsTrigger value="arms-race">Arms Race</TabsTrigger>
                    <TabsTrigger value="claim-drop">Claim Drop</TabsTrigger>
                  </TabsList>
                  
                  {/* XP Farm Configuration */}
                  <TabsContent value="xp-farm" className="space-y-6">
                    <div>
                      <h3 className="text-lg font-medium mb-4">XP Farm (DM memory)</h3>
                      <p className="text-sm text-muted-foreground mb-6">
                        Configure settings for XP farming jobs
                      </p>
                      
                      <div className="space-y-6">
                        {/* Intensity and Map Group side by side */}
                        <div className="grid grid-cols-2 gap-6">
                          <div>
                            <Label className="block mb-2">Intensity</Label>
                            <Select value={intensity} onValueChange={setIntensity}>
                              <SelectTrigger>
                                <SelectValue placeholder="Select intensity" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="noob">Noob</SelectItem>
                                <SelectItem value="normal">Normal</SelectItem>
                                <SelectItem value="clara">Clara</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div>
                            <Label className="block mb-2">Map Group</Label>
                            <Select value={mapGroup} onValueChange={setMapGroup}>
                              <SelectTrigger>
                                <SelectValue placeholder="Select map group" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="defusal-alpha">Defusal Group Alpha</SelectItem>
                                <SelectItem value="defusal-delta">Defusal Group Delta</SelectItem>
                                <SelectItem value="community">Community Map Group</SelectItem>
                                <SelectItem value="hostage">Hostage Group</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        
                        <Accordion type="single" collapsible className="w-full">
                          <AccordionItem value="maps-info">
                            <AccordionTrigger className="text-sm py-2">View included maps</AccordionTrigger>
                            <AccordionContent>
                              {mapGroup === "defusal-alpha" && (
                                <p className="text-sm">Includes Dust II, Mirage, Inferno and Vertigo.</p>
                              )}
                              {mapGroup === "defusal-delta" && (
                                <p className="text-sm">Includes Train, Anubis, Ancient, Overpass and Nuke.</p>
                              )}
                              {mapGroup === "community" && (
                                <p className="text-sm">Includes Jura, Grail and Agency.</p>
                              )}
                              {mapGroup === "hostage" && (
                                <p className="text-sm">Includes Office and Italy.</p>
                              )}
                            </AccordionContent>
                          </AccordionItem>
                        </Accordion>
                        
                        <div className="flex items-center space-x-2 py-2">
                          <Switch 
                            id="bonus-weapons" 
                            checked={useBonusWeapons}
                            onCheckedChange={setUseBonusWeapons}
                          />
                          <Label htmlFor="bonus-weapons">Use Bonus Weapons</Label>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-6 py-2">
                          <div>
                            <Label htmlFor="target-level" className="block mb-2">Target Level</Label>
                            <Input 
                              id="target-level"
                              type="number" 
                              value={targetLevel}
                              onChange={(e) => setTargetLevel(parseInt(e.target.value))} 
                            />
                          </div>
                          <div>
                            <Label htmlFor="target-xp" className="block mb-2">Target XP</Label>
                            <Input 
                              id="target-xp"
                              type="number" 
                              value={targetXp}
                              onChange={(e) => setTargetXp(parseInt(e.target.value))} 
                            />
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2 py-2">
                          <Switch 
                            id="drop-detection" 
                            checked={dropDetection}
                            onCheckedChange={setDropDetection}
                          />
                          <div>
                            <Label htmlFor="drop-detection">Drop Detection</Label>
                            <p className="text-xs text-muted-foreground mt-1">
                              Automatically complete this XP Farm job if a drop is detected, even if the targets are not yet reached.
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                  
                  {/* Update Account Details Configuration */}
                  <TabsContent value="update-details">
                    <div className="py-4">
                      <h3 className="text-lg font-medium mb-2">Update Account Details</h3>
                      <p className="text-sm text-muted-foreground">
                        This job has no options but is only for new accounts.
                      </p>
                    </div>
                  </TabsContent>
                  
                  {/* Claim Service Medal Configuration */}
                  <TabsContent value="claim-medal">
                    <div className="py-4">
                      <h3 className="text-lg font-medium mb-2">Claim Service Medal</h3>
                      <p className="text-sm text-muted-foreground">
                        This job is for claiming the service medal when an account reaches level 40.
                      </p>
                    </div>
                  </TabsContent>
                  
                  {/* Queue Arms Race Configuration */}
                  <TabsContent value="arms-race">
                    <div className="py-4">
                      <h3 className="text-lg font-medium mb-2">Queue Arms Race</h3>
                      <p className="text-sm text-muted-foreground">
                        This job queues up for arms race and takes around 3 minutes to complete.
                      </p>
                    </div>
                  </TabsContent>
                  
                  {/* Claim Drop Configuration */}
                  <TabsContent value="claim-drop">
                    <div className="py-4">
                      <h3 className="text-lg font-medium mb-2">Claim Drop</h3>
                      <div className="mt-4 flex items-center space-x-2">
                        <Switch 
                          id="auto-claim" 
                          checked={autoClaim}
                          onCheckedChange={setAutoClaim}
                        />
                        <Label htmlFor="auto-claim">Auto Claim</Label>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
              <CardFooter>
                <Button 
                  onClick={handleRunJob}
                  disabled={selectedAccounts.length === 0}
                  className="w-full"
                >
                  Run Job on Selected Accounts
                </Button>
              </CardFooter>
            </Card>

            {/* Logs Section */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Job Logs</CardTitle>
                    <CardDescription>Monitor job execution and progress</CardDescription>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearLogs}
                      disabled={logs.length === 0}
                    >
                      Clear Logs
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={toggleLogsExpansion}
                    >
                      {isLogsExpanded ? 'Collapse' : 'Expand'}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <LogsContent />
              </CardContent>
              <CardFooter>
                <div className="text-sm text-muted-foreground">
                  {logs.length} log entries
                </div>
              </CardFooter>
            </Card>
          </div>
        </div>
      </div>

      {/* Logs Popout Window */}
      {showLogsPopout && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-xl w-4/5 h-4/5 max-w-4xl max-h-[600px] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">Job Execution Logs</h2>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearLogs}
                >
                  Clear Logs
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={closeLogsPopout}
                >
                  Close
                </Button>
              </div>
            </div>
            <div className="flex-1 p-4 overflow-hidden">
              <LogsContent inPopout={true} />
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
