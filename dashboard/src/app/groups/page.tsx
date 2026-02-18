"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { api, type Group } from "@/lib/api";
import {
    IconAlertCircle,
    IconLink,
    IconMessage,
    IconRefresh,
    IconSearch,
    IconSettings,
    IconShield,
    IconUsers,
    IconX,
} from "@tabler/icons-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useWebSocket } from "@/hooks/use-websocket";

export default function GroupsPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [groups, setGroups] = useState<Group[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState(searchParams.get("q") || "");
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
    const [refreshing, setRefreshing] = useState(false);
    const toast = useToast();

    const updateSearch = useCallback(
        (q: string) => {
            const params = new URLSearchParams();
            if (q) params.set("q", q);
            const qs = params.toString();
            router.replace(qs ? `?${qs}` : "?", { scroll: false });
        },
        [router],
    );

    const fetchGroups = useCallback(async (isRefresh = false) => {
        try {
            if (isRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            const data = await api.getGroups();
            setGroups(data.groups);
            setError(null);
        } catch (err: unknown) {
            setError("Failed to load groups. Is the API server running?");
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        fetchGroups();
    }, [fetchGroups]);

    const handleRefresh = () => {
        fetchGroups(true);
    };

    const { lastEvent } = useWebSocket();

    useEffect(() => {
        if (!lastEvent || lastEvent.type !== "group_update") return;
        const data = lastEvent.data as {
            action: string;
            group_id: string;
            settings?: Partial<Group["settings"]>;
            setting?: string;
            value?: boolean;
            group_ids?: string[];
        };
        const { action } = data;

        if (action === "leave") {
            setGroups((prev) => prev.filter((g) => g.id !== data.group_id));
            setSelectedGroup((prev) => (prev?.id === data.group_id ? null : prev));
        } else if (action === "update") {
            setGroups((prev) =>
                prev.map((g) =>
                    g.id === data.group_id
                        ? { ...g, settings: { ...g.settings, ...data.settings } }
                        : g,
                ),
            );
            setSelectedGroup((prev) => {
                if (!prev || prev.id !== data.group_id) return prev;
                return { ...prev, settings: { ...prev.settings, ...data.settings } };
            });
        } else if (action === "bulk_update") {
            const { group_ids, setting, value } = data;
            if (group_ids && setting) {
                setGroups((prev) =>
                    prev.map((g) => {
                        if (group_ids.includes(g.id)) {
                            return { ...g, settings: { ...g.settings, [setting]: value } };
                        }
                        return g;
                    }),
                );
                setSelectedGroup((prev) => {
                    if (prev && group_ids.includes(prev.id)) {
                        return { ...prev, settings: { ...prev.settings, [setting]: value } };
                    }
                    return prev;
                });
            }
        }
    }, [lastEvent]);

    const filteredGroups = groups.filter((g) =>
        g.name.toLowerCase().includes(search.toLowerCase()),
    );

    const updateGroupSetting = async (
        groupId: string,
        setting: keyof Group["settings"],
        value: boolean,
    ) => {
        const group = groups.find((g) => g.id === groupId);
        if (!group) return;

        const newSettings = { ...group.settings, [setting]: value };

        setGroups((prev) =>
            prev.map((g) => (g.id === groupId ? { ...g, settings: newSettings } : g)),
        );
        if (selectedGroup?.id === groupId) {
            setSelectedGroup((prev) => (prev ? { ...prev, settings: newSettings } : null));
        }

        try {
            await api.updateGroup(groupId, newSettings);
            toast.success("Group updated", `${setting} setting changed`);
        } catch (err: unknown) {
            setGroups((prev) =>
                prev.map((g) => (g.id === groupId ? { ...g, settings: group.settings } : g)),
            );
            toast.error("Failed to update", "Could not change group setting");
            console.error("Failed to update group:", err);
        }
    };

    const toggleGroupSelection = (groupId: string) => {
        const newSelected = new Set(selectedGroups);
        if (newSelected.has(groupId)) {
            newSelected.delete(groupId);
        } else {
            newSelected.add(groupId);
        }
        setSelectedGroups(newSelected);
    };

    const toggleSelectAll = () => {
        if (selectedGroups.size === filteredGroups.length) {
            setSelectedGroups(new Set());
        } else {
            setSelectedGroups(new Set(filteredGroups.map((g) => g.id)));
        }
    };

    const handleBulkAction = async (action: "antilink" | "welcome" | "mute", value: boolean) => {
        const groupIds = Array.from(selectedGroups);
        if (groupIds.length === 0) return;

        const updates = new Map<string, Group>();
        setGroups((prev) =>
            prev.map((g) => {
                if (selectedGroups.has(g.id)) {
                    const updated = { ...g, settings: { ...g.settings, [action]: value } };
                    updates.set(g.id, updated);
                    return updated;
                }
                return g;
            }),
        );

        try {
            await api.bulkUpdateGroups(groupIds, action, value);
            toast.success(
                "Bulk update successful",
                `Updated ${action} for ${groupIds.length} groups`,
            );
            setSelectedGroups(new Set());
        } catch (err: unknown) {
            setGroups((prev) =>
                prev.map((g) => {
                    if (selectedGroups.has(g.id)) {
                        const original = updates.get(g.id);
                        return original
                            ? { ...original, settings: { ...original.settings, [action]: !value } }
                            : g;
                    }
                    return g;
                }),
            );
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Bulk update failed", message);
        }
    };

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Groups</h1>
                    <p className="mt-1 text-neutral-400">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="py-6">
                                <div className="mb-2 h-10 w-10 animate-pulse rounded-full bg-neutral-700" />
                                <div className="h-4 w-24 animate-pulse rounded bg-neutral-700" />
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
                    <h1 className="text-3xl font-bold text-white">Groups</h1>
                    <p className="mt-1 text-neutral-400">Manage groups where the bot is active</p>
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
            {groups.length === 0 ? (
                <div className="space-y-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white">Groups</h1>
                        <p className="mt-1 text-neutral-400">
                            Manage groups where the bot is active
                        </p>
                    </div>
                    <Card className="border-neutral-700 bg-neutral-800/50">
                        <CardContent className="py-12 text-center">
                            <IconUsers className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                            <p className="text-neutral-400">No groups found</p>
                            <p className="text-sm text-neutral-500">
                                Groups will appear here once the bot joins them
                            </p>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                <div className="grid gap-6 lg:grid-cols-3">
                    <div className="space-y-4 lg:col-span-2">
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-3xl font-bold tracking-tight text-white">
                                    Groups
                                </h1>
                                <p className="mt-1 text-neutral-400">
                                    Manage {groups.length} active groups
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    onClick={handleRefresh}
                                    disabled={refreshing}
                                    className="gap-2 border-neutral-700 text-neutral-400 hover:text-white"
                                >
                                    <IconRefresh
                                        className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
                                    />
                                    <span className="hidden sm:inline">Refresh</span>
                                </Button>
                                <Button
                                    variant={selectedGroups.size > 0 ? "secondary" : "outline"}
                                    onClick={toggleSelectAll}
                                    className={
                                        selectedGroups.size > 0
                                            ? "bg-white text-black hover:bg-neutral-200"
                                            : "border-neutral-700 text-neutral-400 hover:text-white"
                                    }
                                >
                                    {selectedGroups.size === filteredGroups.length
                                        ? "Deselect All"
                                        : "Select All"}
                                </Button>
                            </div>
                        </div>

                        <div className="group relative">
                            <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500 transition-colors group-focus-within:text-white" />
                            <Input
                                placeholder="Search groups..."
                                value={search}
                                onChange={(e) => {
                                    setSearch(e.target.value);
                                    updateSearch(e.target.value);
                                }}
                                className="border-neutral-800 bg-neutral-900 pl-9 text-white placeholder-neutral-500 transition-all focus:border-neutral-600"
                            />
                        </div>

                        {selectedGroups.size > 0 && (
                            <div className="animate-in slide-in-from-bottom-6 fade-in fixed right-4 bottom-6 left-4 z-50 flex items-center justify-between gap-4 rounded-2xl border border-neutral-700/50 bg-neutral-900/90 px-4 py-3 shadow-2xl backdrop-blur-md duration-300 md:right-auto md:left-1/2 md:w-auto md:-translate-x-1/2 md:justify-start md:gap-6 md:px-6 md:py-4">
                                <div className="flex items-center gap-3 border-r border-neutral-700 pr-4 md:pr-6">
                                    <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                                    <span className="text-sm font-semibold whitespace-nowrap text-white">
                                        {selectedGroups.size}{" "}
                                        <span className="hidden md:inline">selected</span>
                                    </span>
                                </div>
                                <div className="flex items-center gap-1 md:gap-2">
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="px-2 text-neutral-400 hover:bg-neutral-800 hover:text-white md:px-4"
                                        onClick={() => handleBulkAction("antilink", true)}
                                    >
                                        <IconLink className="h-4 w-4 md:mr-2" />{" "}
                                        <span className="hidden md:inline">Anti-Link</span>
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="px-2 text-neutral-400 hover:bg-neutral-800 hover:text-white md:px-4"
                                        onClick={() => handleBulkAction("welcome", true)}
                                    >
                                        <IconMessage className="h-4 w-4 md:mr-2" />{" "}
                                        <span className="hidden md:inline">Welcome</span>
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="px-2 text-neutral-400 hover:bg-neutral-800 hover:text-white md:px-4"
                                        onClick={() => handleBulkAction("mute", true)}
                                    >
                                        <IconAlertCircle className="h-4 w-4 md:mr-2" />{" "}
                                        <span className="hidden md:inline">Mute</span>
                                    </Button>
                                </div>
                                <Button
                                    size="icon"
                                    variant="ghost"
                                    className="-mr-2 h-8 w-8 rounded-full text-neutral-500 hover:bg-red-950/30 hover:text-red-400"
                                    onClick={() => setSelectedGroups(new Set())}
                                >
                                    <IconX className="h-4 w-4" />
                                </Button>
                            </div>
                        )}

                        <div className="grid gap-4 pb-24 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
                            {filteredGroups.map((group) => {
                                const isSelected = selectedGroups.has(group.id);
                                const isViewed = selectedGroup?.id === group.id;
                                return (
                                    <div
                                        key={group.id}
                                        onClick={() => setSelectedGroup(group)}
                                        className={`group relative cursor-pointer overflow-hidden rounded-xl border transition-all duration-200 ${
                                            isSelected
                                                ? "border-green-500/50 bg-neutral-900 shadow-[0_0_0_1px_rgba(34,197,94,0.3)]"
                                                : isViewed
                                                  ? "border-blue-500/50 bg-neutral-900 ring-1 ring-blue-500/50"
                                                  : "border-neutral-800 bg-neutral-900/40 hover:border-neutral-700 hover:bg-neutral-900/60"
                                        } `}
                                    >
                                        <div className="p-5">
                                            <div className="mb-4 flex items-start justify-between">
                                                <div
                                                    className={`flex h-10 w-10 items-center justify-center rounded-lg text-sm font-bold ${isSelected ? "bg-green-500/20 text-green-400" : isViewed ? "bg-blue-500/20 text-blue-400" : "bg-neutral-800 text-neutral-400"} `}
                                                >
                                                    {group.name.slice(0, 2).toUpperCase()}
                                                </div>
                                                <div onClick={(e) => e.stopPropagation()}>
                                                    <Checkbox
                                                        checked={isSelected}
                                                        onCheckedChange={() =>
                                                            toggleGroupSelection(group.id)
                                                        }
                                                        className={`transition-opacity duration-200 ${isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-100"} data-[state=checked]:border-green-500 data-[state=checked]:bg-green-500`}
                                                    />
                                                </div>
                                            </div>

                                            <h3 className="mb-1 truncate pr-2 font-medium text-white">
                                                {group.name}
                                            </h3>
                                            <div className="mb-4 flex items-center gap-2 text-xs text-neutral-500">
                                                <span className="flex items-center gap-1">
                                                    <IconUsers className="h-3 w-3" />
                                                    {group.memberCount}
                                                </span>
                                                {group.isAdmin && (
                                                    <span className="flex items-center gap-1 rounded-full bg-green-500/10 px-1.5 py-0.5 text-green-500/80">
                                                        <IconShield className="h-3 w-3" />
                                                        Admin
                                                    </span>
                                                )}
                                            </div>

                                            <div
                                                className="mt-4 space-y-3"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2 text-sm text-neutral-400">
                                                        <IconLink className="h-4 w-4" />
                                                        <span>Anti-Link</span>
                                                    </div>
                                                    <Switch
                                                        checked={group.settings.antilink}
                                                        onCheckedChange={(c) =>
                                                            updateGroupSetting(
                                                                group.id,
                                                                "antilink",
                                                                c,
                                                            )
                                                        }
                                                        className="data-[state=checked]:bg-green-500"
                                                    />
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2 text-sm text-neutral-400">
                                                        <IconMessage className="h-4 w-4" />
                                                        <span>Welcome</span>
                                                    </div>
                                                    <Switch
                                                        checked={group.settings.welcome}
                                                        onCheckedChange={(c) =>
                                                            updateGroupSetting(
                                                                group.id,
                                                                "welcome",
                                                                c,
                                                            )
                                                        }
                                                        className="data-[state=checked]:bg-green-500"
                                                    />
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2 text-sm text-neutral-400">
                                                        <IconAlertCircle className="h-4 w-4" />
                                                        <span>Mute</span>
                                                    </div>
                                                    <Switch
                                                        checked={group.settings.mute}
                                                        onCheckedChange={(c) =>
                                                            updateGroupSetting(group.id, "mute", c)
                                                        }
                                                        className="data-[state=checked]:bg-red-500"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div className="lg:col-span-1">
                        {selectedGroup ? (
                            <Card className="sticky top-6 border-neutral-700 bg-neutral-800/50">
                                <CardHeader>
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-green-400 to-blue-500 text-lg font-bold text-white">
                                            {selectedGroup.name.charAt(0)}
                                        </div>
                                        <div>
                                            <CardTitle className="text-white">
                                                {selectedGroup.name}
                                            </CardTitle>
                                            <CardDescription>
                                                {selectedGroup.memberCount} members
                                            </CardDescription>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    <div className="space-y-4">
                                        <h4 className="flex items-center gap-2 text-sm font-medium text-white">
                                            <IconSettings className="h-4 w-4" />
                                            Group Settings
                                        </h4>

                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-white">Anti-Link</p>
                                                    <p className="text-xs text-neutral-500">
                                                        Remove messages with links
                                                    </p>
                                                </div>
                                                <Switch
                                                    checked={selectedGroup.settings.antilink}
                                                    onCheckedChange={(checked) =>
                                                        updateGroupSetting(
                                                            selectedGroup.id,
                                                            "antilink",
                                                            checked,
                                                        )
                                                    }
                                                    disabled={!selectedGroup.isAdmin}
                                                />
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-white">
                                                        Welcome Messages
                                                    </p>
                                                    <p className="text-xs text-neutral-500">
                                                        Greet new members
                                                    </p>
                                                </div>
                                                <Switch
                                                    checked={selectedGroup.settings.welcome}
                                                    onCheckedChange={(checked) =>
                                                        updateGroupSetting(
                                                            selectedGroup.id,
                                                            "welcome",
                                                            checked,
                                                        )
                                                    }
                                                    disabled={!selectedGroup.isAdmin}
                                                />
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-white">Mute Bot</p>
                                                    <p className="text-xs text-neutral-500">
                                                        Disable bot in this group
                                                    </p>
                                                </div>
                                                <Switch
                                                    checked={selectedGroup.settings.mute}
                                                    onCheckedChange={(checked) =>
                                                        updateGroupSetting(
                                                            selectedGroup.id,
                                                            "mute",
                                                            checked,
                                                        )
                                                    }
                                                    disabled={!selectedGroup.isAdmin}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {!selectedGroup.isAdmin && (
                                        <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-3">
                                            <p className="flex items-center gap-2 text-xs text-yellow-400">
                                                <IconShield className="h-4 w-4" />
                                                Bot is not admin in this group
                                            </p>
                                        </div>
                                    )}

                                    <Button
                                        variant="outline"
                                        className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                                        onClick={async () => {
                                            if (
                                                !confirm(
                                                    `Leave group "${selectedGroup.name}"? This cannot be undone.`,
                                                )
                                            )
                                                return;
                                            try {
                                                await api.leaveGroup(selectedGroup.id);
                                                toast.success("Left group", selectedGroup.name);
                                                setGroups((prev) =>
                                                    prev.filter((g) => g.id !== selectedGroup.id),
                                                );
                                                setSelectedGroup(null);
                                            } catch (err) {
                                                toast.error("Failed to leave group", String(err));
                                            }
                                        }}
                                    >
                                        Leave Group
                                    </Button>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card className="border-neutral-700 bg-neutral-800/50">
                                <CardContent className="py-12 text-center">
                                    <IconUsers className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                                    <p className="text-neutral-400">Select a group</p>
                                    <p className="text-sm text-neutral-500">
                                        Click a group to view settings
                                    </p>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
