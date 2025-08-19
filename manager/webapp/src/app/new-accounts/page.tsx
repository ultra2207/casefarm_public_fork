// app/new-accounts/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, FileText, DollarSign, Send, ShoppingCart, CheckCircle } from "lucide-react";
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";

// Sample initial notifications
const initialNotifications = [
  { 
    id: 1, 
    title: 'New Account Alert', 
    message: 'New accounts ready for processing',
    time: '12:19', 
    type: 'info', 
    read: false 
  },
  { 
    id: 2, 
    title: 'Balance Added', 
    message: '$5 added to account #45921',
    time: '11:45', 
    type: 'success', 
    read: false 
  }
];

export default function NewAccountsPage() {
  // State for notifications
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

  const steps = [
    {
      id: 1,
      title: "Load Accounts",
      description: "Load the accounts from txt file and add steamguard",
      link: "/new-accounts/load-accounts",
      icon: <FileText className="h-5 w-5 mr-2" />,
      details: "Upload account details from a text file and configure SteamGuard for additional security."
    },
    {
      id: 2,
      title: "Add Balance",
      description: "Select the account and add at least $5 worth of balance",
      link: "/new-accounts/add-balance",
      icon: <DollarSign className="h-5 w-5 mr-2" />,
      details: "Add a minimum of $5 to the selected account to enable trading functionality."
    },
    {
      id: 3,
      title: "Send Items",
      description: "Select that account as a receiver account and send items to it",
      link: "/accounts/items-trader",
      icon: <Send className="h-5 w-5 mr-2" />,
      details: "Designate the account as a receiver and transfer items to build inventory."
    },
    {
      id: 4,
      title: "Sell Items",
      description: "After waiting for 7 days select the account and sell it",
      link: "/accounts/items-seller",
      icon: <ShoppingCart className="h-5 w-5 mr-2" />,
      details: "Wait for the mandatory 7-day holding period to complete, then proceed to sell the account's items."
    },
    {
      id: 5,
      title: "Buy Prime",
      description: "Purchase prime and 5 armoury passes and update the database",
      link: "/new-accounts/buy-prime",
      icon: <CheckCircle className="h-5 w-5 mr-2" />,
      details: "Complete the account setup by purchasing Prime status and 5 armoury passes. The account will then be marked as fully integrated in the database."
    }
  ];

  return (
    <DashboardLayout>
      <PageHeader
        title="New Accounts Process"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />

      <div className="space-y-6 mt-6">
        {steps.map((step, index) => (
          <Card key={step.id} className="border-l-4 border-l-primary">
            <CardContent className="pt-6">
              <div className="flex items-center mb-3">
                <Badge variant="outline" className="mr-3 px-3 py-1">
                  Step {step.id}
                </Badge>
                <h3 className="text-xl font-semibold">{step.title}</h3>
              </div>
              <p className="text-md mb-2">{step.description}</p>
              <p className="text-muted-foreground mb-4">{step.details}</p>
              <Link href={step.link} passHref>
                <Button className="flex items-center">
                  {step.icon}
                  Go to {step.title}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </DashboardLayout>
  );
}
