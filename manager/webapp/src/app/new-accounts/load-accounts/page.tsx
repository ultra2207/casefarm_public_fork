"use client";

import React, { useState, useEffect, useRef } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { 
  AlertCircle, 
  ChevronDown, 
  CheckCircle,
  Terminal,
  Upload
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

// Sample notifications data
const initialNotifications = [
  { id: 1, title: 'Low Balance Warning', message: 'Account cs2_player789 is running low on funds', time: '12:19', type: 'warning', read: false },
  { id: 2, title: 'Trade Completed', message: 'Trade offer with user XYZ was completed successfully', time: '11:45', type: 'success', read: false },
  { id: 3, title: 'System Update', message: 'Farmageddon updated to version 1.2.3', time: '09:30', type: 'info', read: true },
  { id: 4, title: 'Error Detected', message: 'Failed to connect to Steam API. Retrying...', time: '08:15', type: 'error', read: true },
];

const LoadAccountsPage: React.FC = () => {
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [startTime, setStartTime] = useState<Date | null>(null);
  const [logs, setLogs] = useState<Array<{level: string, time: string, message: string}>>([]);
  const [showLogs, setShowLogs] = useState<boolean>(false);
  const [processingStage, setProcessingStage] = useState<string>("Idle");
  const [notifications, setNotifications] = useState(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );
  const [accountsCount, setAccountsCount] = useState<number>(0);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // API base URL - adjust as needed
  const API_BASE_URL = 'http://localhost:8000';

  // Regex to validate each line format
  const lineRegex = /^[^:]+:[^|]+ *\| *[^:]+:[^ ]+ \(\d+\)$/;

  // Auto-scroll logs to bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Connect to log stream
  const connectToLogStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    eventSourceRef.current = new EventSource(`${API_BASE_URL}/logs/stream`);
    
    eventSourceRef.current.onmessage = (event) => {
      try {
        const logData = JSON.parse(event.data);
        setLogs(prevLogs => [...prevLogs, logData]);
        
        // Update progress if included in log data
        if (logData.progress !== undefined) {
          setProgress(logData.progress);
        }
        
        // Update processing stage if included
        if (logData.stage) {
          setProcessingStage(logData.stage);
        }
      } catch (e) {
        // If not JSON, treat as plain text
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setLogs(prevLogs => [...prevLogs, { 
          level: 'INFO', 
          time: timeStr, 
          message: event.data 
        }]);
      }
    };

    eventSourceRef.current.onerror = (error) => {
      console.error('EventSource failed:', error);
      setError('Lost connection to log stream');
    };
  };

  // Disconnect from log stream
  const disconnectFromLogStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnectFromLogStream();
    };
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

  // Validate file before upload
  const validateFile = (file: File): Promise<{ isValid: boolean; errorMessage?: string; accountCount?: number }> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const lines = text.split('\n').map(line => line.trim()).filter(line => line.length > 0);
        
        const invalidLines: string[] = [];
        for (const [index, line] of lines.entries()) {
          if (!lineRegex.test(line)) {
            invalidLines.push(`Line ${index + 1}: ${line.substring(0, 50)}...`);
          }
        }
        
        if (invalidLines.length > 0) {
          resolve({
            isValid: false,
            errorMessage: `Invalid format detected in ${invalidLines.length} lines. First error: ${invalidLines[0]}`
          });
        } else {
          resolve({
            isValid: true,
            accountCount: lines.length
          });
        }
      };
      
      reader.onerror = () => {
        resolve({
          isValid: false,
          errorMessage: "Error reading file"
        });
      };
      
      reader.readAsText(file);
    });
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setSuccess(null);
    setProgress(0);
    setLogs([]);
    setProcessingStage("Validating");
    setStartTime(new Date());
    
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file format first
    setIsUploading(true);
    const validation = await validateFile(file);
    
    if (!validation.isValid) {
      setError(validation.errorMessage || "File validation failed");
      setIsUploading(false);
      setProcessingStage("Error");
      return;
    }

    setAccountsCount(validation.accountCount || 0);
    setProcessingStage("Uploading");
    setShowLogs(true);
    
    // Connect to log stream before starting upload
    connectToLogStream();

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/load-accounts`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setSuccess(result.message);
        setProcessingStage("Complete");
        setProgress(100);
      } else {
        setError(result.detail || 'Upload failed');
        setProcessingStage("Error");
      }
    } catch (err) {
      setError('Network error: Unable to connect to server');
      setProcessingStage("Error");
    } finally {
      setIsUploading(false);
      // Keep log stream open for a bit longer to catch final logs
      setTimeout(() => {
        disconnectFromLogStream();
      }, 5000);
    }
  };

  const handleUseDefaultFile = async () => {
    setError(null);
    setSuccess(null);
    setProgress(0);
    setLogs([]);
    setProcessingStage("Processing");
    setStartTime(new Date());
    setIsUploading(true);
    setShowLogs(true);
    
    // Connect to log stream
    connectToLogStream();

    try {
      const response = await fetch(`${API_BASE_URL}/load-accounts-default`, {
        method: 'POST',
      });

      const result = await response.json();

      if (response.ok) {
        setSuccess(result.message);
        setProcessingStage("Complete");
        setProgress(100);
      } else {
        setError(result.detail || 'Processing failed');
        setProcessingStage("Error");
      }
    } catch (err) {
      setError('Network error: Unable to connect to server');
      setProcessingStage("Error");
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        disconnectFromLogStream();
      }, 5000);
    }
  };

  return (
    <DashboardLayout>
      <PageHeader 
        title="Load Accounts" 
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <Card className="bg-white dark:bg-slate-900">
        <CardHeader>
          <CardTitle>Upload Accounts File</CardTitle>
          <CardDescription className="text-slate-600 dark:text-slate-300">
            Upload a text file containing account information. Each line should follow this format:
            <code className="block bg-muted p-2 mt-2 rounded text-sm">
              steam_username:steam_password | email_id:email_password (phone_number)
            </code>
            <span className="text-sm mt-1 block">Example: boredBass57788:aocCLVL60e3y|plazhhuajie@hotmail.com:dkrOGKGi1OvcMr (447956144588)</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid w-full items-center gap-1.5">
              <label htmlFor="account-file" className="text-sm font-medium">
                Select File
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  id="account-file"
                  accept=".txt"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-slate-900 dark:file:text-slate-100 file:text-sm file:font-medium disabled:opacity-50"
                />
                <Button 
                  onClick={handleUseDefaultFile}
                  disabled={isUploading}
                  variant="outline"
                  size="sm"
                >
                  Use Default
                </Button>
              </div>
            </div>
            
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            {success && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertTitle>Success</AlertTitle>
                <AlertDescription>{success}</AlertDescription>
              </Alert>
            )}
            
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress ({processingStage})</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="w-full" />
              {startTime && accountsCount > 0 && (
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>Started: {startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  <span>Accounts: {accountsCount}</span>
                </div>
              )}
            </div>
            
            <Collapsible open={showLogs} onOpenChange={setShowLogs} className="mt-4">
              <CollapsibleTrigger asChild>
                <Button 
                  className="flex items-center w-full justify-between !bg-slate-800 hover:!bg-slate-700 text-white rounded-md border-0" 
                  size="sm"
                >
                  <div className="flex items-center">
                    <Terminal className="h-4 w-4 mr-2" />
                    Live Logs ({logs.length})
                  </div>
                  <ChevronDown className={`h-4 w-4 transition-transform ${showLogs ? "rotate-180" : ""}`} />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="p-4 bg-slate-800 text-slate-100 rounded-md font-mono text-sm">
                  <ScrollArea className="h-[300px]">
                    <div className="space-y-1">
                      {logs.map((log, index) => (
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
                      <div ref={logEndRef} />
                      {logs.length === 0 && (
                        <div className="text-slate-400 py-2">Waiting for logs...</div>
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>
    </DashboardLayout>
  );
};

export default LoadAccountsPage;
