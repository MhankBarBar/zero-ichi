"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, type Group } from "@/lib/api";
import {
    IconAlertCircle,
    IconBan,
    IconPlus,
    IconSearch,
    IconShieldOff,
    IconUsers,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

export default function BlacklistPage() {
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [words, setWords] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [wordsLoading, setWordsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [newWord, setNewWord] = useState("");
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

    const loadBlacklist = async (group: Group) => {
        setSelectedGroup(group);
        setWordsLoading(true);
        try {
            const data = await api.getBlacklist(group.id);
            setWords(data.words);
        } catch (err) {
            toast.error("Failed to load blacklist");
            console.error(err);
        } finally {
            setWordsLoading(false);
        }
    };

    const handleAddWord = async () => {
        if (!selectedGroup || !newWord.trim()) return;

        const word = newWord.trim().toLowerCase();
        try {
            await api.addBlacklistWord(selectedGroup.id, word);
            setWords((prev) => [...prev, word]);
            setNewWord("");
            toast.success("Word added", `"${word}" is now blacklisted`);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Failed to add word", message);
        }
    };

    const handleRemoveWord = async (word: string) => {
        if (!selectedGroup) return;

        try {
            await api.removeBlacklistWord(selectedGroup.id, word);
            setWords((prev) => prev.filter((w) => w !== word));
            toast.success("Word removed", `"${word}" is no longer blacklisted`);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Failed to remove word", message);
        }
    };

    const filteredWords = words.filter((word) => word.toLowerCase().includes(search.toLowerCase()));

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Blacklist Manager</h1>
                    <p className="mt-1 text-neutral-400">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card
                            key={i}
                            className="animate-pulse border-neutral-700 bg-neutral-800/50"
                        >
                            <CardContent className="p-6">
                                <div className="mb-2 h-6 w-3/4 rounded bg-neutral-700"></div>
                                <div className="h-4 w-1/2 rounded bg-neutral-700"></div>
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
                    <h1 className="text-3xl font-bold text-white">Blacklist Manager</h1>
                    <p className="mt-1 text-neutral-400">Manage blocked words per group</p>
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
            <div>
                <h1 className="text-3xl font-bold text-white">Blacklist Manager</h1>
                <p className="mt-1 text-neutral-400">
                    {selectedGroup
                        ? `Managing blacklist for ${selectedGroup.name}`
                        : "Select a group to manage blacklisted words"}
                </p>
            </div>

            {!selectedGroup ? (
                /* Group Selection */
                <div className="space-y-4">
                    <p className="text-sm text-neutral-500">
                        Select a group to manage its blacklist:
                    </p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                className="cursor-pointer border-neutral-700 bg-neutral-800/50 transition-colors hover:border-red-500/50"
                                onClick={() => loadBlacklist(group)}
                            >
                                <CardContent className="flex items-center gap-4 p-4">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-red-500/20 to-orange-500/20">
                                        <IconUsers className="h-5 w-5 text-red-400" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <h3 className="truncate font-medium text-white">
                                            {group.name}
                                        </h3>
                                        <p className="text-sm text-neutral-500">
                                            {group.memberCount} members
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            ) : (
                /* Blacklist Management */
                <div className="space-y-6">
                    <div className="flex flex-wrap items-center gap-4">
                        <Button
                            variant="outline"
                            onClick={() => setSelectedGroup(null)}
                            className="border-neutral-700 text-neutral-400"
                        >
                            ← Back to Groups
                        </Button>
                        <div className="relative max-w-md flex-1">
                            <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                            <Input
                                placeholder="Search words..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="border-neutral-700 bg-neutral-800 pl-10 text-white"
                            />
                        </div>
                    </div>

                    <Card className="border-neutral-700 bg-neutral-800/50">
                        <CardContent className="p-4">
                            <div className="flex gap-3">
                                <Input
                                    placeholder="Enter word or phrase to blacklist..."
                                    value={newWord}
                                    onChange={(e) => setNewWord(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleAddWord()}
                                    className="border-neutral-700 bg-neutral-900 text-white"
                                />
                                <Button
                                    onClick={handleAddWord}
                                    disabled={!newWord.trim()}
                                    className="shrink-0 bg-red-600 hover:bg-red-500"
                                >
                                    <IconPlus className="mr-2 h-4 w-4" />
                                    Add
                                </Button>
                            </div>
                            <p className="mt-2 text-xs text-neutral-500">
                                Messages containing blacklisted words will trigger a warning
                            </p>
                        </CardContent>
                    </Card>

                    {wordsLoading ? (
                        <div className="flex flex-wrap gap-2">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div
                                    key={i}
                                    className="h-8 w-20 animate-pulse rounded-full bg-neutral-700"
                                ></div>
                            ))}
                        </div>
                    ) : filteredWords.length === 0 ? (
                        <Card className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="p-12 text-center">
                                <IconShieldOff className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                                <h3 className="mb-2 text-lg font-medium text-neutral-400">
                                    {search ? "No words found" : "No blacklisted words"}
                                </h3>
                                <p className="text-sm text-neutral-500">
                                    {search
                                        ? "Try a different search term"
                                        : "Add words to prevent their usage in this group"}
                                </p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            <AnimatePresence>
                                {filteredWords.map((word) => (
                                    <motion.div
                                        key={word}
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.8 }}
                                        className="group flex items-center gap-1 rounded-full border border-red-500/30 bg-red-500/20 px-3 py-1.5"
                                    >
                                        <IconBan className="h-3 w-3 text-red-400" />
                                        <span className="text-sm text-red-300">{word}</span>
                                        <button
                                            onClick={() => handleRemoveWord(word)}
                                            className="ml-1 rounded-full p-0.5 text-red-400 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-500/30"
                                        >
                                            <IconX className="h-3 w-3" />
                                        </button>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}

                    {!wordsLoading && words.length > 0 && (
                        <p className="text-sm text-neutral-500">
                            {words.length} word{words.length !== 1 ? "s" : ""} blacklisted
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
