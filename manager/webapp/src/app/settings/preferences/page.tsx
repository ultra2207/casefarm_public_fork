"use client";

import React, { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboardlayout';
import { PageHeader } from '@/components/pageheader';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { toast } from "sonner";

// Sample notifications for the PageHeader
const initialNotifications = [
  { id: 1, title: 'Preferences Loaded', message: 'Preferences page loaded successfully', time: '17:50', type: 'success' as const, read: false },
];

// Logger verbosity levels with 'Trace' as the lowest level
const loggerLevels = ['Trace', 'Debug', 'Info', 'Warning', 'Error', 'Critical'];

export default function PreferencesPage() {
  // State for notifications
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );

  // State for user preferences
  const [theme, setTheme] = useState<string>('system');
  const [loggerVerbosity, setLoggerVerbosity] = useState<number>(2); // 0-5 (trace to critical)
  const [enableNotifications, setEnableNotifications] = useState<boolean>(true);
  
  // State for logs
  const [logs, setLogs] = useState<string[]>([]);

  // Apply theme whenever it changes
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else if (theme === 'light') {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    } else {
      // System default
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.classList.toggle('dark', prefersDark);
      document.documentElement.classList.toggle('light', !prefersDark);
    }
  }, [theme]);
  
  // Function to add logs
  const addLog = (message: string) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  // Load preferences from API or localStorage
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        // For example purposes, we're mocking API call
        // You can replace this with actual API call to fetch user preferences
        const storedTheme = localStorage.getItem('theme') || 'system';
        const storedLoggerVerbosity = Number(localStorage.getItem('loggerVerbosity') || '2');
        const storedEnableNotifications = localStorage.getItem('enableNotifications') !== 'false';
        
        setTheme(storedTheme);
        setLoggerVerbosity(storedLoggerVerbosity);
        setEnableNotifications(storedEnableNotifications);
        
        addLog("Preferences loaded successfully");
        toast.success("Preferences loaded successfully");
      } catch (error) {
        console.error("Failed to load preferences:", error);
        addLog("Failed to load preferences. Using defaults.");
        toast.error("Failed to load preferences. Using defaults.");
      }
    };
    
    loadPreferences();
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

  // Save preferences
  const handleSavePreferences = () => {
    // Save to localStorage for example purposes
    // In a real application, you might want to save to a database via API
    localStorage.setItem('theme', theme);
    localStorage.setItem('loggerVerbosity', loggerVerbosity.toString());
    localStorage.setItem('enableNotifications', enableNotifications.toString());
    
    addLog(`Saved preferences: Theme=${theme}, Logger verbosity=${loggerLevels[loggerVerbosity]}, Notifications=${enableNotifications}`);
    toast.success("Preferences saved successfully");
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="Preferences"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <div className="p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Application Preferences</CardTitle>
            <CardDescription>Customize your application experience</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="theme">Theme</Label>
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger id="theme" className="w-full">
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="system">System Default</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label htmlFor="logger-verbosity">Logger Verbosity</Label>
                <span className="text-sm text-muted-foreground">
                  {loggerLevels[loggerVerbosity]}
                </span>
              </div>
              <Slider 
                id="logger-verbosity"
                min={0} 
                max={5} 
                step={1} 
                value={[loggerVerbosity]} 
                onValueChange={(value) => setLoggerVerbosity(value[0])} 
              />
            </div>
            
            <Separator className="my-4" />
            
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Notification Settings</h3>
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="enable-notifications">Enable Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive notifications about application events
                  </p>
                </div>
                <Switch 
                  id="enable-notifications"
                  checked={enableNotifications} 
                  onCheckedChange={(checked) => {
                    setEnableNotifications(checked);
                    if (checked) {
                      toast("Notifications enabled");
                    }
                  }}
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" onClick={() => {
              setTheme('system');
              setLoggerVerbosity(2);
              setEnableNotifications(true);
              toast.info("Preferences reset to defaults");
            }}>
              Reset
            </Button>
            <Button onClick={handleSavePreferences}>
              Save Preferences
            </Button>
          </CardFooter>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Activity Log</CardTitle>
            <CardDescription>Recent activity and system logs</CardDescription>
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
    </DashboardLayout>
  );
}
