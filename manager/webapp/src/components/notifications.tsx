// components/Notifications.tsx
"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bell, X, Info, CheckCircle, AlertTriangle, AlertOctagon } from "lucide-react";

interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  time: string;
  read: boolean;
}

interface NotificationsProps {
  notifications: Notification[];
  unreadNotifications: number;
  onMarkAllRead?: () => void;
}

export function Notifications({ 
  notifications, 
  unreadNotifications, 
  onMarkAllRead = () => {} 
}: NotificationsProps) {
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <div className="relative">
      <Button 
        variant="ghost" 
        className="relative p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800"
        onClick={() => setShowNotifications(!showNotifications)}
      >
        <Bell className="h-5 w-5" />
        {unreadNotifications > 0 && (
          <div className="absolute -top-1 -right-1 h-5 w-5 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs">
            {unreadNotifications}
          </div>
        )}
      </Button>
      
      {showNotifications && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 rounded-md shadow-lg z-50 border dark:border-slate-800 overflow-hidden">
          <div className="flex items-center justify-between p-3 border-b dark:border-slate-700">
            <h4 className="font-semibold">Notifications</h4>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" className="h-8 text-xs" onClick={onMarkAllRead}>
                Mark all read
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-8 w-8 p-0"
                onClick={() => setShowNotifications(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          <ScrollArea className="h-[300px]">
            <div className="divide-y dark:divide-slate-700">
              {notifications.map((notification) => (
                <div 
                  key={notification.id}
                  className={`p-3 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-full 
                      ${notification.type === 'info' ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300' :
                      notification.type === 'success' ? 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-300' :
                      notification.type === 'warning' ? 'bg-amber-100 text-amber-600 dark:bg-amber-900 dark:text-amber-300' :
                      'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-300'}`}
                    >
                      {notification.type === 'info' && <Info className="h-4 w-4" />}
                      {notification.type === 'success' && <CheckCircle className="h-4 w-4" />}
                      {notification.type === 'warning' && <AlertTriangle className="h-4 w-4" />}
                      {notification.type === 'error' && <AlertOctagon className="h-4 w-4" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <h5 className="font-medium text-sm">{notification.title}</h5>
                        <span className="text-xs text-slate-500 dark:text-slate-400">{notification.time}</span>
                      </div>
                      <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">{notification.message}</p>
                    </div>
                    {!notification.read && (
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5"></div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}

export default Notifications;
