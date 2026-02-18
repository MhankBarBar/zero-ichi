"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { api, type Group } from "@/lib/api";
import {
    IconDeviceFloppy,
    IconHeart,
    IconHeartBroken,
    IconSearch,
    IconUsers,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";

export default function WelcomeGoodbyePage() {
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const toast = useToast();

    const [welcomeEnabled, setWelcomeEnabled] = useState(false);
    const [welcomeMessage, setWelcomeMessage] = useState("");
    const [goodbyeEnabled, setGoodbyeEnabled] = useState(false);
    const [goodbyeMessage, setGoodbyeMessage] = useState("");

    const fetchGroups = useCallback(async () => {
        try {
            const data = await api.getGroups();
            setGroups(data.groups || []);
        } catch (err) {
            toast.error("Failed to fetch", "Could not load groups");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    const fetchWelcomeGoodbye = useCallback(async (groupId: string) => {
        try {
            const [welcomeData, goodbyeData] = await Promise.all([
                api.getWelcome(groupId).catch(() => ({ enabled: false, message: "" })),
                api.getGoodbye(groupId).catch(() => ({ enabled: false, message: "" })),
            ]);

            setWelcomeEnabled(welcomeData?.enabled || false);
            setWelcomeMessage(welcomeData?.message || "");
            setGoodbyeEnabled(goodbyeData?.enabled || false);
            setGoodbyeMessage(goodbyeData?.message || "");
        } catch (err) {
            console.error("Failed to fetch welcome/goodbye:", err);
        }
    }, []);

    useEffect(() => {
        fetchGroups();
    }, [fetchGroups]);

    useEffect(() => {
        if (selectedGroup) {
            fetchWelcomeGoodbye(selectedGroup.id);
        }
    }, [selectedGroup]);

    const handleSelectGroup = (group: Group) => {
        setSelectedGroup(group);
    };

    const handleSaveWelcome = async () => {
        if (!selectedGroup) return;
        setSaving(true);
        try {
            await api.updateWelcome(selectedGroup.id, {
                enabled: welcomeEnabled,
                message: welcomeMessage,
            });
            toast.success("Saved", "Welcome message updated successfully");
        } catch (err) {
            toast.error("Failed", "Could not save welcome message");
        } finally {
            setSaving(false);
        }
    };

    const handleSaveGoodbye = async () => {
        if (!selectedGroup) return;
        setSaving(true);
        try {
            await api.updateGoodbye(selectedGroup.id, {
                enabled: goodbyeEnabled,
                message: goodbyeMessage,
            });
            toast.success("Saved", "Goodbye message updated successfully");
        } catch (err) {
            toast.error("Failed", "Could not save goodbye message");
        } finally {
            setSaving(false);
        }
    };

    const filteredGroups = groups.filter((g) =>
        g.name.toLowerCase().includes(searchTerm.toLowerCase()),
    );

    const placeholderHelp = [
        { placeholder: "{name}", description: "User's name" },
        { placeholder: "{mention}", description: "Mention the user" },
        { placeholder: "{group}", description: "Group name" },
        { placeholder: "{count}", description: "Member count" },
    ];

    return (
        <div className="space-y-8">
            <div>
                <motion.h1
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-3xl font-bold text-white"
                >
                    Welcome & Goodbye
                </motion.h1>
                <p className="mt-1 text-neutral-500">
                    Customize messages for when members join or leave groups
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                <div className="space-y-4 md:col-span-1">
                    <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                        <CardHeader className="pb-4">
                            <CardTitle className="flex items-center gap-2 text-lg">
                                <IconUsers className="h-5 w-5 text-blue-400" />
                                Select Group
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="relative">
                                <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                                <Input
                                    placeholder="Search groups..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="border-neutral-700 bg-neutral-800 pl-10"
                                />
                            </div>

                            <div className="max-h-96 space-y-2 overflow-y-auto">
                                {loading ? (
                                    [...Array(5)].map((_, i) => (
                                        <div
                                            key={i}
                                            className="h-12 animate-pulse rounded-lg bg-neutral-800"
                                        />
                                    ))
                                ) : filteredGroups.length === 0 ? (
                                    <p className="py-4 text-center text-sm text-neutral-500">
                                        No groups found
                                    </p>
                                ) : (
                                    filteredGroups.map((group) => (
                                        <motion.button
                                            key={group.id}
                                            onClick={() => handleSelectGroup(group)}
                                            className={`w-full rounded-lg p-3 text-left transition-all ${
                                                selectedGroup?.id === group.id
                                                    ? "border border-blue-500/50 bg-blue-600/20"
                                                    : "border border-transparent bg-neutral-800 hover:bg-neutral-700"
                                            }`}
                                            whileHover={{ scale: 1.01 }}
                                            whileTap={{ scale: 0.99 }}
                                        >
                                            <p className="truncate font-medium text-white">
                                                {group.name}
                                            </p>
                                            <p className="text-xs text-neutral-500">
                                                {group.memberCount} members
                                            </p>
                                        </motion.button>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </GlowCard>
                </div>

                <div className="space-y-6 md:col-span-2">
                    <AnimatePresence mode="wait">
                        {!selectedGroup ? (
                            <motion.div
                                key="empty"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex flex-col items-center justify-center py-20 text-neutral-500"
                            >
                                <IconUsers className="mb-4 h-16 w-16 opacity-50" />
                                <p className="text-lg">Select a group to edit messages</p>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="editor"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-6"
                            >
                                <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                                    <CardHeader className="pb-4">
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="flex items-center gap-2 text-lg">
                                                <IconHeart className="h-5 w-5 text-green-400" />
                                                Welcome Message
                                            </CardTitle>
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-neutral-400">
                                                    {welcomeEnabled ? "Enabled" : "Disabled"}
                                                </span>
                                                <Switch
                                                    checked={welcomeEnabled}
                                                    onCheckedChange={setWelcomeEnabled}
                                                />
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <textarea
                                            placeholder="Welcome message for new members..."
                                            value={welcomeMessage}
                                            onChange={(e) => setWelcomeMessage(e.target.value)}
                                            className="min-h-[120px] w-full resize-none rounded-xl border border-neutral-700 bg-neutral-800 p-4 text-base text-white transition-all focus:ring-2 focus:ring-green-500/50 focus:outline-none"
                                        />
                                        <div className="flex justify-end">
                                            <Button
                                                onClick={handleSaveWelcome}
                                                disabled={saving}
                                                className="gap-2 bg-green-600 hover:bg-green-500"
                                            >
                                                <IconDeviceFloppy className="h-4 w-4" />
                                                Save Welcome
                                            </Button>
                                        </div>
                                    </CardContent>
                                </GlowCard>

                                <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                                    <CardHeader className="pb-4">
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="flex items-center gap-2 text-lg">
                                                <IconHeartBroken className="h-5 w-5 text-red-400" />
                                                Goodbye Message
                                            </CardTitle>
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-neutral-400">
                                                    {goodbyeEnabled ? "Enabled" : "Disabled"}
                                                </span>
                                                <Switch
                                                    checked={goodbyeEnabled}
                                                    onCheckedChange={setGoodbyeEnabled}
                                                />
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <textarea
                                            placeholder="Goodbye message when members leave..."
                                            value={goodbyeMessage}
                                            onChange={(e) => setGoodbyeMessage(e.target.value)}
                                            className="min-h-[120px] w-full resize-none rounded-xl border border-neutral-700 bg-neutral-800 p-4 text-base text-white transition-all focus:ring-2 focus:ring-red-500/50 focus:outline-none"
                                        />
                                        <div className="flex justify-end">
                                            <Button
                                                onClick={handleSaveGoodbye}
                                                disabled={saving}
                                                className="gap-2 bg-red-600 hover:bg-red-500"
                                            >
                                                <IconDeviceFloppy className="h-4 w-4" />
                                                Save Goodbye
                                            </Button>
                                        </div>
                                    </CardContent>
                                </GlowCard>

                                <Card className="border-neutral-800 bg-neutral-900/30">
                                    <CardContent className="p-4">
                                        <p className="mb-3 text-sm font-medium text-neutral-400">
                                            Available Placeholders
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            {placeholderHelp.map((p) => (
                                                <div
                                                    key={p.placeholder}
                                                    className="flex items-center gap-2 rounded-lg bg-neutral-800 px-3 py-1.5"
                                                >
                                                    <code className="text-sm text-blue-400">
                                                        {p.placeholder}
                                                    </code>
                                                    <span className="text-xs text-neutral-500">
                                                        {p.description}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
