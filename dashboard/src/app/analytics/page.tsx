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
    IconBolt,
    IconWifi,
    IconWifiOff,
} from "@tabler/icons-react";
import { api, type Stats, type Group, type TopCommand, type TimelineEntry } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useWebSocket, type WsEvent } from "@/hooks/use-websocket";


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

function TimelineChart({
    data,
    height = 120,
}: {
    data: TimelineEntry[];
    height?: number;
}) {
    const max = Math.max(...data.map(d => d.count), 1);
    const colors = ["#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#c084fc", "#818cf8", "#60a5fa"];

    return (
        <div className="flex items-end justify-around gap-1.5" style={{ height }}>
            {data.map((item, i) => {
                const dayLabel = new Date(item.date + "T00:00:00").toLocaleDateString("en", {
                    weekday: "short",
                });
                return (
                    <motion.div
                        key={item.date}
                        initial={{ height: 0 }}
                        animate={{ height: `${Math.max((item.count / max) * 100, 3)}%` }}
                        transition={{ duration: 0.5, delay: i * 0.08 }}
                        className="relative flex-1 rounded-t-md flex flex-col justify-end items-center cursor-default group"
                        style={{
                            background: `linear-gradient(to top, ${colors[i % colors.length]}88, ${colors[i % colors.length]})`,
                            minHeight: 4,
                        }}
                    >
                        <span className="absolute -top-6 text-xs font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity">
                            {item.count}
                        </span>
                        <span className="absolute -bottom-6 text-[10px] text-neutral-500">
                            {dayLabel}
                        </span>
                    </motion.div>
                );
            })}
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


function eventIcon(type: string) {
    switch (type) {
        case "command_executed":
            return <IconCommand className="h-3.5 w-3.5 text-purple-400" />;
        case "new_message":
            return <IconMessage className="h-3.5 w-3.5 text-blue-400" />;
        default:
            return <IconBolt className="h-3.5 w-3.5 text-amber-400" />;
    }
}

function eventColor(type: string) {
    switch (type) {
        case "command_executed":
            return "border-l-purple-500";
        case "new_message":
            return "border-l-blue-500";
        default:
            return "border-l-amber-500";
    }
}

function formatEventTime(ts: string) {
    try {
        return new Date(ts).toLocaleTimeString("en", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    } catch {
        return "";
    }
}

function eventSummary(event: WsEvent) {
    const d = event.data;
    switch (event.type) {
        case "command_executed":
            return (
                <>
                    <span className="text-purple-400 font-medium">/{String(d.command)}</span>
                    {" by "}
                    <span className="text-white">{String(d.user || "unknown")}</span>
                </>
            );
        case "new_message":
            return (
                <>
                    <span className="text-white">{String(d.sender || "unknown")}</span>
                    {d.text ? (
                        <>
                            {": "}
                            <span className="text-neutral-400">{String(d.text).slice(0, 60)}</span>
                        </>
                    ) : (
                        <span className="text-neutral-500"> (media)</span>
                    )}
                </>
            );
        default:
            return <span className="text-neutral-400">{event.type}</span>;
    }
}

function LiveFeed({ events, connected }: { events: WsEvent[]; connected: boolean }) {
    return (
        <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
            <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center justify-between">
                    <span className="flex items-center gap-2">
                        <IconActivity className="h-5 w-5 text-green-400" />
                        Live Activity
                    </span>
                    <span className="flex items-center gap-1.5 text-xs font-normal">
                        {connected ? (
                            <>
                                <IconWifi className="h-3.5 w-3.5 text-green-400" />
                                <span className="text-green-400">Connected</span>
                            </>
                        ) : (
                            <>
                                <IconWifiOff className="h-3.5 w-3.5 text-red-400" />
                                <span className="text-red-400">Disconnected</span>
                            </>
                        )}
                    </span>
                </CardTitle>
            </CardHeader>
            <CardContent className="pt-2">
                <div className="space-y-0.5 max-h-80 overflow-y-auto pr-1 scrollbar-thin">
                    <AnimatePresence initial={false}>
                        {events.length === 0 ? (
                            <div className="py-10 text-center text-neutral-500 text-sm">
                                Waiting for events…
                            </div>
                        ) : (
                            events.map((ev, i) => (
                                <motion.div
                                    key={`${ev.timestamp}-${i}`}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className={`flex items-start gap-2 py-2 px-3 rounded-md border-l-2 ${eventColor(ev.type)} bg-neutral-800/30 hover:bg-neutral-800/60 transition-colors`}
                                >
                                    <div className="mt-0.5">{eventIcon(ev.type)}</div>
                                    <div className="flex-1 min-w-0 text-sm leading-snug">
                                        {eventSummary(ev)}
                                    </div>
                                    <span className="text-[10px] text-neutral-600 whitespace-nowrap mt-0.5">
                                        {formatEventTime(ev.timestamp)}
                                    </span>
                                </motion.div>
                            ))
                        )}
                    </AnimatePresence>
                </div>
            </CardContent>
        </GlowCard>
    );
}


export default function AnalyticsPage() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [groups, setGroups] = useState<Group[]>([]);
    const [topCommands, setTopCommands] = useState<TopCommand[]>([]);
    const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
    const [totalCmds, setTotalCmds] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [days, setDays] = useState(7);
    const { events, connected } = useWebSocket(30);

    const fetchData = async () => {
        try {
            const [statsData, groupsData, analyticsData, timelineData] = await Promise.all([
                api.getStats().catch(() => null),
                api.getGroups().catch(() => ({ groups: [], count: 0 })),
                api.getTopCommands(days).catch(() => null),
                api.getTimeline("", days).catch(() => null),
            ]);

            if (statsData) setStats(statsData);
            if (groupsData) setGroups(groupsData.groups || []);
            if (analyticsData) {
                setTopCommands(analyticsData.top_commands);
                setTotalCmds(analyticsData.total);
            }
            if (timelineData) setTimeline(timelineData.timeline);
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
    }, [days]);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const CHART_COLORS = ["#8b5cf6", "#6366f1", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#ec4899", "#14b8a6"];

    const topCmdData = topCommands.slice(0, 8).map((cmd, i) => ({
        label: cmd.command,
        value: cmd.count,
        color: CHART_COLORS[i % CHART_COLORS.length],
    }));

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
                        Bot activity, command insights & real-time feed
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="flex bg-neutral-800 rounded-lg p-0.5 text-sm">
                        {[7, 14, 30].map(d => (
                            <button
                                key={d}
                                onClick={() => setDays(d)}
                                className={`px-3 py-1.5 rounded-md transition-colors ${days === d
                                        ? "bg-purple-500/20 text-purple-300 font-medium"
                                        : "text-neutral-400 hover:text-white"
                                    }`}
                            >
                                {d}d
                            </button>
                        ))}
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
            </div>

            {loading ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-32 bg-neutral-800 animate-pulse rounded-xl" />
                    ))}
                </div>
            ) : (
                <>
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
                            title={`Commands (${days}d)`}
                            value={totalCmds.toLocaleString()}
                            icon={IconTrendingUp}
                            color="bg-amber-500/20"
                            description="From analytics"
                            delay={0.3}
                        />
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4 }}
                        >
                            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <IconChartBar className="h-5 w-5 text-purple-400" />
                                        Top Commands ({days}d)
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4 pb-10">
                                    {topCmdData.length > 0 ? (
                                        <BarChart data={topCmdData} height={140} />
                                    ) : (
                                        <div className="h-32 flex items-center justify-center text-neutral-500">
                                            No command data yet
                                        </div>
                                    )}
                                </CardContent>
                            </GlowCard>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5 }}
                        >
                            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <IconTrendingUp className="h-5 w-5 text-blue-400" />
                                        Daily Usage
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4 pb-10">
                                    {timeline.length > 0 ? (
                                        <TimelineChart data={timeline} height={140} />
                                    ) : (
                                        <div className="h-32 flex items-center justify-center text-neutral-500">
                                            No timeline data yet
                                        </div>
                                    )}
                                </CardContent>
                            </GlowCard>
                        </motion.div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.55 }}
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

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.6 }}
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

                    <div className="grid md:grid-cols-2 gap-6">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.65 }}
                        >
                            <LiveFeed events={events} connected={connected} />
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.7 }}
                        >
                            <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <IconUsers className="h-5 w-5 text-green-400" />
                                        Top Groups by Members
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4 pb-10">
                                    {topGroups.length > 0 ? (
                                        <BarChart data={topGroups} height={120} />
                                    ) : (
                                        <div className="h-32 flex items-center justify-center text-neutral-500">
                                            No group data
                                        </div>
                                    )}
                                </CardContent>
                            </GlowCard>
                        </motion.div>
                    </div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.75 }}
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
