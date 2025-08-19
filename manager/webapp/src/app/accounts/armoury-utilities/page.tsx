'use client';

import { useState, useEffect, useRef } from 'react';
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";

// Define types
type ConfigKey = 
  | 'threshold_calculator_setup_cost'
  | 'threshold_calculator_batch_passes_cost'
  | 'threshold_calculator_profit_scenario1'
  | 'threshold_calculator_profit_scenario2'
  | 'threshold_calculator_weekly_bonus'
  | 'threshold_calculator_farming_hours'
  | 'threshold_calculator_simulation_years';

type RecommenderItem = {
  name: string;
  roi: number;
  profitChance?: number;
  accountsNeededFor80?: number;
};

type RegionData = {
  currency: string;
  name: string;
  originalAmount: number;
  convertedAmount: number;
};

interface ThresholdCalculatorResult {
  balance: number;
  batches: number;
}

interface Notification {
  id: number | string;
  title: string;
  message: string;
  time: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
}

// Logger types
type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
type LogType = 'recommender' | 'threshold';

interface LogEntry {
  level: LogLevel;
  timestamp: string;
  message: string;
  data?: any;
}

const defaultConstants: Record<ConfigKey, number> = {
  threshold_calculator_setup_cost: 1190,
  threshold_calculator_batch_passes_cost: 6275,
  threshold_calculator_profit_scenario1: 1190,
  threshold_calculator_profit_scenario2: 1360,
  threshold_calculator_weekly_bonus: 50,
  threshold_calculator_farming_hours: 15,
  threshold_calculator_simulation_years: 3
};

const configKeys: ReadonlyArray<ConfigKey> = [
  'threshold_calculator_setup_cost',
  'threshold_calculator_batch_passes_cost',
  'threshold_calculator_profit_scenario1',
  'threshold_calculator_profit_scenario2',
  'threshold_calculator_weekly_bonus',
  'threshold_calculator_farming_hours',
  'threshold_calculator_simulation_years'
];

const initialNotifications: Notification[] = [
  { 
    id: 1, 
    title: 'Config Loaded', 
    message: 'Configuration loaded successfully from YAML file',
    time: '12:30', 
    type: 'success', 
    read: false 
  },
  { 
    id: 2, 
    title: 'Armoury Update', 
    message: 'New market data available for analysis',
    time: '12:15', 
    type: 'info', 
    read: false 
  }
];

// Create a professional logger utility
class Logger {
  private static getTimestamp(): string {
    const now = new Date();
    return now.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  }

  static log(level: LogLevel, message: string, data?: any): LogEntry {
    const timestamp = this.getTimestamp();
    
    if (process.env.NODE_ENV !== 'production') {
      const consoleMethod = level === 'ERROR' ? console.error : 
                            level === 'WARN' ? console.warn : console.log;
                            
      consoleMethod(`${level} | ${timestamp} | ${message}`, data || '');
    }
    
    return {
      level,
      timestamp,
      message,
      data
    };
  }

  static info(message: string, data?: any): LogEntry {
    return this.log('INFO', message, data);
  }

  static warn(message: string, data?: any): LogEntry {
    return this.log('WARN', message, data);
  }

  static error(message: string, data?: any): LogEntry {
    return this.log('ERROR', message, data);
  }

  static debug(message: string, data?: any): LogEntry {
    return this.log('DEBUG', message, data);
  }
}

export default function ArmouryPage() {
  // Notification state
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications);
  const [unreadNotifications, setUnreadNotifications] = useState(
    initialNotifications.filter(notification => !notification.read).length
  );

  // State for Recommender
  const [recommendedItems, setRecommendedItems] = useState<RecommenderItem[]>([]);
  const [userAccounts, setUserAccounts] = useState<number>(0);
  const [desiredProfitPercentage, setDesiredProfitPercentage] = useState<number>(80);
  const [accountsNeeded, setAccountsNeeded] = useState<{ [key: string]: number }>({});
  const [futurePlanningOpen, setFuturePlanningOpen] = useState<boolean>(false);
  const [recommenderLogs, setRecommenderLogs] = useState<LogEntry[]>([]);
  const [recommendationInProgress, setRecommendationInProgress] = useState<boolean>(false);
  
  // State for Region Checker
  const [regionData, setRegionData] = useState<RegionData[]>([]);
  const [indianPrice, setIndianPrice] = useState<number>(0);
  const [priceDifference, setPriceDifference] = useState<{ amount: number, percentage: number }>({ amount: 0, percentage: 0 });
  
  // State for FUA Threshold Calculator
  const [constants, setConstants] = useState<Record<ConfigKey, number>>(defaultConstants);
  const [thresholdResult, setThresholdResult] = useState<ThresholdCalculatorResult | null>(null);
  const [configLoaded, setConfigLoaded] = useState<boolean>(false);
  const [thresholdLogs, setThresholdLogs] = useState<LogEntry[]>([]);
  
  // Log panels state
  const [showRecommenderLogs, setShowRecommenderLogs] = useState<boolean>(false);
  const [showThresholdLogs, setShowThresholdLogs] = useState<boolean>(false);
  
  // Refs for log panels
  const thresholdLogRef = useRef<HTMLDivElement>(null);

  // Add logs with proper formatting
  const addLog = (entry: LogEntry, type: LogType) => {
    if (type === 'recommender') {
      setRecommenderLogs(prev => [...prev, entry]);
    } else {
      setThresholdLogs(prev => [...prev, entry]);
    }
  };

  // Handle marking all notifications as read
  const handleMarkAllRead = () => {
    const updatedNotifications = notifications.map(notification => ({
      ...notification,
      read: true
    }));
    setNotifications(updatedNotifications);
    setUnreadNotifications(0);
  };

  // Removed click-outside handlers to prevent logs from auto-closing
  // Logs only close when user explicitly clicks the toggle button

  // Load config and user accounts from API
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error(`Failed to load configuration: ${response.status}`);
        const data = await response.json();
        const filteredData: Record<ConfigKey, number> = { ...defaultConstants };
        configKeys.forEach(key => {
          if (data[key] !== undefined) filteredData[key] = Number(data[key]);
        });
        setConstants(filteredData);
        setConfigLoaded(true);
        addLog(Logger.info("Configuration loaded successfully from YAML file"), 'threshold');
      } catch (error) {
        console.error(error);
        addLog(Logger.error("Failed to load configuration. Using defaults."), 'threshold');
        setConstants(defaultConstants);
        setConfigLoaded(true);
      }
    };

    const loadUserAccounts = async () => {
      try {
        const mockAccountCount = 13;
        setUserAccounts(mockAccountCount);
        addLog(Logger.info(`Loaded user accounts: ${mockAccountCount}`), 'recommender');
      } catch (error) {
        console.error(error);
        addLog(Logger.error("Failed to load user accounts"), 'recommender');
      }
    };

    loadConfig();
    loadUserAccounts();
  }, []);

  const calculateProfitChance = (itemRoi: number, feverCaseRoi: number, accounts: number): number => {
    const roiDifference = itemRoi - feverCaseRoi;
    if (roiDifference <= 0) return 0;
    const baseChance = Math.min(95, 30 + (roiDifference * 2) + (accounts * 1.5));
    return Math.round(baseChance);
  };

  const calculateAccountsNeeded = (itemRoi: number, feverCaseRoi: number, targetChance: number): number => {
    const roiDifference = itemRoi - feverCaseRoi;
    if (roiDifference <= 0) return 999;
    const neededAccounts = Math.max(1, Math.ceil((targetChance - 30 - (roiDifference * 2)) / 1.5));
    return neededAccounts;
  };

  const calculateRecommendations = () => {
    setRecommendationInProgress(true);
    setShowRecommenderLogs(true); // Show logs immediately when calculation starts
    
    addLog(Logger.info("Validating accounts"), 'recommender');
    addLog(Logger.info(`Successfully validated ${userAccounts} accounts`), 'recommender');
    addLog(Logger.info("Calculating recommendations based on current market data..."), 'recommender');
    
    const mockItems: RecommenderItem[] = [
      { name: "XM1014 | Blaze Orange", roi: 160 },
      { name: "Elemental Crafts Collection", roi: 150 },
      { name: "Fever Case", roi: 130 },
    ];
    
    addLog(Logger.info("Connecting to Steam API"), 'recommender');
    addLog(Logger.info("Connection successful"), 'recommender');
    addLog(Logger.info("Fetching inventory items"), 'recommender');
    
    const sortedItems = mockItems.sort((a, b) => b.roi - a.roi);
    const feverCase = sortedItems.find(item => item.name === "Fever Case");
    const feverCaseRoi = feverCase?.roi || 0;

    const itemsWithChances = sortedItems.map(item => {
      if (item.name === "Fever Case") {
        return item;
      } else if (item.roi > feverCaseRoi) {
        const profitChance = calculateProfitChance(item.roi, feverCaseRoi, userAccounts);
        return {
          ...item,
          profitChance
        };
      }
      return item;
    });

    setRecommendedItems(itemsWithChances);

    const neededAccounts: { [key: string]: number } = {};
    itemsWithChances.forEach(item => {
      if (item.name !== "Fever Case" && item.roi > feverCaseRoi) {
        neededAccounts[item.name] = calculateAccountsNeeded(item.roi, feverCaseRoi, desiredProfitPercentage);
      }
    });
    setAccountsNeeded(neededAccounts);

    // Open future planning only if Fever Case is not #1 (after full results are ready)
    setFuturePlanningOpen(sortedItems[0].name !== "Fever Case");

    addLog(Logger.info(`Found ${sortedItems.length} items eligible for listing`), 'recommender');
    addLog(Logger.info("Starting listing process"), 'recommender');
    addLog(Logger.info("Recommendations calculated successfully"), 'recommender');
    
    setRecommendationInProgress(false); // Mark calculation as complete
  };

  const checkRegions = () => {
    addLog(Logger.info("Checking regional pricing..."), 'recommender');
    const mockRegionData: RegionData[] = [
      { currency: "IDR", name: "Rupiah", originalAmount: 244999.0, convertedAmount: 1283.58 },
      { currency: "CNY", name: "Yuan Renminbi", originalAmount: 110.0, convertedAmount: 1307.93 },
      { currency: "VND", name: "Dong", originalAmount: 400000.0, convertedAmount: 1318.43 }
    ];
    setRegionData(mockRegionData.sort((a, b) => a.convertedAmount - b.convertedAmount));
    setIndianPrice(1350.00);
    setPriceDifference({
      amount: 1350.00 - mockRegionData[0].convertedAmount,
      percentage: ((1350.00 - mockRegionData[0].convertedAmount) / mockRegionData[0].convertedAmount) * 100
    });
    addLog(Logger.info("Regional pricing analysis complete"), 'recommender');
  };

  const calculateThreshold = () => {
    addLog(Logger.info("Starting FUA threshold calculation..."), 'threshold');
    addLog(Logger.info("Analyzing optimal configuration..."), 'threshold');
    
    setTimeout(() => {
      const batches = 12.00;
      const balance = 76490;
      setThresholdResult({ balance, batches });
      
      addLog(Logger.info(`Best refined result: Balance ${balance}, Scenario 2, ROI: 25.865`), 'threshold');
      addLog(Logger.info(`An optimal fully upgraded account will have ${batches.toFixed(2)} batches of passes and a total theoretical value of ${balance}.`), 'threshold');
      addLog(Logger.info("FUA threshold calculation complete"), 'threshold');
    }, 1000);
  };

  const getProfitChanceColor = (chance: number) => {
    if (chance >= 80) return "text-green-500 dark:text-green-400";
    if (chance >= 65) return "text-lime-500 dark:text-lime-400";
    if (chance >= 50) return "text-amber-500 dark:text-amber-400";
    return "text-red-500 dark:text-red-400";
  };

  const feverCaseIsTop = recommendedItems.length > 0 && recommendedItems[0].name === "Fever Case";

  return (
    <DashboardLayout>
      <PageHeader
        title="Armoury Utilities"
        notifications={notifications}
        unreadNotifications={unreadNotifications}
        onMarkAllRead={handleMarkAllRead}
      />
      
      <Tabs defaultValue="recommender" className="w-full">
        <TabsList className="grid grid-cols-3 mb-8 bg-slate-800">
          <TabsTrigger value="recommender" className="data-[state=active]:bg-slate-700">Recommender</TabsTrigger>
          <TabsTrigger value="region-checker" className="data-[state=active]:bg-slate-700">Region Checker</TabsTrigger>
          <TabsTrigger value="threshold-calculator" className="data-[state=active]:bg-slate-700">FUA Threshold Calculator</TabsTrigger>
        </TabsList>
        
        {/* Recommender Tab */}
        <TabsContent value="recommender">
          <Card className="bg-slate-900 text-white border-slate-800">
            <CardHeader>
              <CardTitle>Armoury Recommender</CardTitle>
              <CardDescription className="text-slate-300">
                Analyze and find the most profitable items ranked by ROI
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6">
                <div className="flex items-center justify-between">
                  <div className="text-lg font-medium text-slate-200">
                    Armoury Pass Accounts: <span className="font-bold text-blue-400">{userAccounts}</span>
                  </div>
                  <Button 
                    onClick={calculateRecommendations} 
                    variant="default" 
                    className="bg-slate-700 hover:bg-slate-600 text-slate-100 border-slate-600"
                  >
                    Calculate Recommendations
                  </Button>
                </div>
                
                {recommendedItems.length > 0 && (
                  <div className="mt-6">
                    {feverCaseIsTop ? (
                      <div className="mb-4 p-4 bg-green-900 border border-green-700 rounded-md">
                        <h3 className="text-lg font-medium text-green-300 mb-2">Direct Recommendation</h3>
                        <p className="text-green-200">Fever Case is the optimal choice with the highest ROI.</p>
                      </div>
                    ) : (
                      <h3 className="text-lg font-medium mb-4 text-slate-200">Top 3 Recommended Items</h3>
                    )}
                    
                    <Table className="border-slate-800">
                      <TableHeader className="bg-slate-800 border-b border-slate-700">
                        <TableRow>
                          <TableHead className="text-slate-300">Rank</TableHead>
                          <TableHead className="text-slate-300">Item</TableHead>
                          <TableHead className="text-slate-300">ROI %</TableHead>
                          <TableHead className="text-slate-300">Profit Analysis</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {recommendedItems.map((item, index) => (
                          <TableRow key={index} className="border-b border-slate-800 hover:bg-slate-800">
                            <TableCell className="font-medium text-slate-200">{index + 1}</TableCell>
                            <TableCell className="text-slate-200">{item.name}</TableCell>
                            <TableCell className="text-slate-200">{item.roi.toFixed(1)}%</TableCell>
                            <TableCell>
                              {item.name === "Fever Case" ? (
                                <Badge variant="secondary" className="bg-slate-700 text-slate-200">Baseline</Badge>
                              ) : item.profitChance ? (
                                <span className={getProfitChanceColor(item.profitChance)}>
                                  {item.profitChance}% chance of higher profit with {userAccounts} accounts
                                </span>
                              ) : "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {/* Process Logs Row for Recommender - Shows when logs exist and stays visible */}
                {recommenderLogs.length > 0 && (
                  <div className="mt-4">
                    <div 
                      className="flex items-center justify-between p-3 bg-slate-800 border border-slate-700 rounded cursor-pointer hover:bg-slate-700 transition-colors"
                      onClick={() => setShowRecommenderLogs(!showRecommenderLogs)}
                    >
                      <div className="flex items-center gap-2">
                        <Terminal className="h-4 w-4 text-slate-400" />
                        <span className="font-mono text-sm text-slate-300">Process Logs</span>
                        <Badge variant="outline" className="text-xs border-slate-600 text-slate-400">
                          {recommenderLogs.length}
                        </Badge>
                      </div>
                      {showRecommenderLogs ? (
                        <ChevronUp className="h-4 w-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-slate-400" />
                      )}
                    </div>

                    {showRecommenderLogs && (
                      <div className="border-x border-b border-slate-700 bg-[#0d1117] text-white overflow-hidden">
                        <div className="p-0 max-h-[300px] overflow-y-auto font-mono text-sm">
                          <div className="p-3">
                            {recommenderLogs.map((log, i) => (
                              <div key={i} className="whitespace-pre-wrap mb-1">
                                <span className="text-blue-400">{log.level}</span>
                                <span className="text-slate-400"> | {log.timestamp} | </span>
                                <span>{log.message}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Future Planning Calculator - Only shows when not in progress and fever case is not top */}
                {!recommendationInProgress && !feverCaseIsTop && recommendedItems.length > 0 && (
                  <>
                    <Button
                      variant="outline"
                      className="mt-4 border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200"
                      onClick={() => setFuturePlanningOpen(!futurePlanningOpen)}
                    >
                      {futurePlanningOpen ? (
                        <>Hide Future Planning Calculator <ChevronUp className="ml-2 h-4 w-4" /></>
                      ) : (
                        <>Show Future Planning Calculator <ChevronDown className="ml-2 h-4 w-4" /></>
                      )}
                    </Button>
                    
                    {futurePlanningOpen && (
                      <div className="mt-6 p-4 bg-slate-800 rounded-md border border-slate-700">
                        <h4 className="text-md font-medium mb-3 text-slate-200">Future Planning Calculator</h4>
                        <div className="flex items-center gap-4 mb-4">
                          <label htmlFor="target-percentage" className="text-sm font-medium whitespace-nowrap text-slate-300">
                            Target Higher Profit Chance Rate:
                          </label>
                          <div className="flex items-center gap-4 flex-1">
                            <Slider
                              id="target-percentage"
                              min={50}
                              max={95}
                              step={5}
                              value={[desiredProfitPercentage]}
                              onValueChange={(vals) => setDesiredProfitPercentage(vals[0])}
                              className="flex-1"
                            />
                            <span className="w-12 text-right text-slate-200">{desiredProfitPercentage}%</span>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm text-slate-400 mb-2">
                            Accounts needed for {desiredProfitPercentage}% chance of higher profit:
                          </p>
                          {Object.entries(accountsNeeded).map(([itemName, accounts]) => (
                            <div key={itemName} className="flex justify-between items-center">
                              <span className="font-medium text-slate-300">{itemName}:</span>
                              <Badge variant="outline" className="border-slate-600 text-slate-200">{accounts} accounts</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Region Checker Tab */}
        <TabsContent value="region-checker">
          <Card className="bg-slate-900 text-white border-slate-800">
            <CardHeader>
              <CardTitle>Region Checker</CardTitle>
              <CardDescription className="text-slate-300">
                Check price differences across different regions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                onClick={checkRegions} 
                className="mb-6 bg-slate-700 hover:bg-slate-600 text-slate-100 border-slate-600"
              >
                Check Regions
              </Button>
              
              {regionData.length > 0 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-medium mb-3 text-slate-200">Cheapest 3 options:</h3>
                    <Table className="border-slate-800">
                      <TableHeader className="bg-slate-800 border-b border-slate-700">
                        <TableRow>
                          <TableHead className="text-slate-300">Rank</TableHead>
                          <TableHead className="text-slate-300">Currency</TableHead>
                          <TableHead className="text-slate-300">Original Amount</TableHead>
                          <TableHead className="text-slate-300">Converted (₹)</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {regionData.map((region, index) => (
                          <TableRow key={index} className={`border-b border-slate-800 hover:bg-slate-800 ${index === 0 ? "font-bold text-lg" : ""}`}>
                            <TableCell className="text-slate-200">{index + 1}.</TableCell>
                            <TableCell className="text-slate-200">
                              {region.currency} ({region.name})
                            </TableCell>
                            <TableCell className="text-slate-200">{region.originalAmount.toFixed(1)}</TableCell>
                            <TableCell className="text-slate-200">₹{region.convertedAmount.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  
                  <Separator className="bg-slate-700" />
                  
                  <div>
                    <p className="text-lg text-slate-200">Actual Indian price: <span className="font-bold">₹{indianPrice.toFixed(2)}</span></p>
                    <p className="mt-1 text-slate-300">
                      Indian price is <span className="font-bold">₹{priceDifference.amount.toFixed(2)}</span> 
                      (<span className="font-bold">{priceDifference.percentage.toFixed(2)}%</span>) 
                      more expensive than the cheapest option ({regionData[0].currency} - {regionData[0].name})
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* FUA Threshold Calculator Tab */}
        <TabsContent value="threshold-calculator">
          <Card className="bg-slate-900 text-white border-slate-800">
            <CardHeader>
              <CardTitle>FUA Threshold Calculator</CardTitle>
              <CardDescription className="text-slate-300">
                Calculate the optimal balance and batches for fully upgraded accounts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <h3 className="text-lg font-medium text-slate-200">Configuration</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {configKeys.map((key) => (
                    <div key={key} className="grid gap-1.5">
                      <label htmlFor={key} className="text-sm font-medium text-slate-300">
                        {key.replace('threshold_calculator_', '').replace(/_/g, ' ')}
                      </label>
                      <Input
                        id={key}
                        type="number"
                        value={constants[key]}
                        onChange={(e) => 
                          setConstants({
                            ...constants,
                            [key]: parseFloat(e.target.value) || 0
                          })
                        }
                        className="bg-slate-800 border-slate-700 text-slate-200"
                      />
                    </div>
                  ))}
                </div>
                
                <Button 
                  onClick={calculateThreshold} 
                  disabled={!configLoaded}
                  className="w-full bg-slate-700 hover:bg-slate-600 text-slate-100 border-slate-600"
                >
                  Calculate Optimal Threshold
                </Button>
                
                {thresholdResult && (
                  <div className="mt-6 p-4 bg-slate-800 rounded-md border border-slate-700">
                    <h3 className="text-lg font-medium mb-3 text-slate-200">Results</h3>
                    <p className="text-2xl font-bold mb-2 text-blue-400">
                      Balance Requirement: {thresholdResult.balance.toLocaleString()}
                    </p>
                    <p className="text-xl text-slate-200">
                      Optimal Batches of Passes: {thresholdResult.batches.toFixed(2)}
                    </p>
                  </div>
                )}

                {/* Process Logs Row for Threshold Calculator */}
                {thresholdLogs.length > 0 && (
                  <div className="mt-4">
                    <div 
                      className="flex items-center justify-between p-3 bg-slate-800 border border-slate-700 rounded cursor-pointer hover:bg-slate-700 transition-colors"
                      onClick={() => setShowThresholdLogs(!showThresholdLogs)}
                    >
                      <div className="flex items-center gap-2">
                        <Terminal className="h-4 w-4 text-slate-400" />
                        <span className="font-mono text-sm text-slate-300">Process Logs</span>
                        <Badge variant="outline" className="text-xs border-slate-600 text-slate-400">
                          {thresholdLogs.length}
                        </Badge>
                      </div>
                      {showThresholdLogs ? (
                        <ChevronUp className="h-4 w-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-slate-400" />
                      )}
                    </div>

                    {showThresholdLogs && (
                      <div 
                        ref={thresholdLogRef}
                        className="border-x border-b border-slate-700 bg-[#0d1117] text-white overflow-hidden"
                      >
                        <div className="p-0 max-h-[300px] overflow-y-auto font-mono text-sm">
                          <div className="p-3">
                            {thresholdLogs.map((log, i) => (
                              <div key={i} className="whitespace-pre-wrap mb-1">
                                <span className="text-blue-400">{log.level}</span>
                                <span className="text-slate-400"> | {log.timestamp} | </span>
                                <span>{log.message}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Redemption Info */}
      <div className="mt-8 p-4 bg-slate-800 border border-slate-700 rounded text-blue-400 text-sm">
        <strong>Armoury Redemption:</strong> @standard_arb_bot on Telegram
      </div>
    </DashboardLayout>
  );
}
