"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { IconSearch, IconCommand, IconFilter, IconAlertCircle } from "@tabler/icons-react";
import { api, type Command } from "@/lib/api";
import { useToast } from "@/components/ui/toast";

export default function CommandsPage() {
    const [commands, setCommands] = useState<Command[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
    const toast = useToast();

    useEffect(() => {
        async function fetchCommands() {
            try {
                setLoading(true);
                const data = await api.getCommands();
                setCommands(data.commands);
                setError(null);
            } catch (err) {
                setError("Failed to load commands. Is the API server running?");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchCommands();
    }, []);

    const categories = Array.from(new Set(commands.map((c) => c.category)));

    const filteredCommands = commands.filter((cmd) => {
        const matchesSearch = cmd.name.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = !selectedCategory || cmd.category === selectedCategory;
        return matchesSearch && matchesCategory;
    });

    const toggleCommand = async (name: string, currentEnabled: boolean) => {
        const newEnabled = !currentEnabled;

        setCommands((prev) =>
            prev.map((cmd) =>
                cmd.name === name ? { ...cmd, enabled: newEnabled } : cmd
            )
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
                prev.map((cmd) =>
                    cmd.name === name ? { ...cmd, enabled: currentEnabled } : cmd
                )
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
                    <p className="text-neutral-400 mt-1">Loading commands...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <Card key={i} className="bg-neutral-800/50 border-neutral-700">
                            <CardContent className="py-6">
                                <div className="h-4 w-24 bg-neutral-700 animate-pulse rounded mb-2" />
                                <div className="h-3 w-32 bg-neutral-700 animate-pulse rounded" />
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
                    <p className="text-neutral-400 mt-1">Enable or disable bot commands</p>
                </div>
                <Card className="bg-red-900/30 border-red-700/50">
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
            <div>
                <h1 className="text-3xl font-bold text-white">Commands</h1>
                <p className="text-neutral-400 mt-1">
                    Enable or disable bot commands ({enabledCount}/{commands.length} enabled)
                </p>
            </div>

            <div className="flex flex-col md:flex-row gap-4">
                <div className="relative flex-1">
                    <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                    <Input
                        placeholder="Search commands..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-10 bg-neutral-800 border-neutral-700 text-white"
                    />
                </div>
                <div className="flex gap-2 flex-wrap">
                    <button
                        onClick={() => setSelectedCategory(null)}
                        className={`px-3 py-2 rounded-lg text-sm transition-colors ${!selectedCategory
                            ? "bg-green-600 text-white"
                            : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                            }`}
                    >
                        All
                    </button>
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setSelectedCategory(cat)}
                            className={`px-3 py-2 rounded-lg text-sm transition-colors ${selectedCategory === cat
                                ? "bg-green-600 text-white"
                                : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredCommands.map((cmd) => (
                    <GlowCard
                        key={cmd.name}
                        className={`bg-neutral-900/50 backdrop-blur-sm border-neutral-800 transition-opacity ${!cmd.enabled ? "opacity-50" : ""
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
                            <p className="text-sm text-neutral-400">{cmd.description || "No description"}</p>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-neutral-700 text-neutral-300">
                                {cmd.category}
                            </span>
                        </CardContent>
                    </GlowCard>
                ))}
            </div>

            {filteredCommands.length === 0 && (
                <div className="text-center py-12">
                    <IconFilter className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                    <p className="text-neutral-400">No commands found</p>
                    <p className="text-sm text-neutral-500">Try adjusting your search or filters</p>
                </div>
            )}
        </div>
    );
}
