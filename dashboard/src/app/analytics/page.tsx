"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import {
    IconMessage,
    IconCommand,
    IconUsers,
    IconCalendarEvent,
    IconClock,
    IconTrendingUp,
    IconRefresh,
    IconChartBar,
    IconActivity,
} from "@tabler/icons-react";
import { api, type Stats, type Group } from "@/lib/api";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

function BarChart({
    data,
    maxValue,
    height = 120,
}: {
    data: { label: string; value: number; color: string }[];
    maxValue?: number;
    height?: number;
}) {
    const max = maxValue || Math.max(...data.map(d => d.value), 1);

    return (
        <div className="flex items-end justify-around gap-2" style={{ height }}>
            {data.map((item, i) => (
                <motion.div
                    key={item.label}
                    initial={{ height: 0 }}
                    animate={{ height: `${(item.value / max) * 100}%` }}
                    transition={{ duration: 0.5, delay: i * 0.1 }}
                    className="relative flex-1 max-w-16 rounded-t-lg flex flex-col justify-end items-center"
                    style={{ backgroundColor: item.color, minHeight: 4 }}
                >
                    <span className="absolute -top-6 text-xs font-bold text-white">
                        {item.value}
                    </span>
                    <span className="absolute -bottom-6 text-xs text-neutral-500 truncate max-w-full">
                        {item.label}
                    </span>
                </motion.div>
            ))}
        </div>
    );
}

function RingChart({
    value,
    total,
    color,
    size = 80,
    strokeWidth = 8,
}: {
    value: number;
    total: number;
    color: string;
    size?: number;
    strokeWidth?: number;
}) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const percentage = total > 0 ? (value / total) * 100 : 0;
    const offset = circumference - (percentage / 100) * circumference;

    return (
        <div className="relative" style={{ width: size, height: size }}>
            <svg className="transform -rotate-90" width={size} height={size}>
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    className="text-neutral-800"
                />
                <motion.circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset: offset }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    strokeDasharray={circumference}
                />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xl font-bold text-white">{percentage.toFixed(0)}%</span>
            </div>
        </div>
    );
}

function MetricCard({
    title,
    value,
    icon: Icon,
    color,
    description,
    delay = 0,
}: {
    title: string;
    value: number | string;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    description?: string;
    delay?: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay }}
        >
            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-3">
                        <div className={`p-2 rounded-lg ${color}`}>
                            <Icon className="h-4 w-4 text-white" />
                        </div>
                        <span className="text-sm font-medium text-neutral-400">{title}</span>
                    </div>
                    <div className="text-3xl font-bold text-white">{value}</div>
                    {description && (
                        <p className="text-xs text-neutral-500 mt-1">{description}</p>
                    )}
                </CardContent>
            </GlowCard>
        </motion.div>
    );
}

export default function AnalyticsPage() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [groups, setGroups] = useState<Group[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = async () => {
        try {
            const [statsData, groupsData] = await Promise.all([
                api.getStats().catch(() => null),
                api.getGroups().catch(() => ({ groups: [], count: 0 })),
            ]);

            if (statsData) setStats(statsData);
            if (groupsData) setGroups(groupsData.groups || []);
        } catch (err) {
            console.error("Failed to fetch analytics:", err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const activityData = stats ? [
        { label: "Messages", value: stats.messagesTotal, color: "#3b82f6" },
        { label: "Commands", value: stats.commandsUsed, color: "#8b5cf6" },
        { label: "Groups", value: stats.activeGroups, color: "#22c55e" },
        { label: "Tasks", value: stats.scheduledTasks, color: "#f59e0b" },
    ] : [];

    const topGroups = groups
        .sort((a, b) => b.memberCount - a.memberCount)
        .slice(0, 5)
        .map((g, i) => ({
            label: g.name.slice(0, 8),
            value: g.memberCount,
            color: ["#3b82f6", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444"][i],
        }));

    const commandRate = stats && stats.messagesTotal > 0
        ? (stats.commandsUsed / stats.messagesTotal) * 100
        : 0;

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <motion.h1
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-3xl font-bold text-white"
                    >
                        Analytics
                    </motion.h1>
                    <p className="text-neutral-500 mt-1">
                        Bot activity and performance metrics
                    </p>
                </div>
                <Button
                    variant="outline"
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="gap-2"
                >
                    <IconRefresh className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                    Refresh
                </Button>
            </div>

            {loading ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-32 bg-neutral-800 animate-pulse rounded-xl" />
                    ))}
                </div>
            ) : (
                <>
                    {/* Main Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <MetricCard
                            title="Total Messages"
                            value={stats?.messagesTotal.toLocaleString() || "0"}
                            icon={IconMessage}
                            color="bg-blue-500/20"
                            description="All time"
                            delay={0}
                        />
                        <MetricCard
                            title="Commands Used"
                            value={stats?.commandsUsed.toLocaleString() || "0"}
                            icon={IconCommand}
                            color="bg-purple-500/20"
                            description={`${commandRate.toFixed(1)}% of messages`}
                            delay={0.1}
                        />
                        <MetricCard
                            title="Active Groups"
                            value={stats?.activeGroups || 0}
                            icon={IconUsers}
                            color="bg-green-500/20"
                            delay={0.2}
                        />
                        <MetricCard
                            title="Scheduled Tasks"
                            value={stats?.scheduledTasks || 0}
                            icon={IconCalendarEvent}
                            color="bg-amber-500/20"
                            delay={0.3}
                        />
                    </div>

                    {/* Charts Row */}
                    <div className="grid md:grid-cols-2 gap-6">
                        {/* Activity Overview */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4 }}
                        >
                            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <IconChartBar className="h-5 w-5 text-blue-400" />
                                        Activity Overview
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4 pb-10">
                                    {activityData.length > 0 ? (
                                        <BarChart data={activityData} height={140} />
                                    ) : (
                                        <div className="h-32 flex items-center justify-center text-neutral-500">
                                            No data available
                                        </div>
                                    )}
                                </CardContent>
                            </GlowCard>
                        </motion.div>

                        {/* Command Usage Rate */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5 }}
                        >
                            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <IconActivity className="h-5 w-5 text-purple-400" />
                                        Command Usage Rate
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4">
                                    <div className="flex items-center justify-center gap-8 py-4">
                                        <RingChart
                                            value={stats?.commandsUsed || 0}
                                            total={stats?.messagesTotal || 1}
                                            color="#8b5cf6"
                                            size={100}
                                        />
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <div className="w-3 h-3 rounded-full bg-purple-500" />
                                                <span className="text-sm text-neutral-400">
                                                    Commands: {stats?.commandsUsed.toLocaleString() || 0}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-3 h-3 rounded-full bg-neutral-700" />
                                                <span className="text-sm text-neutral-400">
                                                    Other: {((stats?.messagesTotal || 0) - (stats?.commandsUsed || 0)).toLocaleString()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </GlowCard>
                        </motion.div>
                    </div>

                    {/* Top Groups */}
                    {topGroups.length > 0 && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.6 }}
                        >
                            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <IconTrendingUp className="h-5 w-5 text-green-400" />
                                        Top Groups by Members
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4 pb-10">
                                    <BarChart data={topGroups} height={120} />
                                </CardContent>
                            </GlowCard>
                        </motion.div>
                    )}

                    {/* Uptime Card */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.7 }}
                    >
                        <Card className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-green-500/10 border-neutral-800">
                            <CardContent className="p-6">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="p-3 rounded-xl bg-green-500/20">
                                            <IconClock className="h-6 w-6 text-green-400" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-neutral-400">Bot Uptime</p>
                                            <p className="text-2xl font-bold text-white">
                                                {stats?.uptime || "Unknown"}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                        <span className="text-sm text-green-400">Online</span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                </>
            )}
        </div>
    );
}
