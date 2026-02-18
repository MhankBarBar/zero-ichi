"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { api, type LogEntry } from "@/lib/api";
import {
    IconAlertCircle,
    IconAlertTriangle,
    IconBug,
    IconChevronDown,
    IconChevronRight,
    IconClock,
    IconCode,
    IconFilter,
    IconHash,
    IconInfoCircle,
    IconMessage,
    IconMessageCircle,
    IconPlayerPlay,
    IconRefresh,
    IconSearch,
    IconTerminal2,
    IconUser,
    IconUsers,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";

const levelConfig: Record<
    string,
    {
        icon: typeof IconInfoCircle;
        color: string;
        bg: string;
        border: string;
        label: string;
    }
> = {
    info: {
        icon: IconInfoCircle,
        color: "text-blue-400",
        bg: "bg-blue-500/10",
        border: "border-blue-500/20",
        label: "Info",
    },
    warning: {
        icon: IconAlertTriangle,
        color: "text-amber-400",
        bg: "bg-amber-500/10",
        border: "border-amber-500/20",
        label: "Warning",
    },
    error: {
        icon: IconAlertCircle,
        color: "text-red-400",
        bg: "bg-red-500/10",
        border: "border-red-500/20",
        label: "Error",
    },
    debug: {
        icon: IconBug,
        color: "text-neutral-400",
        bg: "bg-neutral-500/10",
        border: "border-neutral-500/20",
        label: "Debug",
    },
    command: {
        icon: IconPlayerPlay,
        color: "text-green-400",
        bg: "bg-green-500/10",
        border: "border-green-500/20",
        label: "Command",
    },
};

interface ParsedLogEntry {
    timestamp?: string;
    data?: {
        id?: string;
        chat?: string;
        sender?: string;
        sender_name?: string;
        is_from_me?: boolean;
        is_group?: boolean;
        text?: string;
        timestamp?: number;
        raw_message?: Record<string, unknown>;
    };
}

function formatChatId(chat?: string) {
    if (!chat) return "Unknown";
    return (
        chat
            .replace(/@g\.us$/, "")
            .replace(/@s\.whatsapp\.net$/, "")
            .slice(0, 16) + "..."
    );
}

function getMessagePreview(data: ParsedLogEntry["data"]): string {
    if (!data) return "";
    if (data.text) return data.text;

    const raw = data.raw_message;
    if (!raw) return "";

    if (typeof raw.conversation === "string") return raw.conversation;
    if (
        raw.extendedTextMessage &&
        typeof (raw.extendedTextMessage as Record<string, unknown>).text === "string"
    ) {
        return (raw.extendedTextMessage as Record<string, unknown>).text as string;
    }
    if (raw.imageMessage) return "📷 Image";
    if (raw.videoMessage) return "🎬 Video";
    if (raw.stickerMessage) return "🎨 Sticker";
    if (raw.documentMessage) return "📄 Document";
    if (raw.audioMessage) return "🎵 Audio";

    return "";
}

function BotLogEntry({ log }: { log: LogEntry }) {
    const config = levelConfig[log.level] || levelConfig.info;
    const Icon = config.icon;

    const cmdMatch = log.message.match(
        /^CMD \[(SUCCESS|FAILED)\] (.+?) \| sender=(.+?) \| chat=(.+?) \| time=(.+?)(?:\s*\| error=(.+))?$/,
    );

    return (
        <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-xl border px-4 py-3 ${config.border} ${config.bg}`}
        >
            <div className="flex min-w-0 items-start gap-3">
                <div
                    className={`rounded-lg p-1.5 ${config.bg} border ${config.border} mt-0.5 shrink-0`}
                >
                    <Icon className={`h-3.5 w-3.5 ${config.color}`} />
                </div>

                <div className="min-w-0 flex-1 space-y-1">
                    {cmdMatch ? (
                        <>
                            <div className="flex flex-wrap items-center gap-2">
                                <span
                                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                                        cmdMatch[1] === "SUCCESS"
                                            ? "bg-green-500/20 text-green-400"
                                            : "bg-red-500/20 text-red-400"
                                    }`}
                                >
                                    {cmdMatch[1]}
                                </span>
                                <code className="text-sm font-medium text-white">
                                    {cmdMatch[2]}
                                </code>
                                <span className="ml-auto hidden text-xs text-neutral-500 sm:block">
                                    {cmdMatch[5]}
                                </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-500">
                                <span className="flex items-center gap-1">
                                    <IconUser className="h-3 w-3" />
                                    {cmdMatch[3]}
                                </span>
                                <span className="truncate">{cmdMatch[4]}</span>
                            </div>
                            {cmdMatch[6] && (
                                <p className="mt-1 text-xs text-red-400">Error: {cmdMatch[6]}</p>
                            )}
                        </>
                    ) : (
                        <p className="text-sm break-words text-neutral-200">
                            {log.message.length > 300
                                ? log.message.slice(0, 300) + "..."
                                : log.message}
                        </p>
                    )}
                </div>

                {log.timestamp && (
                    <span className="hidden shrink-0 text-xs whitespace-nowrap text-neutral-600 sm:block">
                        {log.timestamp.slice(11, 19) || log.timestamp}
                    </span>
                )}
            </div>
        </motion.div>
    );
}

function MessageLogEntry({ log, showRaw }: { log: LogEntry; showRaw: boolean }) {
    const [expanded, setExpanded] = useState(false);
    const config = levelConfig.info;
    const Icon = config.icon;

    let parsed: ParsedLogEntry | null = null;
    let isJson = false;
    try {
        if (log.message.startsWith("{")) {
            parsed = JSON.parse(log.message);
            isJson = true;
        }
    } catch {
        /* not json */
    }

    const formatTimestamp = (ts: number | string | undefined) => {
        if (!ts) return "";
        let date: Date;
        if (typeof ts === "number") {
            date = ts < 946684800000 ? new Date(ts * 1000) : new Date(ts);
        } else {
            date = new Date(ts);
        }
        return date.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
        });
    };

    if (showRaw) {
        return (
            <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-xl border p-3 ${config.border} ${config.bg} overflow-hidden`}
            >
                <div className="flex items-start gap-3">
                    <Icon className={`mt-0.5 h-4 w-4 ${config.color} shrink-0`} />
                    <pre className="max-w-full flex-1 overflow-x-auto font-mono text-xs break-all whitespace-pre-wrap text-neutral-300">
                        {log.message.length > 500 ? log.message.slice(0, 500) + "..." : log.message}
                    </pre>
                </div>
            </motion.div>
        );
    }

    if (isJson && parsed) {
        const data = parsed.data;
        const messagePreview = getMessagePreview(data);
        const hasDetails = data && (data.raw_message || data.id || data.chat);

        return (
            <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-xl border ${config.border} ${config.bg} overflow-hidden`}
            >
                <div
                    className={`p-4 ${hasDetails ? "cursor-pointer hover:bg-white/5" : ""} transition-colors`}
                    onClick={() => hasDetails && setExpanded(!expanded)}
                >
                    <div className="flex min-w-0 items-start gap-3">
                        <div
                            className={`rounded-lg p-2 ${config.bg} border ${config.border} shrink-0`}
                        >
                            <Icon className={`h-4 w-4 ${config.color}`} />
                        </div>

                        <div className="min-w-0 flex-1 space-y-2 overflow-hidden">
                            <div className="flex flex-wrap items-center gap-2">
                                {data?.sender_name && (
                                    <span className="flex items-center gap-1.5 text-sm font-medium text-white">
                                        <IconUser className="h-3.5 w-3.5 shrink-0 text-green-400" />
                                        <span className="max-w-[120px] truncate sm:max-w-[150px]">
                                            {data.sender_name}
                                        </span>
                                    </span>
                                )}
                                {data?.is_group && (
                                    <span className="flex shrink-0 items-center gap-1 rounded-full bg-purple-500/20 px-2 py-0.5 text-xs text-purple-400">
                                        <IconUsers className="h-3 w-3" />
                                        Group
                                    </span>
                                )}
                                {data?.is_from_me && (
                                    <span className="shrink-0 rounded-full bg-blue-500/20 px-2 py-0.5 text-xs text-blue-400">
                                        You
                                    </span>
                                )}
                                <span className="ml-auto hidden shrink-0 items-center gap-1 text-xs text-neutral-500 sm:flex">
                                    <IconClock className="h-3 w-3" />
                                    {formatTimestamp(data?.timestamp) ||
                                        parsed.timestamp?.slice(11, 19) ||
                                        ""}
                                </span>
                            </div>

                            <div className="flex items-center gap-1 text-xs text-neutral-500 sm:hidden">
                                <IconClock className="h-3 w-3" />
                                {formatTimestamp(data?.timestamp) ||
                                    parsed.timestamp?.slice(11, 19) ||
                                    ""}
                            </div>

                            {messagePreview && (
                                <div className="flex min-w-0 items-start gap-2">
                                    <IconMessage className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" />
                                    <p className="line-clamp-2 text-sm break-words text-neutral-200">
                                        {messagePreview}
                                    </p>
                                </div>
                            )}

                            {data?.chat && (
                                <div className="flex items-center gap-4 text-xs text-neutral-500">
                                    <span className="flex items-center gap-1 truncate">
                                        <IconHash className="h-3 w-3 shrink-0" />
                                        <span className="truncate">{formatChatId(data.chat)}</span>
                                    </span>
                                </div>
                            )}

                            {!data?.sender_name && !messagePreview && (
                                <p className="text-sm text-neutral-500 italic">Log entry</p>
                            )}
                        </div>

                        {hasDetails && (
                            <div className="shrink-0">
                                {expanded ? (
                                    <IconChevronDown className="h-4 w-4 text-neutral-500" />
                                ) : (
                                    <IconChevronRight className="h-4 w-4 text-neutral-500" />
                                )}
                            </div>
                        )}
                    </div>
                </div>

                <AnimatePresence>
                    {expanded && data && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                        >
                            <div className="border-t border-neutral-700/50 bg-neutral-900/50 p-4">
                                <div className="mb-4 grid gap-2 text-sm">
                                    {data.id && (
                                        <div className="flex gap-2">
                                            <span className="w-20 shrink-0 text-neutral-500">
                                                ID
                                            </span>
                                            <span className="truncate font-mono text-xs text-neutral-300">
                                                {data.id}
                                            </span>
                                        </div>
                                    )}
                                    {data.chat && (
                                        <div className="flex gap-2">
                                            <span className="w-20 shrink-0 text-neutral-500">
                                                Chat
                                            </span>
                                            <span className="truncate font-mono text-xs text-neutral-300">
                                                {data.chat}
                                            </span>
                                        </div>
                                    )}
                                    {data.sender && (
                                        <div className="flex gap-2">
                                            <span className="w-20 shrink-0 text-neutral-500">
                                                Sender
                                            </span>
                                            <span className="truncate font-mono text-xs text-neutral-300">
                                                {data.sender}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {data.raw_message && (
                                    <div>
                                        <div className="mb-2 flex items-center gap-2">
                                            <IconCode className="h-4 w-4 text-neutral-500" />
                                            <span className="text-xs font-medium text-neutral-500">
                                                Raw Message
                                            </span>
                                        </div>
                                        <pre className="max-h-48 overflow-x-auto rounded-lg bg-neutral-800 p-3 text-xs break-all whitespace-pre-wrap text-neutral-400">
                                            {JSON.stringify(data.raw_message, null, 2)}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-xl border p-4 ${config.border} ${config.bg} overflow-hidden`}
        >
            <div className="flex min-w-0 items-start gap-3">
                <div className={`rounded-lg p-2 ${config.bg} border ${config.border} shrink-0`}>
                    <Icon className={`h-4 w-4 ${config.color}`} />
                </div>
                <div className="min-w-0 flex-1">
                    {log.timestamp && (
                        <span className="mb-1 block text-xs text-neutral-500">{log.timestamp}</span>
                    )}
                    <p className={`${config.color} text-sm break-words`}>
                        {log.message.length > 300 ? log.message.slice(0, 300) + "..." : log.message}
                    </p>
                </div>
            </div>
        </motion.div>
    );
}

export default function LogsPage() {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [selectedLevel, setSelectedLevel] = useState<string | null>(null);
    const [autoRefresh, setAutoRefresh] = useState(false);
    const [showRaw, setShowRaw] = useState(false);
    const [source, setSource] = useState<"bot" | "messages">("bot");

    const fetchLogs = useCallback(async () => {
        try {
            const data = await api.getLogs(200, selectedLevel || undefined, source);
            setLogs(data.logs);
            setError(null);
        } catch (err) {
            setError("Failed to load logs. Is the API server running?");
            console.error(err);
        }
    }, [selectedLevel, source]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setLoading(true);
        setSelectedLevel(null);
        fetchLogs().finally(() => setLoading(false));
    }, [source]);

    useEffect(() => {
        if (loading) return;
        // eslint-disable-next-line react-hooks/set-state-in-effect
        fetchLogs();
    }, [selectedLevel]);

    useEffect(() => {
        if (!autoRefresh) return;
        const interval = setInterval(fetchLogs, 3000);
        return () => clearInterval(interval);
    }, [autoRefresh, selectedLevel, source]);

    const filteredLogs = logs.filter((log) =>
        log.message.toLowerCase().includes(search.toLowerCase()),
    );

    const botLevels = ["info", "warning", "error", "debug", "command"];
    const msgLevels = ["info"];

    const levelsToShow = source === "bot" ? botLevels : msgLevels;

    if (loading) {
        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-white">Logs</h1>
                    <p className="mt-1 text-neutral-400">Loading logs...</p>
                </div>
                <Card className="border-neutral-700 bg-neutral-800/50">
                    <CardContent className="py-8">
                        <div className="space-y-3">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div
                                    key={i}
                                    className="h-16 animate-pulse rounded-xl bg-neutral-700/50"
                                />
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="max-w-full space-y-6 overflow-hidden">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white">Logs</h1>
                    <p className="mt-1 text-neutral-400">
                        {source === "bot"
                            ? "Structured bot activity logs"
                            : "Raw WhatsApp message logs"}
                    </p>
                </div>
                <div className="flex shrink-0 gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className={`gap-2 ${autoRefresh ? "border-green-500 bg-green-500/10 text-green-400" : ""}`}
                        onClick={() => setAutoRefresh(!autoRefresh)}
                    >
                        <IconRefresh className={`h-4 w-4 ${autoRefresh ? "animate-spin" : ""}`} />
                        {autoRefresh ? "Live" : "Auto"}
                    </Button>
                    <Button variant="outline" size="sm" onClick={fetchLogs}>
                        <IconRefresh className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            <div className="flex gap-2">
                <button
                    onClick={() => setSource("bot")}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-all ${
                        source === "bot"
                            ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-400"
                            : "border border-transparent bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                    }`}
                >
                    <IconTerminal2 className="h-4 w-4" />
                    Bot Logs
                </button>
                <button
                    onClick={() => setSource("messages")}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-all ${
                        source === "messages"
                            ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-400"
                            : "border border-transparent bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                    }`}
                >
                    <IconMessageCircle className="h-4 w-4" />
                    Messages
                </button>
            </div>

            {error && (
                <Card className="border-red-700/50 bg-red-900/30">
                    <CardContent className="flex items-center gap-4 py-4">
                        <IconAlertCircle className="h-6 w-6 text-red-400" />
                        <div>
                            <h3 className="font-semibold text-white">Error</h3>
                            <p className="text-sm text-red-400">{error}</p>
                        </div>
                    </CardContent>
                </Card>
            )}

            <div className="space-y-4">
                <div className="relative">
                    <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                    <Input
                        placeholder="Search logs..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="h-11 rounded-xl border-neutral-700 bg-neutral-800/50 pl-10 text-white"
                    />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <button
                        onClick={() => setSelectedLevel(null)}
                        className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                            !selectedLevel
                                ? "bg-green-500 text-white"
                                : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                        }`}
                    >
                        All
                    </button>
                    {levelsToShow.map((level) => {
                        const cfg = levelConfig[level];
                        if (!cfg) return null;
                        return (
                            <button
                                key={level}
                                onClick={() => setSelectedLevel(level)}
                                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                                    selectedLevel === level
                                        ? "bg-green-500 text-white"
                                        : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                                }`}
                            >
                                <cfg.icon className="h-3.5 w-3.5" />
                                {cfg.label}
                            </button>
                        );
                    })}

                    {source === "messages" && (
                        <div className="ml-auto flex items-center gap-2 rounded-lg bg-neutral-800 px-3 py-1.5">
                            <IconCode className="h-4 w-4 text-neutral-400" />
                            <span className="text-xs text-neutral-400">Raw</span>
                            <Switch
                                checked={showRaw}
                                onCheckedChange={setShowRaw}
                                className="scale-75"
                            />
                        </div>
                    )}
                </div>
            </div>

            <Card className="overflow-hidden border-neutral-700/50 bg-neutral-800/30">
                <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-lg text-white">Log Entries</CardTitle>
                        <span className="rounded-full bg-neutral-800 px-2 py-1 text-xs text-neutral-500">
                            {filteredLogs.length} entries
                        </span>
                    </div>
                </CardHeader>
                <CardContent className="overflow-hidden">
                    {filteredLogs.length === 0 ? (
                        <div className="py-16 text-center">
                            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-neutral-800">
                                <IconFilter className="h-8 w-8 text-neutral-600" />
                            </div>
                            <p className="font-medium text-neutral-400">No logs found</p>
                            <p className="mt-1 text-sm text-neutral-500">
                                {source === "bot"
                                    ? "Bot logs will appear here once FILE_LOGGING is enabled and the bot runs"
                                    : "Message logs will appear as the bot receives messages"}
                            </p>
                        </div>
                    ) : (
                        <div className="max-h-[65vh] space-y-2 overflow-x-hidden overflow-y-auto pr-1">
                            {filteredLogs.map((log, index) =>
                                source === "bot" ? (
                                    <BotLogEntry key={`${log.id}-${index}`} log={log} />
                                ) : (
                                    <MessageLogEntry
                                        key={`${log.id}-${index}`}
                                        log={log}
                                        showRaw={showRaw}
                                    />
                                ),
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
