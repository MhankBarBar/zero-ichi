"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
    IconHeart,
    IconHeartBroken,
    IconRefresh,
    IconUsers,
    IconDeviceFloppy,
    IconSearch,
} from "@tabler/icons-react";
import { api, type Group, type WelcomeConfig } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { useToast } from "@/components/ui/toast";

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

    const fetchGroups = async () => {
        try {
            const data = await api.getGroups();
            setGroups(data.groups || []);
        } catch (err) {
            toast.error("Failed to fetch", "Could not load groups");
        } finally {
            setLoading(false);
        }
    };

    const fetchWelcomeGoodbye = async (groupId: string) => {
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
    };

    useEffect(() => {
        fetchGroups();
    }, []);

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

    const filteredGroups = groups.filter(
        (g) => g.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const placeholderHelp = [
        { placeholder: "{name}", description: "User's name" },
        { placeholder: "{mention}", description: "Mention the user" },
        { placeholder: "{group}", description: "Group name" },
        { placeholder: "{count}", description: "Member count" },
    ];

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <motion.h1
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-3xl font-bold text-white"
                >
                    Welcome & Goodbye
                </motion.h1>
                <p className="text-neutral-500 mt-1">
                    Customize messages for when members join or leave groups
                </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
                {/* Group Selection Sidebar */}
                <div className="md:col-span-1 space-y-4">
                    <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <IconUsers className="h-5 w-5 text-blue-400" />
                                Select Group
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* Search */}
                            <div className="relative">
                                <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                                <Input
                                    placeholder="Search groups..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10 bg-neutral-800 border-neutral-700"
                                />
                            </div>

                            {/* Group List */}
                            <div className="space-y-2 max-h-96 overflow-y-auto">
                                {loading ? (
                                    [...Array(5)].map((_, i) => (
                                        <div
                                            key={i}
                                            className="h-12 bg-neutral-800 animate-pulse rounded-lg"
                                        />
                                    ))
                                ) : filteredGroups.length === 0 ? (
                                    <p className="text-neutral-500 text-sm text-center py-4">
                                        No groups found
                                    </p>
                                ) : (
                                    filteredGroups.map((group) => (
                                        <motion.button
                                            key={group.id}
                                            onClick={() => handleSelectGroup(group)}
                                            className={`w-full p-3 rounded-lg text-left transition-all ${selectedGroup?.id === group.id
                                                    ? "bg-blue-600/20 border border-blue-500/50"
                                                    : "bg-neutral-800 hover:bg-neutral-700 border border-transparent"
                                                }`}
                                            whileHover={{ scale: 1.01 }}
                                            whileTap={{ scale: 0.99 }}
                                        >
                                            <p className="text-white font-medium truncate">
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

                {/* Editor Area */}
                <div className="md:col-span-2 space-y-6">
                    <AnimatePresence mode="wait">
                        {!selectedGroup ? (
                            <motion.div
                                key="empty"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex flex-col items-center justify-center py-20 text-neutral-500"
                            >
                                <IconUsers className="h-16 w-16 mb-4 opacity-50" />
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
                                {/* Welcome Message Editor */}
                                <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                    <CardHeader className="pb-4">
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="text-lg flex items-center gap-2">
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
                                            className="w-full min-h-[120px] bg-neutral-800 border border-neutral-700 text-white rounded-xl p-4 text-base focus:outline-none focus:ring-2 focus:ring-green-500/50 transition-all resize-none"
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

                                {/* Goodbye Message Editor */}
                                <GlowCard className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                                    <CardHeader className="pb-4">
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="text-lg flex items-center gap-2">
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
                                            className="w-full min-h-[120px] bg-neutral-800 border border-neutral-700 text-white rounded-xl p-4 text-base focus:outline-none focus:ring-2 focus:ring-red-500/50 transition-all resize-none"
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

                                {/* Placeholder Help */}
                                <Card className="bg-neutral-900/30 border-neutral-800">
                                    <CardContent className="p-4">
                                        <p className="text-sm font-medium text-neutral-400 mb-3">
                                            Available Placeholders
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            {placeholderHelp.map((p) => (
                                                <div
                                                    key={p.placeholder}
                                                    className="flex items-center gap-2 bg-neutral-800 px-3 py-1.5 rounded-lg"
                                                >
                                                    <code className="text-blue-400 text-sm">
                                                        {p.placeholder}
                                                    </code>
                                                    <span className="text-neutral-500 text-xs">
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
