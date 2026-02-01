"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { IconSearch, IconUsers, IconSettings, IconLink, IconShield, IconMessage, IconAlertCircle } from "@tabler/icons-react";
import { api, type Group } from "@/lib/api";
import { useToast } from "@/components/ui/toast";

export default function GroupsPage() {
    const [groups, setGroups] = useState<Group[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const toast = useToast();

    useEffect(() => {
        async function fetchGroups() {
            try {
                setLoading(true);
                const data = await api.getGroups();
                setGroups(data.groups);
                setError(null);
            } catch (err) {
                setError("Failed to load groups. Is the API server running?");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchGroups();
    }, []);

    const filteredGroups = groups.filter((g) =>
        g.name.toLowerCase().includes(search.toLowerCase())
    );

    const updateGroupSetting = async (groupId: string, setting: keyof Group["settings"], value: boolean) => {
        const group = groups.find(g => g.id === groupId);
        if (!group) return;

        const newSettings = { ...group.settings, [setting]: value };

        setGroups((prev) =>
            prev.map((g) =>
                g.id === groupId
                    ? { ...g, settings: newSettings }
                    : g
            )
        );
        if (selectedGroup?.id === groupId) {
            setSelectedGroup((prev) =>
                prev ? { ...prev, settings: newSettings } : null
            );
        }

        try {
            await api.updateGroup(groupId, newSettings);
            toast.success("Group updated", `${setting} setting changed`);
        } catch (err) {
            setGroups((prev) =>
                prev.map((g) =>
                    g.id === groupId
                        ? { ...g, settings: group.settings }
                        : g
                )
            );
            toast.error("Failed to update", "Could not change group setting");
            console.error("Failed to update group:", err);
        }
    };

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Groups</h1>
                    <p className="text-neutral-400 mt-1">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="bg-neutral-800/50 border-neutral-700">
                            <CardContent className="py-6">
                                <div className="h-10 w-10 bg-neutral-700 animate-pulse rounded-full mb-2" />
                                <div className="h-4 w-24 bg-neutral-700 animate-pulse rounded" />
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
                    <p className="text-neutral-400 mt-1">Manage groups where the bot is active</p>
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
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white">Groups</h1>
                <p className="text-neutral-400 mt-1">
                    Manage groups where the bot is active ({groups.length} groups)
                </p>
            </div>

            {groups.length === 0 ? (
                <Card className="bg-neutral-800/50 border-neutral-700">
                    <CardContent className="py-12 text-center">
                        <IconUsers className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                        <p className="text-neutral-400">No groups found</p>
                        <p className="text-sm text-neutral-500">Groups will appear here once the bot joins them</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-6 lg:grid-cols-3">
                    {/* Groups List */}
                    <div className="lg:col-span-2 space-y-4">
                        {/* Search */}
                        <div className="relative">
                            <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                            <Input
                                placeholder="Search groups..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-10 bg-neutral-800 border-neutral-700 text-white"
                            />
                        </div>

                        {/* Group Cards */}
                        <div className="grid gap-4 md:grid-cols-2">
                            {filteredGroups.map((group) => (
                                <Card
                                    key={group.id}
                                    className={`bg-neutral-800/50 border-neutral-700 cursor-pointer transition-all hover:border-green-600/50 ${selectedGroup?.id === group.id ? "border-green-600 ring-1 ring-green-600" : ""
                                        }`}
                                    onClick={() => setSelectedGroup(group)}
                                >
                                    <CardContent className="pt-4">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center text-white font-bold">
                                                    {group.name.charAt(0)}
                                                </div>
                                                <div>
                                                    <h3 className="font-semibold text-white">{group.name}</h3>
                                                    <p className="text-xs text-neutral-500 flex items-center gap-1">
                                                        <IconUsers className="h-3 w-3" />
                                                        {group.memberCount} members
                                                    </p>
                                                </div>
                                            </div>
                                            {group.isAdmin && (
                                                <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400">
                                                    Admin
                                                </span>
                                            )}
                                        </div>

                                        {/* Quick settings indicators */}
                                        <div className="flex gap-2">
                                            {group.settings.antilink && (
                                                <span className="px-2 py-0.5 text-xs rounded bg-neutral-700 text-neutral-300 flex items-center gap-1">
                                                    <IconLink className="h-3 w-3" /> Anti-Link
                                                </span>
                                            )}
                                            {group.settings.welcome && (
                                                <span className="px-2 py-0.5 text-xs rounded bg-neutral-700 text-neutral-300 flex items-center gap-1">
                                                    <IconMessage className="h-3 w-3" /> Welcome
                                                </span>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>

                    {/* Group Details Panel */}
                    <div className="lg:col-span-1">
                        {selectedGroup ? (
                            <Card className="bg-neutral-800/50 border-neutral-700 sticky top-6">
                                <CardHeader>
                                    <div className="flex items-center gap-3">
                                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center text-white font-bold text-lg">
                                            {selectedGroup.name.charAt(0)}
                                        </div>
                                        <div>
                                            <CardTitle className="text-white">{selectedGroup.name}</CardTitle>
                                            <CardDescription>{selectedGroup.memberCount} members</CardDescription>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    <div className="space-y-4">
                                        <h4 className="text-sm font-medium text-white flex items-center gap-2">
                                            <IconSettings className="h-4 w-4" />
                                            Group Settings
                                        </h4>

                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-white">Anti-Link</p>
                                                    <p className="text-xs text-neutral-500">Remove messages with links</p>
                                                </div>
                                                <Switch
                                                    checked={selectedGroup.settings.antilink}
                                                    onCheckedChange={(checked) =>
                                                        updateGroupSetting(selectedGroup.id, "antilink", checked)
                                                    }
                                                    disabled={!selectedGroup.isAdmin}
                                                />
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-white">Welcome Messages</p>
                                                    <p className="text-xs text-neutral-500">Greet new members</p>
                                                </div>
                                                <Switch
                                                    checked={selectedGroup.settings.welcome}
                                                    onCheckedChange={(checked) =>
                                                        updateGroupSetting(selectedGroup.id, "welcome", checked)
                                                    }
                                                    disabled={!selectedGroup.isAdmin}
                                                />
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-white">Mute Bot</p>
                                                    <p className="text-xs text-neutral-500">Disable bot in this group</p>
                                                </div>
                                                <Switch
                                                    checked={selectedGroup.settings.mute}
                                                    onCheckedChange={(checked) =>
                                                        updateGroupSetting(selectedGroup.id, "mute", checked)
                                                    }
                                                    disabled={!selectedGroup.isAdmin}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {!selectedGroup.isAdmin && (
                                        <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                                            <p className="text-xs text-yellow-400 flex items-center gap-2">
                                                <IconShield className="h-4 w-4" />
                                                Bot is not admin in this group
                                            </p>
                                        </div>
                                    )}

                                    <Button variant="outline" className="w-full" disabled={!selectedGroup.isAdmin}>
                                        Leave Group
                                    </Button>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card className="bg-neutral-800/50 border-neutral-700">
                                <CardContent className="py-12 text-center">
                                    <IconUsers className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                                    <p className="text-neutral-400">Select a group</p>
                                    <p className="text-sm text-neutral-500">Click a group to view settings</p>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
