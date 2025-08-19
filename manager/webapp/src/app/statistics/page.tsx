"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { DashboardLayout } from "@/components/dashboardlayout";
import { PageHeader } from "@/components/pageheader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Maximize2, Minimize2, ArrowLeft, ArrowRight } from "lucide-react";
import {
    LineChart, Line, BarChart, Bar, AreaChart, Area,
    XAxis, YAxis, ResponsiveContainer, Tooltip, Legend
} from "recharts";
import { 
  ChartConfig,
} from "@/components/ui/chart";

// Interfaces
interface ExpenseData {
  date: string;
  crypto: number;
  inr: number;
  giftcards: number;
  timestamp: number;
}

interface MarketCsgoData {
  date: string;
  usdt: number;
  inrEquivalent: number;
  timestamp: number;
}

interface ArmouryData {
  time: string;
  item1Profit: number;
  item2Profit: number;
  item3Profit: number;
  timestamp: number;
}

interface CsfloatData {
  date: string;
  inrAmount: number;
  timestamp: number;
}

interface PassesData {
  week: string;
  passes: number;
  timestamp: number;
}

interface CompletionTimeData {
  date: string;
  avgMinutes: number;
  timestamp: number;
}

interface SteamProfitData {
    week: string;
    profit: number;
    timestamp: number;
}

interface DateRange {
  label: string;
  days: number | null;
}

interface HoverTooltip {
  visible: boolean;
  x: number;
  date: string;
}

// Pre-computed data slice interface
interface PreComputedSlices<T> {
  [key: string]: T[];
}

// Global date range options
const dateRanges: DateRange[] = [
  { label: 'Last Week', days: 7 },
  { label: 'Last Month', days: 30 },
  { label: 'Last 3 Months', days: 90 },
  { label: 'Last 6 Months', days: 180 },
  { label: 'Last 12 Months', days: 365 },
  { label: 'All Time', days: null },
];

// Chart configs
const expensesChartConfig: ChartConfig = {
  crypto: { label: "Crypto", color: "#4f46e5" },
  inr: { label: "INR", color: "#10b981" },
  giftcards: { label: "Gift Cards", color: "#f59e0b" }
};

const marketCsgoChartConfig: ChartConfig = {
  usdt: { label: "USDT", color: "#06b6d4" },
  inrEquivalent: { label: "INR Equivalent", color: "#8b5cf6" }
};

const armouryChartConfig: ChartConfig = {
  item1Profit: { label: "AK-47 | Asiimov", color: "#ef4444" },
  item2Profit: { label: "M4A4 | Neo-Noir", color: "#ec4899" },
  item3Profit: { label: "AWP | Containment Breach", color: "#8b5cf6" }
};

const csfloatChartConfig: ChartConfig = {
  inrAmount: { label: "INR Withdrawn", color: "#3b82f6" }
};

const passesChartConfig: ChartConfig = {
  passes: { label: "Passes Farmed", color: "#84cc16" }
};

const steamProfitChartConfig: ChartConfig = {
  profit: { label: "Profit (INR)", color: "#f43f5e" }
};

const completionTimeChartConfig: ChartConfig = {
  avgMinutes: { label: "Completion Time", color: "#14b8a6" }
};

// Format time from minutes to hours and minutes
const formatTime = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const mins = Math.floor(minutes % 60);
  return `${hours}h ${mins}m`;
};

// Generate dynamic date markers based on global date range selection
const generateDynamicDateMarkers = <T extends { timestamp: number }>(
  data: T[], 
  globalDateRange: DateRange
): Array<{position: number, label: string}> => {
  if (data.length === 0) return [];
  
  const now = Date.now();
  const markers: Array<{position: number, label: string}> = [];
  
  // For "All Time", use the full dataset range
  if (globalDateRange.days === null) {
    const timestamps = data.map(d => d.timestamp);
    const startTime = Math.min(...timestamps);
    const endTime = Math.max(...timestamps);
    const timeDiff = endTime - startTime;
    const days = timeDiff / (24 * 60 * 60 * 1000);
    
    let format: Intl.DateTimeFormatOptions;
    let intervalCount: number;
    
    if (days <= 7) {
      format = { month: 'short', day: 'numeric' };
      intervalCount = Math.min(4, Math.floor(days));
    } else if (days <= 90) {
      format = { month: 'short', day: 'numeric' };
      intervalCount = 4;
    } else if (days <= 365) {
      format = { month: 'short', year: '2-digit' };
      intervalCount = 5;
    } else {
      format = { year: 'numeric' };
      intervalCount = 4;
    }
    
    markers.push({
      position: 0,
      label: new Date(startTime).toLocaleDateString('en-US', format)
    });
    
    for (let i = 1; i < intervalCount; i++) {
      const position = (i / intervalCount) * 100;
      const time = startTime + (timeDiff * i / intervalCount);
      markers.push({
        position,
        label: new Date(time).toLocaleDateString('en-US', format)
      });
    }
    
    markers.push({
      position: 100,
      label: new Date(endTime).toLocaleDateString('en-US', format)
    });
    
    return markers;
  }
  
  // For specific time ranges, generate markers based on current date
  const rangeStartTime = now - (globalDateRange.days * 24 * 60 * 60 * 1000);
  
  switch (globalDateRange.label) {
    case 'Last Week': {
      // Show last 7 days
      for (let i = 0; i <= 6; i++) {
        const dayTime = rangeStartTime + (i * 24 * 60 * 60 * 1000);
        const position = (i / 6) * 100;
        markers.push({
          position,
          label: new Date(dayTime).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        });
      }
      break;
    }
    
    case 'Last Month': {
      // Show dates throughout the month (like 1st, 8th, 15th, 22nd, 29th)
      const daysInRange = 30;
      const intervals = [0, 7, 14, 21, 28, 30]; // Roughly weekly intervals
      
      intervals.forEach((dayOffset, index) => {
        const dayTime = rangeStartTime + (dayOffset * 24 * 60 * 60 * 1000);
        const position = (dayOffset / daysInRange) * 100;
        markers.push({
          position,
          label: new Date(dayTime).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        });
      });
      break;
    }
    
    case 'Last 3 Months': {
      // Show weeks over the last 3 months
      const weeksCount = 12; // Roughly 12 weeks in 3 months
      for (let week = 0; week <= weeksCount; week += 2) { // Every 2 weeks
        const weekTime = rangeStartTime + (week * 7 * 24 * 60 * 60 * 1000);
        const position = (week / weeksCount) * 100;
        markers.push({
          position,
          label: new Date(weekTime).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        });
      }
      break;
    }
    
    case 'Last 6 Months': {
      // Show months over the last 6 months
      for (let month = 0; month <= 6; month++) {
        const monthTime = rangeStartTime + (month * 30 * 24 * 60 * 60 * 1000);
        const position = (month / 6) * 100;
        markers.push({
          position,
          label: new Date(monthTime).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
        });
      }
      break;
    }
    
    case 'Last 12 Months': {
      // Show months over the last 12 months
      for (let month = 0; month <= 12; month += 2) { // Every 2 months
        const monthTime = rangeStartTime + (month * 30 * 24 * 60 * 60 * 1000);
        const position = (month / 12) * 100;
        markers.push({
          position,
          label: new Date(monthTime).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
        });
      }
      break;
    }
    
    default:
      break;
  }
  
  return markers;
};

// Enhanced slider component with hover tooltip and much larger click zone
const EnhancedSlider: React.FC<{
  value: [number, number];
  onChange: (value: [number, number]) => void;
  data: Array<{ timestamp: number }>;
  globalDateRange: DateRange;
  className?: string;
}> = ({ value, onChange, data, globalDateRange, className = "" }) => {
  const sliderRef = useRef<HTMLDivElement>(null);
  const clickZoneRef = useRef<HTMLDivElement>(null);
  const [hoverTooltip, setHoverTooltip] = useState<HoverTooltip>({
    visible: false,
    x: 0,
    date: ''
  });

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!clickZoneRef.current || data.length === 0) return;
    
    const rect = clickZoneRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    
    // Calculate the date at this position based on global date range
    let startTime: number, endTime: number;
    
    if (globalDateRange.days === null) {
      // All time - use dataset range
      const timestamps = data.map(d => d.timestamp);
      startTime = Math.min(...timestamps);
      endTime = Math.max(...timestamps);
    } else {
      // Specific range - use current date range
      const now = Date.now();
      startTime = now - (globalDateRange.days * 24 * 60 * 60 * 1000);
      endTime = now;
    }
    
    const targetTime = startTime + ((endTime - startTime) * percentage / 100);
    
    setHoverTooltip({
      visible: true,
      x: x,
      date: new Date(targetTime).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    });
  }, [data, globalDateRange]);

  const handleMouseLeave = useCallback(() => {
    setHoverTooltip(prev => ({ ...prev, visible: false }));
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (!clickZoneRef.current || data.length === 0) return;
    
    const rect = clickZoneRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    
    // Determine which handle is closer
    const [start, end] = value;
    const distToStart = Math.abs(percentage - start);
    const distToEnd = Math.abs(percentage - end);
    
    if (distToStart < distToEnd) {
      // Move start handle
      onChange([Math.min(percentage, end - 1), end]);
    } else {
      // Move end handle
      onChange([start, Math.max(percentage, start + 1)]);
    }
  }, [value, onChange, data]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!clickZoneRef.current) return;
    
    const rect = clickZoneRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    
    // Determine which handle is closer
    const [start, end] = value;
    const distToStart = Math.abs(percentage - start);
    const distToEnd = Math.abs(percentage - end);
    
    let isDragging = true;
    const isStartHandle = distToStart < distToEnd;
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!isDragging || !clickZoneRef.current) return;
      
      const rect = clickZoneRef.current.getBoundingClientRect();
      const x = moveEvent.clientX - rect.left;
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
      
      if (isStartHandle) {
        onChange([Math.min(percentage, end - 1), end]);
      } else {
        onChange([start, Math.max(percentage, start + 1)]);
      }
    };
    
    const handleMouseUp = () => {
      isDragging = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [value, onChange]);

  return (
    <div className="relative">
      {/* Large invisible click zone with embedded date markers */}
      <div 
        ref={clickZoneRef}
        className={`relative cursor-pointer ${className}`}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        style={{ 
          padding: '40px 0', // Larger vertical click zone
          marginTop: '-20px', 
          marginBottom: '-20px'
        }}
      >
        {/* Date markers embedded within the top padding */}
        <div className="absolute top-2 left-0 right-0 pointer-events-none">
          {generateDynamicDateMarkers(data, globalDateRange).map((marker, index) => (
            <div
              key={index}
              className="absolute text-xs text-gray-400 transform -translate-x-1/2 select-none"
              style={{ left: `${marker.position}%` }}
            >
              {marker.label}
            </div>
          ))}
        </div>

        {/* Actual slider container */}
        <div 
          ref={sliderRef}
          className="relative"
          style={{ 
            marginTop: '20px',
            marginBottom: '20px',
            pointerEvents: 'none'
          }}
        >
          <Slider
            value={value}
            min={0}
            max={100}
            step={1}
            onValueChange={onChange}
            className="slider-enhanced"
          />
        </div>
        
        {/* Hover tooltip */}
        {hoverTooltip.visible && (
          <div
            className="absolute pointer-events-none z-10 bg-gray-800 text-white text-xs px-2 py-1 rounded shadow-lg border border-gray-600"
            style={{
              left: `${hoverTooltip.x}px`,
              top: '-80px',
              transform: 'translateX(-50%)'
            }}
          >
            {hoverTooltip.date}
          </div>
        )}
      </div>
    </div>
  );
};

// RAF Throttle Hook - Much better than debounce for sliders
const useRAFThrottle = (callback: Function) => {
  const rafRef = useRef<number | undefined>(undefined);
  
  return useCallback((...args: any[]) => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }
    rafRef.current = requestAnimationFrame(() => {
      callback(...args);
    });
  }, [callback]);
};

// Pre-compute data slices for performance
const preComputeDataSlices = <T extends { timestamp: number }>(
  data: T[], 
  steps: number = 10
): PreComputedSlices<T> => {
  if (data.length === 0) return {};
  
  const slices: PreComputedSlices<T> = {};
  const minTime = Math.min(...data.map(d => d.timestamp));
  const maxTime = Math.max(...data.map(d => d.timestamp));
  
  for (let start = 0; start <= 100; start += steps) {
    for (let end = start + steps; end <= 100; end += steps) {
      const rangeMinTime = minTime + ((maxTime - minTime) * start / 100);
      const rangeMaxTime = minTime + ((maxTime - minTime) * end / 100);
      
      const filteredData = data.filter(item => 
        item.timestamp >= rangeMinTime && item.timestamp <= rangeMaxTime
      );
      
      slices[`${start}-${end}`] = filteredData;
    }
  }
  
  return slices;
};

// Get data slice with caching
const getDataSlice = <T extends { timestamp: number }>(
  data: T[],
  preComputedSlices: PreComputedSlices<T>,
  range: [number, number],
  steps: number = 10
): T[] => {
  const startRounded = Math.floor(range[0] / steps) * steps;
  const endRounded = Math.ceil(range[1] / steps) * steps;
  
  const sliceKey = `${startRounded}-${Math.min(endRounded, 100)}`;
  
  if (preComputedSlices[sliceKey]) {
    const baseSlice = preComputedSlices[sliceKey];
    if (startRounded === range[0] && endRounded === range[1]) {
      return baseSlice;
    }
    
    if (baseSlice.length === 0) return [];
    
    const minTime = Math.min(...baseSlice.map(d => d.timestamp));
    const maxTime = Math.max(...baseSlice.map(d => d.timestamp));
    const rangeMinTime = minTime + ((maxTime - minTime) * (range[0] - startRounded) / (endRounded - startRounded));
    const rangeMaxTime = minTime + ((maxTime - minTime) * (range[1] - startRounded) / (endRounded - startRounded));
    
    return baseSlice.filter(item => 
      item.timestamp >= rangeMinTime && item.timestamp <= rangeMaxTime
    );
  }
  
  if (data.length === 0) return [];
  const minTime = Math.min(...data.map(d => d.timestamp));
  const maxTime = Math.max(...data.map(d => d.timestamp));
  const rangeMinTime = minTime + ((maxTime - minTime) * range[0] / 100);
  const rangeMaxTime = minTime + ((maxTime - minTime) * range[1] / 100);
  
  return data.filter(item => item.timestamp >= rangeMinTime && item.timestamp <= rangeMaxTime);
};

// Helper to filter data by global date range
const filterDataByGlobalRange = <T extends { timestamp: number }>(
  data: T[], 
  globalRange: DateRange
): T[] => {
  if (globalRange.days === null) return data;
  
  const now = Date.now();
  const cutoffTime = now - (globalRange.days * 24 * 60 * 60 * 1000);
  return data.filter(item => item.timestamp >= cutoffTime);
};

// Memoized Chart Components to prevent unnecessary re-renders - ALL ANIMATIONS DISABLED
const ExpensesChart = React.memo(({ data, includeGiftCards }: { data: ExpenseData[], includeGiftCards: boolean }) => (
  <ResponsiveContainer width="100%" height="100%">
    <AreaChart data={data}>
      <XAxis dataKey="date" tick={{ fill: '#f0f0f0' }} />
      <YAxis tick={{ fill: '#f0f0f0' }} />
      <Tooltip 
        formatter={(value, name) => [`₹${value}`, name]} 
        labelFormatter={(label) => `Date: ${label}`} 
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Area 
        type="monotone" 
        dataKey="crypto" 
        stroke={expensesChartConfig.crypto.color} 
        fill={`${expensesChartConfig.crypto.color}40`} 
        name="Crypto" 
        stackId="1"
        isAnimationActive={false}
      />
      <Area 
        type="monotone" 
        dataKey="inr" 
        stroke={expensesChartConfig.inr.color} 
        fill={`${expensesChartConfig.inr.color}40`} 
        name="INR" 
        stackId="1"
        isAnimationActive={false}
      />
      {includeGiftCards && (
        <Area 
          type="monotone" 
          dataKey="giftcards" 
          stroke={expensesChartConfig.giftcards.color} 
          fill={`${expensesChartConfig.giftcards.color}40`} 
          name="Gift Cards" 
          stackId="1"
          isAnimationActive={false}
        />
      )}
    </AreaChart>
  </ResponsiveContainer>
));

const SteamProfitChart = React.memo(({ data }: { data: SteamProfitData[] }) => (
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="week" tick={{ fill: '#f0f0f0' }} />
      <YAxis domain={['auto', 'auto']} tick={{ fill: '#f0f0f0' }} />
      <Tooltip 
        formatter={(value, name) => [`₹${value}`, name]} 
        labelFormatter={(label) => `Week of ${label}`} 
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Line 
        type="monotone" 
        dataKey="profit" 
        stroke={steamProfitChartConfig.profit.color} 
        dot={false} 
        name="Profit (INR)"
        isAnimationActive={false}
      />
    </LineChart>
  </ResponsiveContainer>
));

const ArmouryChart = React.memo(({ data }: { data: ArmouryData[] }) => (
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="time" tick={{ fill: '#f0f0f0' }} />
      <YAxis tick={{ fill: '#f0f0f0' }} />
      <Tooltip 
        formatter={(value, name) => [`${value}%`, name]} 
        labelFormatter={(label) => `Date: ${label}`} 
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Line 
        type="monotone" 
        dataKey="item1Profit" 
        stroke={armouryChartConfig.item1Profit.color} 
        name="AK-47 | Asiimov" 
        dot={false}
        isAnimationActive={false}
      />
      <Line 
        type="monotone" 
        dataKey="item2Profit" 
        stroke={armouryChartConfig.item2Profit.color} 
        name="M4A4 | Neo-Noir" 
        dot={false}
        isAnimationActive={false}
      />
      <Line 
        type="monotone" 
        dataKey="item3Profit" 
        stroke={armouryChartConfig.item3Profit.color} 
        name="AWP | Containment Breach" 
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  </ResponsiveContainer>
));

const PassesChart = React.memo(({ data }: { data: PassesData[] }) => (
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="week" tick={{ fill: '#f0f0f0' }} />
      <YAxis tick={{ fill: '#f0f0f0' }} />
      <Tooltip 
        formatter={(value, name) => [value, name]} 
        labelFormatter={(label) => `Week: ${label}`} 
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Line 
        type="monotone" 
        dataKey="passes" 
        stroke={passesChartConfig.passes.color} 
        name="Passes Farmed" 
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  </ResponsiveContainer>
));

const CompletionTimeChart = React.memo(({ data }: { data: CompletionTimeData[] }) => (
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="date" tick={{ fill: '#f0f0f0' }} />
      <YAxis tick={{ fill: '#f0f0f0' }} />
      <Tooltip 
        formatter={(value, name) => [formatTime(Number(value)), name]} 
        labelFormatter={(label) => `Date: ${label}`} 
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Line 
        type="monotone" 
        dataKey="avgMinutes" 
        stroke={completionTimeChartConfig.avgMinutes.color} 
        name="Completion Time" 
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  </ResponsiveContainer>
));

const CsfloatChart = React.memo(({ data }: { data: CsfloatData[] }) => (
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="date" tick={{ fill: '#f0f0f0' }} />
      <YAxis tick={{ fill: '#f0f0f0' }} />
      <Tooltip 
        formatter={(value, name) => [`₹${value}`, name]} 
        labelFormatter={(label) => `Date: ${label}`} 
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Line 
        type="monotone" 
        dataKey="inrAmount" 
        stroke={csfloatChartConfig.inrAmount.color} 
        dot={false} 
        name="INR Withdrawn"
        isAnimationActive={false}
      />
    </LineChart>
  </ResponsiveContainer>
));

const MarketCsgoChart = React.memo(({ data }: { data: MarketCsgoData[] }) => (
  <ResponsiveContainer width="100%" height="100%">
    <LineChart data={data}>
      <XAxis dataKey="date" tick={{ fill: '#f0f0f0' }} />
      <YAxis tick={{ fill: '#f0f0f0' }} />
      <Tooltip
        formatter={(value, name, { payload }) => {
          if (name === "USDT") {
            return [`$${value} (₹${payload.inrEquivalent})`, name];
          }
          return [`$${value}`, name];
        }}
        labelFormatter={(label) => `Date: ${label}`}
        contentStyle={{ backgroundColor: "rgba(33, 33, 33, 0.9)", color: "#f0f0f0", border: "1px solid #555" }}
        animationDuration={0}
      />
      <Legend />
      <Line 
        type="monotone" 
        dataKey="usdt" 
        stroke={marketCsgoChartConfig.usdt.color} 
        name="USDT" 
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  </ResponsiveContainer>
));

export default function StatisticsPage() {
  // Chart with slider component
  function ChartWithSlider({
    chart,
    data,
    range,
    onRangeChange,
    poppedOut,
    maximized,
    heightNormal = 300,
    heightPopped = 450,
    heightMaximized = 600,
  }: {
    chart: React.ReactNode;
    data: Array<{ timestamp: number }>;
    range: [number, number];
    onRangeChange: (range: [number, number]) => void;
    poppedOut: boolean;
    maximized: boolean;
    heightNormal?: number;
    heightPopped?: number;
    heightMaximized?: number;
  }) {
    const getHeight = () => {
      if (maximized) return heightMaximized;
      if (poppedOut) return heightPopped;
      return heightNormal;
    };

    const getMarginTop = () => {
      if (maximized) return "mt-8";
      if (poppedOut) return "mt-4";
      return "mt-2";
    };

    return (
      <div>
        <div 
          className="w-full" 
          style={{ height: `${getHeight()}px` }}
        >
          {chart}
        </div>
        <div className={getMarginTop()}>
          <EnhancedSlider
            value={range}
            onChange={onRangeChange}
            data={data}
            globalDateRange={globalDateRange}
            className="my-2"
          />
        </div>
      </div>
    );
  }
  
  // Global date range selection
  const [globalDateRange, setGlobalDateRange] = useState<DateRange>(dateRanges[5]);
  
  // Toggle for gift cards
  const [includeGiftCards, setIncludeGiftCards] = useState<boolean>(true);
  
  // Loading state
  const [loading, setLoading] = useState<boolean>(true);
  
  // Data states
  const [expensesData, setExpensesData] = useState<ExpenseData[]>([]);
  const [marketCsgoData, setMarketCsgoData] = useState<MarketCsgoData[]>([]);
  const [armouryData, setArmouryData] = useState<ArmouryData[]>([]);
  const [csfloatData, setCsfloatData] = useState<CsfloatData[]>([]);
  const [passesData, setPassesData] = useState<PassesData[]>([]);
  const [steamProfitData, setSteamProfitData] = useState<SteamProfitData[]>([]);
  const [completionTimeData, setCompletionTimeData] = useState<CompletionTimeData[]>([]);
  
  // Pre-computed slices
  const [preComputedSlices, setPreComputedSlices] = useState<{
    expenses: PreComputedSlices<ExpenseData>;
    marketCsgo: PreComputedSlices<MarketCsgoData>;
    armoury: PreComputedSlices<ArmouryData>;
    csfloat: PreComputedSlices<CsfloatData>;
    passes: PreComputedSlices<PassesData>;
    steamProfit: PreComputedSlices<SteamProfitData>;
    completionTime: PreComputedSlices<CompletionTimeData>;
  }>({
    expenses: {},
    marketCsgo: {},
    armoury: {},
    csfloat: {},
    passes: {},
    steamProfit: {},
    completionTime: {}
  });
  
  // Individual chart range sliders - each isolated
  const [expensesRange, setExpensesRange] = useState<[number, number]>([0, 100]);
  const [marketCsgoRange, setMarketCsgoRange] = useState<[number, number]>([0, 100]);
  const [armouryRange, setArmouryRange] = useState<[number, number]>([0, 100]);
  const [csfloatRange, setCsfloatRange] = useState<[number, number]>([0, 100]);
  const [passesRange, setPassesRange] = useState<[number, number]>([0, 100]);
  const [steamProfitRange, setSteamProfitRange] = useState<[number, number]>([0, 100]);
  const [completionTimeRange, setCompletionTimeRange] = useState<[number, number]>([0, 100]);
  
  // RAF throttled update functions - isolated per chart
  const throttledExpensesUpdate = useRAFThrottle(setExpensesRange);
  const throttledMarketCsgoUpdate = useRAFThrottle(setMarketCsgoRange);
  const throttledArmouryUpdate = useRAFThrottle(setArmouryRange);
  const throttledCsfloatUpdate = useRAFThrottle(setCsfloatRange);
  const throttledPassesUpdate = useRAFThrottle(setPassesRange);
  const throttledSteamProfitUpdate = useRAFThrottle(setSteamProfitRange);
  const throttledCompletionTimeUpdate = useRAFThrottle(setCompletionTimeRange);
  
  // Pop-out and maximize states
  const [poppedOutGraphs, setPoppedOutGraphs] = useState<string[]>([]);
  const [maximized, setMaximized] = useState<boolean>(false);
  const [maximizedGraph, setMaximizedGraph] = useState<string | null>(null);
  
  // Memoized global filtered data - use original data for static markers when "All Time" is selected
  const globalFilteredData = useMemo(() => {
    // For static date markers, always use full dataset
    const baseData = {
      expenses: expensesData,
      marketCsgo: marketCsgoData,
      armoury: armouryData,
      csfloat: csfloatData,
      passes: passesData,
      steamProfit: steamProfitData,
      completionTime: completionTimeData
    };
    
    // For chart data, apply global filter
    const filtered = {
      expenses: filterDataByGlobalRange(expensesData, globalDateRange),
      marketCsgo: filterDataByGlobalRange(marketCsgoData, globalDateRange),
      armoury: filterDataByGlobalRange(armouryData, globalDateRange),
      csfloat: filterDataByGlobalRange(csfloatData, globalDateRange),
      passes: filterDataByGlobalRange(passesData, globalDateRange),
      steamProfit: filterDataByGlobalRange(steamProfitData, globalDateRange),
      completionTime: filterDataByGlobalRange(completionTimeData, globalDateRange)
    };
    
    return { base: baseData, filtered };
  }, [
    expensesData, marketCsgoData, armouryData, csfloatData, 
    passesData, steamProfitData, completionTimeData, globalDateRange
  ]);
  
  // Pre-compute slices when data changes
  useEffect(() => {
    if (loading) return;
    
    const newSlices = {
      expenses: preComputeDataSlices(globalFilteredData.filtered.expenses),
      marketCsgo: preComputeDataSlices(globalFilteredData.filtered.marketCsgo),
      armoury: preComputeDataSlices(globalFilteredData.filtered.armoury),
      csfloat: preComputeDataSlices(globalFilteredData.filtered.csfloat),
      passes: preComputeDataSlices(globalFilteredData.filtered.passes),
      steamProfit: preComputeDataSlices(globalFilteredData.filtered.steamProfit),
      completionTime: preComputeDataSlices(globalFilteredData.filtered.completionTime)
    };
    
    setPreComputedSlices(newSlices);
  }, [globalFilteredData, loading]);
  
  // Memoized filtered data - each isolated to prevent cross-renders
  const filteredExpensesData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.expenses, preComputedSlices.expenses, expensesRange),
    [globalFilteredData.filtered.expenses, preComputedSlices.expenses, expensesRange]
  );
  
  const filteredMarketCsgoData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.marketCsgo, preComputedSlices.marketCsgo, marketCsgoRange),
    [globalFilteredData.filtered.marketCsgo, preComputedSlices.marketCsgo, marketCsgoRange]
  );
  
  const filteredArmouryData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.armoury, preComputedSlices.armoury, armouryRange),
    [globalFilteredData.filtered.armoury, preComputedSlices.armoury, armouryRange]
  );
  
  const filteredCsfloatData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.csfloat, preComputedSlices.csfloat, csfloatRange),
    [globalFilteredData.filtered.csfloat, preComputedSlices.csfloat, csfloatRange]
  );
  
  const filteredPassesData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.passes, preComputedSlices.passes, passesRange),
    [globalFilteredData.filtered.passes, preComputedSlices.passes, passesRange]
  );
  
  const filteredCompletionTimeData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.completionTime, preComputedSlices.completionTime, completionTimeRange),
    [globalFilteredData.filtered.completionTime, preComputedSlices.completionTime, completionTimeRange]
  );
  
  const filteredSteamProfitData = useMemo(() => 
    getDataSlice(globalFilteredData.filtered.steamProfit, preComputedSlices.steamProfit, steamProfitRange),
    [globalFilteredData.filtered.steamProfit, preComputedSlices.steamProfit, steamProfitRange]
  );
  
  // Toggle functions
  const togglePopOut = (graphName: string) => {
    setPoppedOutGraphs(prevPopped => {
      if (prevPopped.includes(graphName)) {
        return prevPopped.filter(name => name !== graphName);
      } else {
        return [...prevPopped, graphName];
      }
    });
    
    if (maximized && maximizedGraph === graphName) {
      setMaximized(false);
      setMaximizedGraph(null);
    }
  };
  
  const toggleMaximize = (graphName: string) => {
    if (maximized && maximizedGraph === graphName) {
      setMaximized(false);
      setMaximizedGraph(null);
    } else {
      setMaximized(true);
      setMaximizedGraph(graphName);
      setPoppedOutGraphs(prev => prev.filter(name => name !== graphName));
    }
  };
  
  const isGraphPoppedOut = (graphName: string): boolean => {
    return poppedOutGraphs.includes(graphName);
  };
  
  // Data loading
  useEffect(() => {
    const now = Date.now();
    const day = 24 * 60 * 60 * 1000;
    
    const expensesTemp: ExpenseData[] = [
      { date: '2025-01-01', crypto: 14500, inr: 8200, giftcards: 5300, timestamp: now - 150 * day },
      { date: '2025-02-01', crypto: 16200, inr: 9500, giftcards: 4800, timestamp: now - 120 * day },
      { date: '2025-03-01', crypto: 15400, inr: 7800, giftcards: 5100, timestamp: now - 90 * day },
      { date: '2025-04-01', crypto: 17800, inr: 9200, giftcards: 5500, timestamp: now - 60 * day },
      { date: '2025-05-01', crypto: 19500, inr: 10500, giftcards: 6200, timestamp: now - 30 * day },
    ];
    setExpensesData(expensesTemp);
    
    const marketCsgoTemp: MarketCsgoData[] = [
      { date: '2025-04-22', usdt: 250, inrEquivalent: 20750, timestamp: now - 30 * day },
      { date: '2025-04-29', usdt: 180, inrEquivalent: 14940, timestamp: now - 23 * day },
      { date: '2025-05-06', usdt: 320, inrEquivalent: 26560, timestamp: now - 16 * day },
      { date: '2025-05-13', usdt: 210, inrEquivalent: 17430, timestamp: now - 9 * day },
      { date: '2025-05-20', usdt: 280, inrEquivalent: 23240, timestamp: now - 2 * day },
    ];
    setMarketCsgoData(marketCsgoTemp);
    
    const armouryTemp: ArmouryData[] = [
      { time: '2025-05-18', item1Profit: 5.2, item2Profit: 4.1, item3Profit: 6.3, timestamp: now - 4 * day },
      { time: '2025-05-19', item1Profit: 5.8, item2Profit: 3.9, item3Profit: 6.7, timestamp: now - 3 * day },
      { time: '2025-05-20', item1Profit: 5.5, item2Profit: 4.3, item3Profit: 6.2, timestamp: now - 2 * day },
      { time: '2025-05-21', item1Profit: 5.7, item2Profit: 4.5, item3Profit: 6.5, timestamp: now - 1 * day },
      { time: '2025-05-22', item1Profit: 6.1, item2Profit: 4.8, item3Profit: 6.9, timestamp: now },
    ];
    setArmouryData(armouryTemp);
    
    const csfloatTemp: CsfloatData[] = [
      { date: '2025-04-22', inrAmount: 12500, timestamp: now - 30 * day },
      { date: '2025-04-29', inrAmount: 9800, timestamp: now - 23 * day },
      { date: '2025-05-06', inrAmount: 14200, timestamp: now - 16 * day },
      { date: '2025-05-13', inrAmount: 11500, timestamp: now - 9 * day },
      { date: '2025-05-20', inrAmount: 15800, timestamp: now - 2 * day },
    ];
    setCsfloatData(csfloatTemp);
    
    const passesTemp: PassesData[] = [
      { week: 'Week 1', passes: 45, timestamp: now - 28 * day },
      { week: 'Week 2', passes: 52, timestamp: now - 21 * day },
      { week: 'Week 3', passes: 48, timestamp: now - 14 * day },
      { week: 'Week 4', passes: 56, timestamp: now - 7 * day },
    ];
    setPassesData(passesTemp);
    
    const completionTimeTemp: CompletionTimeData[] = [
      { date: '2025-05-18', avgMinutes: 145, timestamp: now - 4 * day },
      { date: '2025-05-19', avgMinutes: 132, timestamp: now - 3 * day },
      { date: '2025-05-20', avgMinutes: 128, timestamp: now - 2 * day },
      { date: '2025-05-21', avgMinutes: 120, timestamp: now - 1 * day },
      { date: '2025-05-22', avgMinutes: 115, timestamp: now },
    ];
    setCompletionTimeData(completionTimeTemp);
    
    const steamProfitTemp: SteamProfitData[] = [
      { week: 'Jan 8', profit: 6800, timestamp: now - 140 * day },
      { week: 'Jan 15', profit: 6300, timestamp: now - 133 * day },
      { week: 'Jan 22', profit: 7500, timestamp: now - 126 * day },
      { week: 'Jan 29', profit: 7200, timestamp: now - 119 * day },
      { week: 'Feb 5', profit: 8200, timestamp: now - 112 * day },
      { week: 'Feb 12', profit: 6000, timestamp: now - 105 * day },
      { week: 'Feb 19', profit: 9000, timestamp: now - 98 * day },
      { week: 'Feb 26', profit: 7500, timestamp: now - 91 * day },
      { week: 'Mar 5', profit: 8800, timestamp: now - 84 * day },
      { week: 'Mar 12', profit: 6500, timestamp: now - 77 * day },
      { week: 'Mar 19', profit: 9200, timestamp: now - 70 * day },
      { week: 'Mar 26', profit: 8200, timestamp: now - 63 * day },
      { week: 'Apr 2', profit: 7000, timestamp: now - 56 * day },
      { week: 'Apr 9', profit: 9500, timestamp: now - 49 * day },
      { week: 'Apr 16', profit: 8000, timestamp: now - 42 * day },
      { week: 'Apr 23', profit: 9800, timestamp: now - 35 * day },
      { week: 'Apr 30', profit: 9200, timestamp: now - 28 * day },
      { week: 'May 7', profit: 10200, timestamp: now - 21 * day },
      { week: 'May 14', profit: 11000, timestamp: now - 14 * day },
    ];
    setSteamProfitData(steamProfitTemp);
    
    setLoading(false);
  }, []);
  
  const getGridClasses = () => {
    const poppedCount = poppedOutGraphs.length;
    if (poppedCount === 0) return "grid-cols-1 md:grid-cols-2";
    return "grid-cols-1";
  };
  
  return (
    <DashboardLayout>
      {/* Enhanced slider styles */}
      <style jsx global>{`
        .slider-enhanced .slider-track {
          height: 8px !important;
        }
        .slider-enhanced .slider-thumb {
          width: 20px !important;
          height: 20px !important;
        }
        .slider-enhanced .slider-range {
          height: 8px !important;
        }
      `}</style>
      
      <div className="flex flex-col gap-4">
        <PageHeader
          title="Trading Statistics" 
          notifications={[]} 
          unreadNotifications={0}        
        />
        
        {/* Global Date Range Filter */}
        <div className="flex items-center justify-end mb-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="date-range" className="text-white">Date Range:</Label>
            <select
              id="date-range"
              className="p-2 rounded bg-gray-800 border border-gray-700 text-gray-200 hover:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={globalDateRange.label}
              onChange={(e) => {
                const selected = dateRanges.find(dr => dr.label === e.target.value);
                if (selected) setGlobalDateRange(selected);
              }}
            >
              {dateRanges.map((range) => (
                <option key={range.label} value={range.label} className="bg-gray-800 text-gray-200">
                  {range.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className={`grid ${getGridClasses()} gap-4`}>
          {/* 1. Weekly Steam Balance Profit */}
          <Card className={`${isGraphPoppedOut('steamprofit') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'steamprofit' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Weekly Steam Balance Profit</CardTitle>
                <CardDescription>INR profit from steam items</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('steamprofit')}>
                  {isGraphPoppedOut('steamprofit') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('steamprofit')}>
                  {maximized && maximizedGraph === 'steamprofit' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('steamprofit')}
                maximized={maximized && maximizedGraph === 'steamprofit'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <SteamProfitChart data={filteredSteamProfitData} />
                }
                data={globalFilteredData.base.steamProfit}
                range={steamProfitRange}
                onRangeChange={throttledSteamProfitUpdate}
              />
            </CardContent>
          </Card>

          {/* 2. Armoury Item Profitability */}
          <Card className={`${isGraphPoppedOut('armoury') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'armoury' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Armoury Item Profitability</CardTitle>
                <CardDescription>Profit percentage from key CS items</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('armoury')}>
                  {isGraphPoppedOut('armoury') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('armoury')}>
                  {maximized && maximizedGraph === 'armoury' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('armoury')}
                maximized={maximized && maximizedGraph === 'armoury'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <ArmouryChart data={filteredArmouryData} />
                }
                data={globalFilteredData.base.armoury}
                range={armouryRange}
                onRangeChange={throttledArmouryUpdate}
              />
            </CardContent>
          </Card>

          {/* 3. Passes Farmed Over Time */}
          <Card className={`${isGraphPoppedOut('passes') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'passes' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Passes Farmed Over Time</CardTitle>
                <CardDescription>Number of mission passes completed</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('passes')}>
                  {isGraphPoppedOut('passes') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('passes')}>
                  {maximized && maximizedGraph === 'passes' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('passes')}
                maximized={maximized && maximizedGraph === 'passes'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <PassesChart data={filteredPassesData} />
                }
                data={globalFilteredData.base.passes}
                range={passesRange}
                onRangeChange={throttledPassesUpdate}
              />
            </CardContent>
          </Card>

          {/* 4. Pass Completion Time Graph */}
          <Card className={`${isGraphPoppedOut('completion') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'completion' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Pass Completion Time</CardTitle>
                <CardDescription>Average time to complete passes</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('completion')}>
                  {isGraphPoppedOut('completion') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('completion')}>
                  {maximized && maximizedGraph === 'completion' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('completion')}
                maximized={maximized && maximizedGraph === 'completion'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <CompletionTimeChart data={filteredCompletionTimeData} />
                }
                data={globalFilteredData.base.completionTime}
                range={completionTimeRange}
                onRangeChange={throttledCompletionTimeUpdate}
              />
            </CardContent>
          </Card>

          {/* 5. Expenses Over Time */}
          <Card className={`${isGraphPoppedOut('expenses') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'expenses' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Expenses Over Time</CardTitle>
                <CardDescription>Monthly breakdown of expenses by payment method</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('expenses')}>
                  {isGraphPoppedOut('expenses') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('expenses')}>
                  {maximized && maximizedGraph === 'expenses' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('expenses')}
                maximized={maximized && maximizedGraph === 'expenses'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <ExpensesChart data={filteredExpensesData} includeGiftCards={includeGiftCards} />
                }
                data={globalFilteredData.base.expenses}
                range={expensesRange}
                onRangeChange={throttledExpensesUpdate}
              />
              <div className="flex items-center space-x-2 mt-2">
                <Switch id="include-gift-cards" checked={includeGiftCards} onCheckedChange={setIncludeGiftCards} />
                <Label htmlFor="include-gift-cards">Include Gift Cards</Label>
              </div>
            </CardContent>
          </Card>

          {/* 6. CSFloat Withdrawals */}
          <Card className={`${isGraphPoppedOut('csfloat') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'csfloat' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>CSFloat Withdrawals</CardTitle>
                <CardDescription>Weekly INR withdrawals from CSFloat</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('csfloat')}>
                  {isGraphPoppedOut('csfloat') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('csfloat')}>
                  {maximized && maximizedGraph === 'csfloat' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('csfloat')}
                maximized={maximized && maximizedGraph === 'csfloat'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <CsfloatChart data={filteredCsfloatData} />
                }
                data={globalFilteredData.base.csfloat}
                range={csfloatRange}
                onRangeChange={throttledCsfloatUpdate}
              />
            </CardContent>
          </Card>

          {/* 7. Market.CSGO Chart */}
          <Card className={`${isGraphPoppedOut('marketcsgo') ? 'col-span-full' : ''} ${maximized && maximizedGraph === 'marketcsgo' ? 'fixed inset-4 z-50 overflow-auto bg-gray-900' : ''}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Market.CSGO Withdrawals</CardTitle>
                <CardDescription>Weekly USDT withdrawals (INR equivalent in tooltip)</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" onClick={() => togglePopOut('marketcsgo')}>
                  {isGraphPoppedOut('marketcsgo') ? <ArrowLeft size={16} /> : <ArrowRight size={16} />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => toggleMaximize('marketcsgo')}>
                  {maximized && maximizedGraph === 'marketcsgo' ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChartWithSlider
                poppedOut={isGraphPoppedOut('marketcsgo')}
                maximized={maximized && maximizedGraph === 'marketcsgo'}
                chart={
                  loading ? <Skeleton className="w-full h-full" /> : <MarketCsgoChart data={filteredMarketCsgoData} />
                }
                data={globalFilteredData.base.marketCsgo}
                range={marketCsgoRange}
                onRangeChange={throttledMarketCsgoUpdate}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
