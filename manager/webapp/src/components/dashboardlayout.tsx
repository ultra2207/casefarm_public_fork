// components/DashboardLayout.tsx
"use client";

import React, { ReactNode } from 'react';
import { Sidebar } from "@/components/sidebar";

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 p-6 overflow-y-auto dark:bg-gray-950 dark:text-gray-100">
        {children}
      </div>
    </div>
  );
}

export default DashboardLayout;
