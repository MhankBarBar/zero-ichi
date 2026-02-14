"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
    IconCalendarEvent,
    IconTrash,
    IconAlertCircle,
    IconClock,
    IconRepeat,
    IconBell,
    IconRefresh
} from "@tabler/icons-react";
import { api, type ScheduledTask } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { motion, AnimatePresence } from "framer-motion";

export default function TasksPage() {
    const [tasks, setTasks] = useState<ScheduledTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const toast = useToast();

    const fetchTasks = async () => {
        try {
            setLoading(true);
            const data = await api.getTasks();
            setTasks(data.tasks);
            setError(null);
        } catch (err) {
            setError("Failed to load tasks. Is the API server running?");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTasks();
    }, []);

    const handleToggleTask = async (taskId: string, enabled: boolean) => {
        try {
            await api.toggleTask(taskId, enabled);
            setTasks(prev => prev.map(t =>
                t.id === taskId ? { ...t, enabled } : t
            ));
            toast.success(enabled ? "Task enabled" : "Task disabled");
        } catch (err: any) {
            toast.error("Failed to toggle task", err.message);
        }
    };

    const handleDeleteTask = async (taskId: string) => {
        try {
            await api.deleteTask(taskId);
            setTasks(prev => prev.filter(t => t.id !== taskId));
            toast.success("Task deleted");
        } catch (err: any) {
            toast.error("Failed to delete task", err.message);
        }
    };

    const getTaskIcon = (type: string) => {
        switch (type) {
            case "reminder": return <IconBell className="h-5 w-5 text-amber-400" />;
            case "recurring": return <IconRepeat className="h-5 w-5 text-purple-400" />;
            default: return <IconClock className="h-5 w-5 text-blue-400" />;
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
                    <p className="text-neutral-400 mt-1">Loading tasks...</p>
                </div>
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="bg-neutral-800/50 border-neutral-700 animate-pulse">
                            <CardContent className="p-6">
                                <div className="h-6 bg-neutral-700 rounded w-1/3 mb-2"></div>
                                <div className="h-4 bg-neutral-700 rounded w-2/3"></div>
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
                    <p className="text-neutral-400 mt-1">Manage scheduled messages and reminders</p>
                </div>
                <Card className="bg-red-500/10 border-red-500/20">
                    <CardContent className="p-6 flex items-center gap-3">
                        <IconAlertCircle className="h-5 w-5 text-red-400" />
                        <p className="text-red-400">{error}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Scheduled Tasks</h1>
                    <p className="text-neutral-400 mt-1">
                        {tasks.length} task{tasks.length !== 1 ? "s" : ""} scheduled
                    </p>
                </div>
                <Button
                    onClick={fetchTasks}
                    variant="outline"
                    className="border-neutral-700 text-neutral-400"
                >
                    <IconRefresh className="h-4 w-4 mr-2" />
                    Refresh
                </Button>
            </div>

            {tasks.length === 0 ? (
                <Card className="bg-neutral-800/50 border-neutral-700">
                    <CardContent className="p-12 text-center">
                        <IconCalendarEvent className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-neutral-400 mb-2">
                            No scheduled tasks
                        </h3>
                        <p className="text-neutral-500 text-sm">
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
                                <Card className={`border-neutral-700 transition-colors ${task.enabled
                                        ? "bg-neutral-800/50 hover:border-neutral-600"
                                        : "bg-neutral-800/30 opacity-60"
                                    }`}>
                                    <CardContent className="p-4">
                                        <div className="flex items-start gap-4">
                                            <div className="h-10 w-10 rounded-lg bg-neutral-700/50 flex items-center justify-center shrink-0">
                                                {getTaskIcon(task.type)}
                                            </div>

                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="px-2 py-0.5 bg-neutral-700 text-neutral-300 text-xs rounded capitalize">
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

                                                <p className="text-white text-sm mb-2 line-clamp-2">
                                                    {task.message}
                                                </p>

                                                <div className="flex items-center gap-4 text-xs text-neutral-500">
                                                    {task.trigger_time && (
                                                        <span className="flex items-center gap-1">
                                                            <IconClock className="h-3 w-3" />
                                                            {formatTime(task.trigger_time)}
                                                        </span>
                                                    )}
                                                    <span className="truncate max-w-[200px]">
                                                        To: {task.chat_jid}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-3 shrink-0">
                                                <Switch
                                                    checked={task.enabled}
                                                    onCheckedChange={(checked) => handleToggleTask(task.id, checked)}
                                                />
                                                <button
                                                    onClick={() => handleDeleteTask(task.id)}
                                                    className="p-2 rounded-lg hover:bg-red-500/20 text-neutral-400 hover:text-red-400"
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
