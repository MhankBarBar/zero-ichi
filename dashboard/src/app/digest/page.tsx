"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CustomSelect } from "@/components/ui/custom-select";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { api, type DigestConfig, type Group } from "@/lib/api";
import {
    IconAlertCircle,
    IconCalendarEvent,
    IconRefresh,
    IconSend,
    IconUsers,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";

const periodOptions = [
    { label: "Daily", value: "daily" },
    { label: "Weekly", value: "weekly" },
];

const dayOptions = [
    { label: "Sunday", value: "sun" },
    { label: "Monday", value: "mon" },
    { label: "Tuesday", value: "tue" },
    { label: "Wednesday", value: "wed" },
    { label: "Thursday", value: "thu" },
    { label: "Friday", value: "fri" },
    { label: "Saturday", value: "sat" },
];

export default function DigestPage() {
    const toast = useToast();
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [config, setConfig] = useState<DigestConfig>({
        enabled: false,
        period: "daily",
        day: "sun",
        time: "20:00",
    });
    const [preview, setPreview] = useState("");
    const [loading, setLoading] = useState(true);
    const [groupLoading, setGroupLoading] = useState(false);

    useEffect(() => {
        async function fetchGroups() {
            try {
                setLoading(true);
                const data = await api.getGroups();
                setGroups(data.groups);
            } catch {
                toast.error("Failed to load groups");
            } finally {
                setLoading(false);
            }
        }

        fetchGroups();
    }, [toast]);

    const loadGroup = async (group: Group) => {
        setSelectedGroup(group);
        setGroupLoading(true);
        try {
            const res = await api.getDigest(group.id);
            setConfig(res.config);
            setPreview(res.preview);
        } catch {
            toast.error("Failed to load digest config");
        } finally {
            setGroupLoading(false);
        }
    };

    const refreshPreview = async () => {
        if (!selectedGroup) return;
        try {
            const res = await api.getDigest(selectedGroup.id);
            setPreview(res.preview);
        } catch {
            toast.error("Failed to refresh digest preview");
        }
    };

    const save = async () => {
        if (!selectedGroup) return;
        try {
            const res = await api.updateDigest(selectedGroup.id, config);
            setConfig(res.config);
            await refreshPreview();
            toast.success("Digest settings saved");
        } catch {
            toast.error("Failed to save digest settings");
        }
    };

    const sendNow = async () => {
        if (!selectedGroup) return;
        try {
            await api.sendDigestNow(selectedGroup.id);
            toast.success("Digest queued", "Will be sent shortly");
        } catch {
            toast.error("Failed to trigger digest");
        }
    };

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Digest</h1>
                    <p className="mt-1 text-neutral-400">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="animate-pulse border-neutral-700 bg-neutral-800/50">
                            <CardContent className="p-6">
                                <div className="mb-3 h-5 w-2/3 rounded bg-neutral-700" />
                                <div className="h-4 w-1/2 rounded bg-neutral-700" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold text-white">Digest</h1>
                <p className="mt-1 text-neutral-400">
                    {selectedGroup
                        ? `Configure digest for ${selectedGroup.name}`
                        : "Choose a group to configure daily or weekly summary"}
                </p>
            </div>

            {!selectedGroup ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {groups.map((group) => (
                        <Card
                            key={group.id}
                            className="cursor-pointer border-neutral-700 bg-neutral-800/50 transition-colors hover:border-green-500/50"
                            onClick={() => loadGroup(group)}
                        >
                            <CardContent className="flex items-center gap-4 p-4">
                                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20">
                                    <IconUsers className="h-5 w-5 text-green-300" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <h3 className="truncate font-medium text-white">{group.name}</h3>
                                    <p className="text-sm text-neutral-500">
                                        {group.memberCount} members
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="space-y-6">
                    <div className="flex flex-wrap items-center gap-3">
                        <Button
                            variant="outline"
                            onClick={() => setSelectedGroup(null)}
                            className="border-neutral-700 text-neutral-400"
                        >
                            ← Back to Groups
                        </Button>
                        <Button
                            variant="outline"
                            onClick={refreshPreview}
                            className="border-neutral-700 text-neutral-400"
                        >
                            <IconRefresh className="mr-2 h-4 w-4" /> Refresh Preview
                        </Button>
                        <Button onClick={sendNow} className="bg-emerald-600 hover:bg-emerald-500">
                            <IconSend className="mr-2 h-4 w-4" /> Send Now
                        </Button>
                    </div>

                    <div className="grid gap-6 lg:grid-cols-2">
                        <Card className="border-neutral-700 bg-neutral-800/50">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-white">
                                    <IconCalendarEvent className="h-5 w-5 text-green-400" />
                                    Digest Settings
                                </CardTitle>
                                <CardDescription>
                                    Schedule automatic digest for this group
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-5">
                                <div className="flex items-center justify-between rounded-lg border border-neutral-700 bg-neutral-900/60 p-3">
                                    <div>
                                        <p className="font-medium text-white">Enable digest</p>
                                        <p className="text-xs text-neutral-500">
                                            Turn scheduled digest on or off
                                        </p>
                                    </div>
                                    <Switch
                                        checked={config.enabled}
                                        onCheckedChange={(value) =>
                                            setConfig((prev) => ({ ...prev, enabled: value }))
                                        }
                                    />
                                </div>

                                <div className="grid gap-4 sm:grid-cols-2">
                                    <div className="space-y-2">
                                        <p className="text-sm font-medium text-neutral-300">Period</p>
                                        <CustomSelect
                                            options={periodOptions}
                                            value={config.period}
                                            onChange={(value) =>
                                                setConfig((prev) => ({
                                                    ...prev,
                                                    period: value as "daily" | "weekly",
                                                }))
                                            }
                                            className="w-full"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-sm font-medium text-neutral-300">Day</p>
                                        <CustomSelect
                                            options={dayOptions}
                                            value={config.day}
                                            onChange={(value) =>
                                                setConfig((prev) => ({ ...prev, day: value }))
                                            }
                                            className={`w-full ${config.period !== "weekly" ? "pointer-events-none opacity-50" : ""}`}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <p className="text-sm font-medium text-neutral-300">Time (HH:MM)</p>
                                    <Input
                                        value={config.time}
                                        onChange={(e) =>
                                            setConfig((prev) => ({ ...prev, time: e.target.value }))
                                        }
                                        className="border-neutral-700 bg-neutral-900 text-white"
                                        placeholder="20:00"
                                    />
                                </div>

                                <Button
                                    onClick={save}
                                    disabled={groupLoading}
                                    className="bg-green-600 hover:bg-green-500"
                                >
                                    Save Settings
                                </Button>
                            </CardContent>
                        </Card>

                        <Card className="border-neutral-700 bg-neutral-800/40">
                            <CardHeader>
                                <CardTitle className="text-white">Preview</CardTitle>
                                <CardDescription>
                                    {groupLoading ? "Loading preview..." : "Latest generated digest message"}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {groupLoading ? (
                                    <div className="space-y-2">
                                        <div className="h-4 w-1/3 animate-pulse rounded bg-neutral-700" />
                                        <div className="h-4 w-full animate-pulse rounded bg-neutral-700" />
                                        <div className="h-4 w-2/3 animate-pulse rounded bg-neutral-700" />
                                    </div>
                                ) : preview ? (
                                    <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg border border-neutral-700 bg-neutral-900/70 p-3 text-xs leading-relaxed text-neutral-300">
                                        {preview}
                                    </pre>
                                ) : (
                                    <div className="rounded-lg border border-neutral-700 bg-neutral-900/70 p-4 text-sm text-neutral-500">
                                        No preview available.
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            )}

            {!selectedGroup && groups.length === 0 && (
                <Card className="border-amber-600/30 bg-amber-500/10">
                    <CardContent className="flex items-center gap-2 p-4 text-amber-300">
                        <IconAlertCircle className="h-4 w-4" /> No groups available.
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
