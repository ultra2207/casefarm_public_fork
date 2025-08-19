"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { 
  Home, Users, Settings, ChevronDown, DollarSign, ShoppingCart, 
  Gift, Shield, Store, Repeat, PlusCircle, Trash, 
  FileText, LineChart, BarChart4, ShieldCheck, Activity, Clock, Loader2
} from "lucide-react";

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const [isStartingDocs, setIsStartingDocs] = useState(false);

  const startDocs = async () => {
    setIsStartingDocs(true);
    
    try {
      const response = await fetch('/api/start-docs', { 
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (response.ok) {
        console.log('MkDocs started:', data.message);
        // Wait a moment for server to fully start, then open documentation
        setTimeout(() => {
          window.open('http://localhost:8000', '_blank', 'noopener,noreferrer');
        }, 3000);
      } else {
        console.error('Failed to start MkDocs:', data.error);
        alert('Failed to start documentation server. Check console for details.');
      }
    } catch (error) {
      console.error('Network error:', error);
      alert('Network error occurred while starting documentation server.');
    } finally {
      setIsStartingDocs(false);
    }
  };

  return (
    <div className={`hidden md:flex w-64 flex-col bg-slate-100 dark:bg-slate-900 p-4 shadow-md ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 relative">
            <Image 
              src="/favicon.svg" 
              alt="Farmageddon Logo" 
              fill 
              className="object-contain"
            />
          </div>
          <h2 className="text-2xl font-bold">Farmageddon</h2>
        </div>
      </div>
      
      <Separator className="my-4" />
      
      <ScrollArea className="flex-1">
        <div className="space-y-6">
          <Button variant="ghost" className="w-full justify-start" asChild>
            <Link href="/">
              <Home className="mr-2 h-4 w-4" />
              Overview
            </Link>
          </Button>
          
          <div>
            <Collapsible>
              <div className="flex items-center gap-1">
                <Button variant="ghost" className="flex-grow justify-start" asChild>
                  <Link href="/new-accounts">
                    <div className="flex items-center">
                      <Users className="mr-2 h-4 w-4" />
                      <span>New Accounts</span>
                    </div>
                  </Link>
                </Button>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="px-2">
                    <ChevronDown className="h-4 w-4 transition-transform group-data-[state=open]:rotate-180" />
                  </Button>
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent className="pl-6 mt-1 space-y-1">
                <Button variant="ghost" className="w-full justify-start" asChild>
                  <Link href="/new-accounts/load-accounts">
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    Load Accounts
                  </Link>
                </Button>
                <Button variant="ghost" className="w-full justify-start" asChild>
                  <Link href="/new-accounts/add-balance">
                    <DollarSign className="mr-2 h-4 w-4" />
                    Add Balance
                  </Link>
                </Button>
                <Button variant="ghost" className="w-full justify-start" asChild>
                  <Link href="/new-accounts/buy-prime">
                    <Shield className="mr-2 h-4 w-4" />
                    Buy Prime
                  </Link>
                </Button>
              </CollapsibleContent>
            </Collapsible>
          </div>
          
          <div className="space-y-1">
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/accounts/view">
                <Users className="mr-2 h-4 w-4" />
                View Accounts
              </Link>
            </Button>
            
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/accounts/items-seller">
                <Store className="mr-2 h-4 w-4" />
                Items Seller
              </Link>
            </Button>
            
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/accounts/items-trader">
                <Repeat className="mr-2 h-4 w-4" />
                Items Trader
              </Link>
            </Button>
            
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/accounts/create-farmlabs">
                <PlusCircle className="mr-2 h-4 w-4" />
                Create Farmlabs Jobs
              </Link>
            </Button>
            
            <Button variant="ghost" className="w-full justify-start" asChild>
              <a 
                href="https://dashboard.farmlabs.dev/bot-jobs" 
                target="_blank" 
                rel="noopener noreferrer"
              >
                <Trash className="mr-2 h-4 w-4" />
                View Farmlabs Jobs
              </a>
            </Button>
            
            <Button variant="ghost" className="w-full justify-start" asChild>
              <Link href="/accounts/armoury-utilities">
                <Shield className="mr-2 h-4 w-4" />
                Armoury Utilities
              </Link>
            </Button>
          </div>
          
          <Collapsible>
            <div className="flex items-center gap-1">
              <Button variant="ghost" className="flex-grow justify-start" asChild>
                <Link href="/marketplace">
                  <div className="flex items-center">
                    <ShoppingCart className="mr-2 h-4 w-4" />
                    <span>Marketplace</span>
                  </div>
                </Link>
              </Button>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="px-2">
                  <ChevronDown className="h-4 w-4 transition-transform group-data-[state=open]:rotate-180" />
                </Button>
              </CollapsibleTrigger>
            </div>
            <CollapsibleContent className="space-y-1 pl-6 mt-1">
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/marketplace/csfloat">
                  <ShoppingCart className="mr-2 h-4 w-4" />
                  CSFloat
                </Link>
              </Button>
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/marketplace/market-csgo">
                  <ShoppingCart className="mr-2 h-4 w-4" />
                  Market.CSGO
                </Link>
              </Button>
            </CollapsibleContent>
          </Collapsible>
          
          <Button variant="ghost" className="w-full justify-start" asChild>
            <Link href="/statistics">
              <LineChart className="mr-2 h-4 w-4" />
              Statistics
            </Link>
          </Button>
          
          <Collapsible>
            <div className="flex items-center gap-1">
              <Button variant="ghost" className="flex-grow justify-start" asChild>
                <Link href="/settings">
                  <div className="flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </div>
                </Link>
              </Button>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="px-2">
                  <ChevronDown className="h-4 w-4 transition-transform group-data-[state=open]:rotate-180" />
                </Button>
              </CollapsibleTrigger>
            </div>
            <CollapsibleContent className="space-y-1 pl-6 mt-1">
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/settings/preferences">
                  <Settings className="mr-2 h-4 w-4" />
                  Preferences
                </Link>
              </Button>
              <Button variant="ghost" className="w-full justify-start" asChild>
                <Link href="/settings/edit-config">
                  <FileText className="mr-2 h-4 w-4" />
                  Edit Config
                </Link>
              </Button>
            </CollapsibleContent>
          </Collapsible>
        </div>
      </ScrollArea>

      <div className="mt-auto pt-4 border-t dark:border-gray-700">
        <Button 
          variant="outline" 
          className="w-full"
          onClick={startDocs}
          disabled={isStartingDocs}
        >
          {isStartingDocs ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Starting Docs...
            </>
          ) : (
            <>
              <FileText className="mr-2 h-4 w-4" />
              Documentation
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

export default Sidebar;
