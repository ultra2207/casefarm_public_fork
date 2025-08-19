// components/PageHeader.tsx
"use client";

import React from 'react';
import { Separator } from "@/components/ui/separator";
import { Notifications } from "@/components/notifications";

interface PageHeaderProps {
  title: string;
  notifications: any[];
  unreadNotifications: number;
  onMarkAllRead?: () => void;
}

export function PageHeader({ 
  title, 
  notifications, 
  unreadNotifications,
  onMarkAllRead 
}: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-3xl font-bold">{title}</h1>
      
      <div className="flex items-center">
        <Separator orientation="vertical" className="h-8 mx-4" />
        <Notifications 
          notifications={notifications} 
          unreadNotifications={unreadNotifications} 
          onMarkAllRead={onMarkAllRead}
        />
      </div>
    </div>
  );
}

export default PageHeader;