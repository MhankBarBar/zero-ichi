"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { api, type ScheduledTask } from "@/lib/api";
import {
    IconAlertCircle,
    IconBell,
    IconCalendarEvent,
    IconClock,
    IconPlus,
    IconRefresh,
    IconRepeat,
    IconTrash,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

interface TaskModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (task: Omit<ScheduledTask, "id" | "enabled" | "created_at">) => void;
}

function TaskModal({ isOpen, onClose, onSave }: TaskModalProps) {
    const [type, setType] = useState<"reminder" | "auto_message" | "recurring">("reminder");
    const [chatJid, setChatJid] = useState("");
    const [message, setMessage] = useState("");

    const [triggerDate, setTriggerDate] = useState("");
    const [triggerTime, setTriggerTime] = useState("");
    const [interval, setInterval] = useState("");
    const [cron, setCron] = useState("");

    const handleSave = () => {
        if (!chatJid || !message) return;

        const baseTask = {
            chat_jid: chatJid.includes("@") ? chatJid : `${chatJid}@g.us`,
            message,
            type,
        };

        if (type === "reminder") {
            if (!triggerDate || !triggerTime) return;
            const combined = new Date(`${triggerDate}T${triggerTime}`);
            onSave({
                ...baseTask,
                trigger_time: combined.toISOString(),
            });
        } else if (type === "auto_message") {
            if (!interval) return;
            onSave({
                ...baseTask,
                interval_minutes: parseInt(interval),
            });
        } else if (type === "recurring") {
            if (!cron) return;
            onSave({
                ...baseTask,
                cron_expression: cron,
            });
        }
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="mx-4 w-full max-w-lg rounded-2xl border border-neutral-700 bg-neutral-900 p-6 shadow-2xl"
            >
                <div className="mb-6 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Create Scheduled Task</h2>
                    <button onClick={onClose} className="text-neutral-400 hover:text-white">
                        <IconX className="h-5 w-5" />
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Task Type
                        </label>
                        <div className="grid grid-cols-3 gap-2">
                            {(["reminder", "auto_message", "recurring"] as const).map((t) => (
                                <button
                                    key={t}
                                    onClick={() => setType(t)}
                                    className={`rounded-lg px-3 py-2 text-sm capitalize transition-colors ${
                                        type === t
                                            ? "bg-green-600 text-white"
                                            : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                                    }`}
                                >
                                    {t.replace("_", " ")}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Target JID
                        </label>
                        <Input
                            placeholder="e.g. 123456789@g.us (or just number for group)"
                            value={chatJid}
                            onChange={(e) => setChatJid(e.target.value)}
                            className="border-neutral-700 bg-neutral-800 text-white"
                        />
                        <p className="mt-1 text-xs text-neutral-500">
                            Group ID or User JID where the message will be sent
                        </p>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Message
                        </label>
                        <textarea
                            placeholder="Enter your message..."
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            rows={3}
                            className="w-full resize-none rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-white placeholder-neutral-500 focus:ring-2 focus:ring-green-500 focus:outline-none"
                        />
                    </div>

                    {type === "reminder" && (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="mb-2 block text-sm font-medium text-neutral-400">
                                    Date
                                </label>
                                <Input
                                    type="date"
                                    value={triggerDate}
                                    onChange={(e) => setTriggerDate(e.target.value)}
                                    className="border-neutral-700 bg-neutral-800 text-white"
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-neutral-400">
                                    Time
                                </label>
                                <Input
                                    type="time"
                                    value={triggerTime}
                                    onChange={(e) => setTriggerTime(e.target.value)}
                                    className="border-neutral-700 bg-neutral-800 text-white"
                                />
                            </div>
                        </div>
                    )}

                    {type === "auto_message" && (
                        <div>
                            <label className="mb-2 block text-sm font-medium text-neutral-400">
                                Interval (minutes)
                            </label>
                            <Input
                                type="number"
                                placeholder="e.g. 60"
                                value={interval}
                                onChange={(e) => setInterval(e.target.value)}
                                className="border-neutral-700 bg-neutral-800 text-white"
                            />
                        </div>
                    )}

                    {type === "recurring" && (
                        <div>
                            <label className="mb-2 block text-sm font-medium text-neutral-400">
                                Cron Expression
                            </label>
                            <Input
                                placeholder="e.g. 0 8 * * *"
                                value={cron}
                                onChange={(e) => setCron(e.target.value)}
                                className="border-neutral-700 bg-neutral-800 text-white"
                            />
                            <p className="mt-1 text-xs text-neutral-500">
                                Standard cron syntax (min hour day month dow)
                            </p>
                        </div>
                    )}
                </div>

                <div className="mt-6 flex gap-3">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        className="flex-1 border-neutral-700 text-neutral-400"
                    >
                        Cancel
                    </Button>
                    <Button onClick={handleSave} className="flex-1 bg-green-600 hover:bg-green-500">
                        Schedule Task
                    </Button>
                </div>
            </motion.div>
        </div>
    );
}

export default function TasksPage() {
    const [tasks, setTasks] = useState<ScheduledTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [modalOpen, setModalOpen] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const toast = useToast();

    const handleCreateTask = async (task: Omit<ScheduledTask, "id" | "enabled" | "created_at">) => {
        try {
            await api.createTask(task);
            fetchTasks(true);
            toast.success("Task scheduled successfully");
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Failed to schedule task", message);
        }
    };

    const fetchTasks = async (isRefresh = false) => {
        try {
            if (isRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            const data = await api.getTasks();
            setTasks(data.tasks);
            setError(null);
        } catch (err) {
            setError("Failed to load tasks. Is the API server running?");
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchTasks();
    }, []);

    const handleToggleTask = async (taskId: string, enabled: boolean) => {
        try {
            await api.toggleTask(taskId, enabled);
            setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, enabled } : t)));
            toast.success(enabled ? "Task enabled" : "Task disabled");
        } catch (err: any) {
            toast.error("Failed to toggle task", err.message);
        }
    };

    const handleDeleteTask = async (taskId: string) => {
        try {
            await api.deleteTask(taskId);
            setTasks((prev) => prev.filter((t) => t.id !== taskId));
            toast.success("Task deleted");
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Failed to delete task", message);
        }
    };

    const getTaskIcon = (type: string) => {
        switch (type) {
            case "reminder":
                return <IconBell className="h-5 w-5 text-amber-400" />;
            case "recurring":
                return <IconRepeat className="h-5 w-5 text-purple-400" />;
            default:
                return <IconClock className="h-5 w-5 text-blue-400" />;
        }
    };

    const formatTime = (isoString: string | null) => {
        if (!isoString) return "N/A";
        try {
            return new Date(isoString).toLocaleString();
        } catch {
            return isoString;
        }
    };

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Scheduled Tasks</h1>
                    <p className="mt-1 text-neutral-400">Loading tasks...</p>
                </div>
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <Card
                            key={i}
                            className="animate-pulse border-neutral-700 bg-neutral-800/50"
                        >
                            <CardContent className="p-6">
                                <div className="mb-2 h-6 w-1/3 rounded bg-neutral-700"></div>
                                <div className="h-4 w-2/3 rounded bg-neutral-700"></div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Scheduled Tasks</h1>
                    <p className="mt-1 text-neutral-400">Manage scheduled messages and reminders</p>
                </div>
                <Card className="border-red-500/20 bg-red-500/10">
                    <CardContent className="flex items-center gap-3 p-6">
                        <IconAlertCircle className="h-5 w-5 text-red-400" />
                        <p className="text-red-400">{error}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white">Scheduled Tasks</h1>
                    <p className="mt-1 text-neutral-400">
                        {tasks.length} task{tasks.length !== 1 ? "s" : ""} scheduled
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        onClick={() => fetchTasks(true)}
                        variant="outline"
                        disabled={refreshing}
                        className="flex-1 border-neutral-700 text-neutral-400 md:flex-none"
                    >
                        <IconRefresh
                            className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
                        />
                        Refresh
                    </Button>
                    <Button
                        onClick={() => setModalOpen(true)}
                        className="flex-1 bg-green-600 hover:bg-green-500 md:flex-none"
                    >
                        <IconPlus className="mr-2 h-4 w-4" />
                        Create Task
                    </Button>
                </div>
            </div>

            <TaskModal
                isOpen={modalOpen}
                onClose={() => setModalOpen(false)}
                onSave={handleCreateTask}
            />

            {tasks.length === 0 ? (
                <Card className="border-neutral-700 bg-neutral-800/50">
                    <CardContent className="p-12 text-center">
                        <IconCalendarEvent className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                        <h3 className="mb-2 text-lg font-medium text-neutral-400">
                            No scheduled tasks
                        </h3>
                        <p className="text-sm text-neutral-500">
                            Tasks can be created using bot commands like /remind and /schedule
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-4">
                    <AnimatePresence>
                        {tasks.map((task) => (
                            <motion.div
                                key={task.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                            >
                                <Card
                                    className={`border-neutral-700 transition-colors ${
                                        task.enabled
                                            ? "bg-neutral-800/50 hover:border-neutral-600"
                                            : "bg-neutral-800/30 opacity-60"
                                    }`}
                                >
                                    <CardContent className="p-4">
                                        <div className="flex items-start gap-4">
                                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-neutral-700/50">
                                                {getTaskIcon(task.type)}
                                            </div>

                                            <div className="min-w-0 flex-1">
                                                <div className="mb-1 flex items-center gap-2">
                                                    <span className="rounded bg-neutral-700 px-2 py-0.5 text-xs text-neutral-300 capitalize">
                                                        {task.type.replace("_", " ")}
                                                    </span>
                                                    {task.cron_expression && (
                                                        <span className="text-xs text-neutral-500">
                                                            {task.cron_expression}
                                                        </span>
                                                    )}
                                                    {task.interval_minutes && (
                                                        <span className="text-xs text-neutral-500">
                                                            Every {task.interval_minutes} min
                                                        </span>
                                                    )}
                                                </div>

                                                <p className="mb-2 line-clamp-2 text-sm text-white">
                                                    {task.message}
                                                </p>

                                                <div className="flex items-center gap-4 text-xs text-neutral-500">
                                                    {task.trigger_time && (
                                                        <span className="flex items-center gap-1">
                                                            <IconClock className="h-3 w-3" />
                                                            {formatTime(task.trigger_time)}
                                                        </span>
                                                    )}
                                                    <span className="max-w-[200px] truncate">
                                                        To: {task.chat_jid}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex shrink-0 items-center gap-3">
                                                <Switch
                                                    checked={task.enabled}
                                                    onCheckedChange={(checked) =>
                                                        handleToggleTask(task.id, checked)
                                                    }
                                                />
                                                <button
                                                    onClick={() => handleDeleteTask(task.id)}
                                                    className="rounded-lg p-2 text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
                                                >
                                                    <IconTrash className="h-4 w-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
}
