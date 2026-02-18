"use client";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    GlowCard,
} from "@/components/ui/card";
import { SparklesCore } from "@/components/ui/sparkles";
import { useWebSocket } from "@/hooks/use-websocket";
import { api, type BotStatus, type Stats } from "@/lib/api";
import {
    IconActivity,
    IconAlertCircle,
    IconArrowRight,
    IconBolt,
    IconBrandWhatsapp,
    IconCheck,
    IconClock,
    IconCommand,
    IconCopy,
    IconMessage,
    IconQrcode,
    IconRefresh,
    IconSend,
    IconSettings,
    IconTerminal2,
    IconUsers,
    IconWifi,
    IconWifiOff,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

function StatCard({
    title,
    value,
    description,
    icon: Icon,
    gradient,
    loading,
    delay = 0,
}: {
    title: string;
    value: string | number;
    description?: string;
    icon: React.ComponentType<{ className?: string }>;
    gradient: string;
    loading?: boolean;
    delay?: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay }}
        >
            <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                <CardContent className="relative p-6">
                    <div className="mb-4 flex items-start justify-between">
                        <div className={`rounded-xl p-3 ${gradient} bg-opacity-20`}>
                            <Icon className="h-5 w-5 text-white" />
                        </div>
                    </div>

                    {loading ? (
                        <div className="space-y-2">
                            <div className="h-8 w-20 animate-pulse rounded bg-neutral-800" />
                            <div className="h-4 w-32 animate-pulse rounded bg-neutral-800" />
                        </div>
                    ) : (
                        <>
                            <div className="text-3xl font-bold tracking-tight text-white">
                                {value}
                            </div>
                            {description && (
                                <p className="mt-1 text-sm text-neutral-500">{description}</p>
                            )}
                        </>
                    )}

                    <p className="mt-4 text-xs font-medium tracking-wide text-neutral-400 uppercase">
                        {title}
                    </p>
                </CardContent>
            </GlowCard>
        </motion.div>
    );
}

function QuickAction({
    icon: Icon,
    title,
    description,
    href,
    color,
    delay = 0,
}: {
    icon: React.ComponentType<{ className?: string }>;
    title: string;
    description: string;
    href: string;
    color: string;
    delay?: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay }}
        >
            <Link href={href} className="block">
                <div className="group cursor-pointer rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 transition-all hover:border-neutral-700 hover:bg-neutral-800/50">
                    <div className="flex items-start gap-4">
                        <div className={`rounded-lg p-3 ${color}`}>
                            <Icon className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                            <p className="font-semibold text-white transition-colors group-hover:text-green-400">
                                {title}
                            </p>
                            <p className="mt-0.5 text-sm text-neutral-500">{description}</p>
                        </div>
                        <IconArrowRight className="h-5 w-5 text-neutral-600 transition-all group-hover:translate-x-1 group-hover:text-green-400" />
                    </div>
                </div>
            </Link>
        </motion.div>
    );
}

export default function DashboardPage() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<BotStatus | null>(null);
    const [stats, setStats] = useState<Stats | null>(null);
    const [authStatus, setAuthStatus] = useState<any>(null);
    const [qrCode, setQrCode] = useState<string | null>(null);
    const [messageTo, setMessageTo] = useState("");
    const [messageText, setMessageText] = useState("");
    const [sending, setSending] = useState(false);
    const [copied, setCopied] = useState(false);
    const { events, connected } = useWebSocket(8);

    const copyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error("Failed to copy:", err);
        }
    };
    const setupAuth = useCallback(async () => {
        const authData = await api.getAuthStatus().catch(() => null);
        if (authData) {
            setAuthStatus(authData);
            if (authData.has_qr) {
                const qrData = await api.getQR().catch(() => ({ qr: null }));
                setQrCode(qrData.qr);
            } else {
                setQrCode(null);
            }
        }
        return authData;
    }, []);

    const fetchData = useCallback(async () => {
        try {
            const [statusData] = await Promise.all([
                api.getStatus().catch(() => null),
                setupAuth(),
            ]);

            if (statusData) setStatus(statusData);

            const statsData = await api.getStats().catch(() => null);
            if (statsData) setStats(statsData);

            setError(null);
        } catch (err) {
            console.error("Fetch data error:", err);
            // Simple error check without state dependency to avoid circularity
            setError("Failed to connect to bot API. Is the API server running?");
        } finally {
            setLoading(false);
        }
    }, [setupAuth]);

    useEffect(() => {
        fetchData();

        const getInterval = () => {
            if (authStatus?.is_logged_in) return 30000;
            return 5000;
        };

        const interval = setInterval(fetchData, getInterval());
        return () => clearInterval(interval);
    }, [fetchData, authStatus?.is_logged_in]);

    return (
        <div className="space-y-8">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col justify-between gap-4 md:flex-row md:items-center"
            >
                <div>
                    <h1 className="text-4xl font-bold tracking-tight text-white">Dashboard</h1>
                    <p className="mt-2 text-neutral-400">Overview of your Zero Ichi WhatsApp bot</p>
                </div>
                <button
                    onClick={fetchData}
                    className="flex items-center gap-2 rounded-lg bg-neutral-800 px-4 py-2 text-sm text-neutral-300 transition-colors hover:bg-neutral-700 hover:text-white"
                >
                    <IconRefresh className="h-4 w-4" />
                    Refresh
                </button>
            </motion.div>

            {error && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                >
                    <Card className="border-red-900/50 bg-red-950/50 backdrop-blur-sm">
                        <CardContent className="flex items-center gap-4 py-4">
                            <div className="rounded-lg bg-red-500/20 p-2">
                                <IconAlertCircle className="h-5 w-5 text-red-400" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-white">Connection Error</h3>
                                <p className="text-sm text-red-400">{error}</p>
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>
            )}

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
            >
                <Card
                    className={`relative overflow-hidden border-0 ${
                        status?.status === "online" && authStatus?.is_logged_in
                            ? "bg-gradient-to-br from-green-950/80 via-emerald-950/50 to-neutral-950"
                            : "bg-gradient-to-br from-red-950/80 via-red-900/50 to-neutral-950"
                    }`}
                >
                    {status?.status === "online" && authStatus?.is_logged_in && (
                        <div className="absolute inset-0 h-full w-full">
                            <SparklesCore
                                id="status-sparkles"
                                background="transparent"
                                minSize={0.4}
                                maxSize={1}
                                particleDensity={40}
                                particleColor="#22c55e"
                                speed={0.5}
                                className="h-full w-full"
                            />
                        </div>
                    )}

                    <CardContent className="relative z-10 p-6">
                        <div className="flex flex-col gap-6 md:flex-row md:items-center">
                            <div className="relative">
                                <div
                                    className={`h-16 w-16 rounded-2xl ${
                                        status?.status === "online" && authStatus?.is_logged_in
                                            ? "bg-gradient-to-br from-green-500 to-emerald-600"
                                            : "bg-gradient-to-br from-red-500 to-red-600"
                                    } flex items-center justify-center shadow-lg ${
                                        status?.status === "online"
                                            ? "shadow-green-500/25"
                                            : "shadow-red-500/25"
                                    }`}
                                >
                                    <IconBrandWhatsapp className="h-8 w-8 text-white" />
                                </div>
                                {status?.status === "online" && authStatus?.is_logged_in && (
                                    <span className="absolute -top-1 -right-1 flex h-4 w-4">
                                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                                        <span className="relative inline-flex h-4 w-4 rounded-full bg-green-500" />
                                    </span>
                                )}
                            </div>

                            <div className="flex-1">
                                <h2 className="text-2xl font-bold text-white">
                                    {loading
                                        ? "Connecting..."
                                        : status?.status === "online" && authStatus?.is_logged_in
                                          ? "Bot Online"
                                          : "Bot Offline"}
                                </h2>
                                <p
                                    className={`mt-1 text-sm ${status?.status === "online" && authStatus?.is_logged_in ? "text-green-400" : "text-red-400"}`}
                                >
                                    {loading
                                        ? "Waiting for API..."
                                        : error
                                          ? "Dashboard API unreachable"
                                          : authStatus?.is_logged_in
                                            ? "All systems operational"
                                            : "WhatsApp login required"}
                                </p>
                            </div>

                            {authStatus?.is_logged_in && (
                                <div className="flex items-center gap-3 rounded-xl bg-black/30 px-4 py-3">
                                    <IconClock className="h-5 w-5 text-neutral-400" />
                                    <div>
                                        <p className="text-xs text-neutral-400">Uptime</p>
                                        <p className="font-mono text-lg font-bold text-white">
                                            {stats?.uptime || "—"}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            <div className="grid gap-6">
                <AnimatePresence mode="wait">
                    {(!authStatus?.is_logged_in || authStatus?.has_qr) && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                        >
                            <Card className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-white">
                                        <IconQrcode className="h-5 w-5 text-green-400" />
                                        WhatsApp Login
                                    </CardTitle>
                                    <CardDescription>
                                        Scan the QR code or enter the pair code to connect
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="flex flex-col items-center justify-center py-6">
                                    {qrCode ? (
                                        <div className="rounded-2xl bg-white p-4 shadow-xl shadow-green-500/10">
                                            <Image
                                                src={`data:image/png;base64,${qrCode}`}
                                                alt="WhatsApp QR Code"
                                                width={192}
                                                height={192}
                                                className="h-48 w-48"
                                                unoptimized
                                            />
                                        </div>
                                    ) : authStatus?.pair_code ? (
                                        <div className="space-y-4 text-center">
                                            <div className="rounded-2xl border border-neutral-700 bg-neutral-800 p-6">
                                                <p className="mb-2 text-xs font-bold tracking-widest text-neutral-500 uppercase">
                                                    Pairing Code
                                                </p>
                                                <p className="font-mono text-4xl font-bold tracking-widest text-white">
                                                    {authStatus.pair_code}
                                                </p>
                                            </div>
                                            <Button
                                                variant="outline"
                                                className="gap-2"
                                                onClick={() =>
                                                    authStatus.pair_code &&
                                                    copyToClipboard(authStatus.pair_code)
                                                }
                                            >
                                                {copied ? (
                                                    <IconCheck className="h-4 w-4" />
                                                ) : (
                                                    <IconCopy className="h-4 w-4" />
                                                )}
                                                {copied ? "Copied" : "Copy Code"}
                                            </Button>
                                        </div>
                                    ) : (
                                        <div className="space-y-4 py-10 text-center">
                                            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-green-500/30 border-t-green-500" />
                                            <p className="text-neutral-400">
                                                Waiting for connection data...
                                            </p>
                                        </div>
                                    )}

                                    <div className="mt-8 text-center text-sm text-neutral-500">
                                        <p>Open WhatsApp &gt; Linked Devices &gt; Link a Device</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <StatCard
                    title="Messages"
                    value={stats?.messagesTotal ?? 0}
                    description="Total processed"
                    icon={IconMessage}
                    gradient="bg-gradient-to-br from-blue-500 to-blue-600"
                    loading={loading}
                    delay={0.2}
                />
                <StatCard
                    title="Active Groups"
                    value={stats?.activeGroups ?? 0}
                    description="Bot is member"
                    icon={IconUsers}
                    gradient="bg-gradient-to-br from-purple-500 to-purple-600"
                    loading={loading}
                    delay={0.25}
                />
                <StatCard
                    title="Commands"
                    value={stats?.commandsUsed ?? 0}
                    description="Executed today"
                    icon={IconCommand}
                    gradient="bg-gradient-to-br from-green-500 to-emerald-600"
                    loading={loading}
                    delay={0.3}
                />
                <StatCard
                    title="Uptime"
                    value={stats?.uptime || "—"}
                    description="Since restart"
                    icon={IconActivity}
                    gradient="bg-gradient-to-br from-amber-500 to-orange-600"
                    loading={loading}
                    delay={0.35}
                />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.38 }}
            >
                <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                        <CardTitle className="flex items-center justify-between text-lg">
                            <span className="flex items-center gap-2">
                                <IconActivity className="h-5 w-5 text-green-400" />
                                Live Activity
                            </span>
                            <span className="flex items-center gap-2">
                                <span className="flex items-center gap-1 text-xs font-normal">
                                    {connected ? (
                                        <>
                                            <IconWifi className="h-3.5 w-3.5 text-green-400" />
                                            <span className="text-green-400">Live</span>
                                        </>
                                    ) : (
                                        <>
                                            <IconWifiOff className="h-3.5 w-3.5 text-red-400" />
                                            <span className="text-red-400">Offline</span>
                                        </>
                                    )}
                                </span>
                                <Link
                                    href="/analytics"
                                    className="text-xs text-neutral-500 transition-colors hover:text-green-400"
                                >
                                    View all →
                                </Link>
                            </span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-2">
                        <div className="max-h-48 space-y-0.5 overflow-y-auto pr-1">
                            <AnimatePresence initial={false}>
                                {events.length === 0 ? (
                                    <div className="py-8 text-center text-sm text-neutral-500">
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
                                            className={`flex items-center gap-2 rounded-md border-l-2 px-3 py-1.5 ${
                                                ev.type === "command_executed"
                                                    ? "border-l-purple-500"
                                                    : ev.type === "new_message"
                                                      ? "border-l-blue-500"
                                                      : "border-l-amber-500"
                                            } bg-neutral-800/30`}
                                        >
                                            <div>
                                                {ev.type === "command_executed" ? (
                                                    <IconCommand className="h-3.5 w-3.5 text-purple-400" />
                                                ) : ev.type === "new_message" ? (
                                                    <IconMessage className="h-3.5 w-3.5 text-blue-400" />
                                                ) : (
                                                    <IconBolt className="h-3.5 w-3.5 text-amber-400" />
                                                )}
                                            </div>
                                            <div className="min-w-0 flex-1 truncate text-sm leading-snug text-neutral-300">
                                                {ev.type === "command_executed" ? (
                                                    <>
                                                        <span className="font-medium text-purple-400">
                                                            /{String(ev.data.command)}
                                                        </span>
                                                        {" by "}
                                                        <span className="text-white">
                                                            {String(ev.data.user || "unknown")}
                                                        </span>
                                                    </>
                                                ) : ev.type === "new_message" ? (
                                                    <>
                                                        <span className="text-white">
                                                            {String(ev.data.sender || "unknown")}
                                                        </span>
                                                        {ev.data.text ? (
                                                            <>
                                                                :{" "}
                                                                <span className="text-neutral-400">
                                                                    {String(ev.data.text).slice(
                                                                        0,
                                                                        50,
                                                                    )}
                                                                </span>
                                                            </>
                                                        ) : (
                                                            <span className="text-neutral-500">
                                                                {" "}
                                                                (media)
                                                            </span>
                                                        )}
                                                    </>
                                                ) : (
                                                    <span className="text-neutral-400">
                                                        {ev.type}
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-[10px] whitespace-nowrap text-neutral-600">
                                                {(() => {
                                                    try {
                                                        return new Date(
                                                            ev.timestamp,
                                                        ).toLocaleTimeString("en", {
                                                            hour: "2-digit",
                                                            minute: "2-digit",
                                                            second: "2-digit",
                                                        });
                                                    } catch {
                                                        return "";
                                                    }
                                                })()}
                                            </span>
                                        </motion.div>
                                    ))
                                )}
                            </AnimatePresence>
                        </div>
                    </CardContent>
                </GlowCard>
            </motion.div>

            <div>
                <h3 className="mb-4 text-lg font-semibold text-white">Quick Actions</h3>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                    <QuickAction
                        icon={IconSend}
                        title="Send Message"
                        description="Send text or media"
                        href="/send"
                        color="bg-blue-500/20"
                        delay={0.4}
                    />
                    <QuickAction
                        icon={IconUsers}
                        title="Groups"
                        description="View and manage groups"
                        href="/groups"
                        color="bg-purple-500/20"
                        delay={0.45}
                    />
                    <QuickAction
                        icon={IconSettings}
                        title="Configuration"
                        description="Bot settings & features"
                        href="/config"
                        color="bg-blue-500/20"
                        delay={0.5}
                    />
                    <QuickAction
                        icon={IconTerminal2}
                        title="Logs"
                        description="View activity logs"
                        href="/logs"
                        color="bg-amber-500/20"
                        delay={0.55}
                    />
                </div>
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="py-4 text-center"
            >
                <p className="text-xs text-neutral-600">
                    Zero Ichi Dashboard • Bot: {status?.bot_name || "—"} • Prefix:{" "}
                    {status?.prefix || "—"}
                </p>
            </motion.div>
        </div>
    );
}
