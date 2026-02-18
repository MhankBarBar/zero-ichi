"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import { CustomSelect } from "@/components/ui/custom-select";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { useWebSocket } from "@/hooks/use-websocket";
import { api, type Command } from "@/lib/api";
import {
    IconAlertCircle,
    IconCommand,
    IconFilter,
    IconRefresh,
    IconSearch,
} from "@tabler/icons-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export default function CommandsPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [commands, setCommands] = useState<Command[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState(searchParams.get("q") || "");
    const [selectedCategory, setSelectedCategory] = useState<string | null>(
        searchParams.get("cat") || null,
    );
    const toast = useToast();
    const { lastEvent } = useWebSocket();
    const [refreshing, setRefreshing] = useState(false);

    const updateParams = useCallback(
        (q: string, cat: string | null) => {
            const params = new URLSearchParams();
            if (q) params.set("q", q);
            if (cat) params.set("cat", cat);
            const qs = params.toString();
            router.replace(qs ? `?${qs}` : "?", { scroll: false });
        },
        [router],
    );

    useEffect(() => {
        if (lastEvent?.type === "command_update") {
            const { name, enabled } = lastEvent.data as { name: string; enabled: boolean };
            setCommands((prev) =>
                prev.map((cmd) => (cmd.name === name ? { ...cmd, enabled } : cmd)),
            );
        }
    }, [lastEvent]);

    const fetchCommands = async (isRefresh = false) => {
        try {
            if (isRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            const data = await api.getCommands();
            setCommands(data.commands);
            setError(null);
        } catch (err) {
            setError("Failed to load commands. Is the API server running?");
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchCommands();
    }, []);

    const handleRefresh = () => {
        fetchCommands(true);
    };

    const categories = Array.from(new Set(commands.map((c) => c.category)));

    const filteredCommands = commands.filter((cmd) => {
        const matchesSearch = cmd.name.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = !selectedCategory || cmd.category === selectedCategory;
        return matchesSearch && matchesCategory;
    });

    const toggleCommand = async (name: string, currentEnabled: boolean) => {
        const newEnabled = !currentEnabled;

        setCommands((prev) =>
            prev.map((cmd) => (cmd.name === name ? { ...cmd, enabled: newEnabled } : cmd)),
        );

        try {
            await api.toggleCommand(name, newEnabled);
            if (newEnabled) {
                toast.success(`/${name} enabled`);
            } else {
                toast.warning(`/${name} disabled`);
            }
        } catch (err) {
            setCommands((prev) =>
                prev.map((cmd) => (cmd.name === name ? { ...cmd, enabled: currentEnabled } : cmd)),
            );
            toast.error("Failed to toggle", `Could not update /${name}`);
            console.error("Failed to toggle command:", err);
        }
    };

    const enabledCount = commands.filter((c) => c.enabled).length;

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Commands</h1>
                    <p className="mt-1 text-neutral-400">Loading commands...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <Card key={i} className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="py-6">
                                <div className="mb-2 h-4 w-24 animate-pulse rounded bg-neutral-700" />
                                <div className="h-3 w-32 animate-pulse rounded bg-neutral-700" />
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
                    <h1 className="text-3xl font-bold text-white">Commands</h1>
                    <p className="mt-1 text-neutral-400">Enable or disable bot commands</p>
                </div>
                <Card className="border-red-700/50 bg-red-900/30">
                    <CardContent className="flex items-center gap-4 py-4">
                        <IconAlertCircle className="h-6 w-6 text-red-400" />
                        <div>
                            <h3 className="font-semibold text-white">Error</h3>
                            <p className="text-sm text-red-400">{error}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Commands</h1>
                    <p className="mt-1 text-neutral-400">
                        Enable or disable bot commands ({enabledCount}/{commands.length} enabled)
                    </p>
                </div>
                <Button
                    variant="outline"
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="gap-2 border-neutral-700 text-neutral-400 hover:text-white"
                >
                    <IconRefresh className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                    Refresh
                </Button>
            </div>

            <div className="space-y-4">
                <div className="relative">
                    <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                    <Input
                        placeholder="Search commands..."
                        value={search}
                        onChange={(e) => {
                            setSearch(e.target.value);
                            updateParams(e.target.value, selectedCategory);
                        }}
                        className="border-neutral-700 bg-neutral-800 pl-10 text-white"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <CustomSelect
                        options={[
                            { label: "All Categories", value: "" },
                            ...categories.map((c) => ({ label: c, value: c })),
                        ]}
                        value={selectedCategory || ""}
                        onChange={(val) => {
                            setSelectedCategory(val || null);
                            updateParams(search, val || null);
                        }}
                        placeholder="Filter Commands by Category"
                        className="w-full md:w-64"
                    />
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredCommands.map((cmd) => (
                    <GlowCard
                        key={cmd.name}
                        className={`border-neutral-800 bg-neutral-900/50 backdrop-blur-sm transition-opacity ${
                            !cmd.enabled ? "opacity-50" : ""
                        }`}
                    >
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <IconCommand className="h-4 w-4 text-green-400" />
                                    <CardTitle className="text-base text-white">
                                        /{cmd.name}
                                    </CardTitle>
                                </div>
                                <Switch
                                    checked={cmd.enabled}
                                    onCheckedChange={() => toggleCommand(cmd.name, cmd.enabled)}
                                />
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <p className="text-sm text-neutral-400">
                                {cmd.description || "No description"}
                            </p>
                            <span className="rounded-full bg-neutral-700 px-2 py-0.5 text-xs text-neutral-300">
                                {cmd.category}
                            </span>
                        </CardContent>
                    </GlowCard>
                ))}
            </div>

            {filteredCommands.length === 0 && (
                <div className="py-12 text-center">
                    <IconFilter className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                    <p className="text-neutral-400">No commands found</p>
                    <p className="text-sm text-neutral-500">Try adjusting your search or filters</p>
                </div>
            )}
        </div>
    );
}
