"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    IconBan,
    IconPlus,
    IconTrash,
    IconSearch,
    IconUsers,
    IconAlertCircle,
    IconX,
    IconShieldOff
} from "@tabler/icons-react";
import { api, type Group } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { motion, AnimatePresence } from "framer-motion";

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
            setWords(prev => [...prev, word]);
            setNewWord("");
            toast.success("Word added", `"${word}" is now blacklisted`);
        } catch (err: any) {
            toast.error("Failed to add word", err.message);
        }
    };

    const handleRemoveWord = async (word: string) => {
        if (!selectedGroup) return;

        try {
            await api.removeBlacklistWord(selectedGroup.id, word);
            setWords(prev => prev.filter(w => w !== word));
            toast.success("Word removed", `"${word}" is no longer blacklisted`);
        } catch (err: any) {
            toast.error("Failed to remove word", err.message);
        }
    };

    const filteredWords = words.filter(word =>
        word.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Blacklist Manager</h1>
                    <p className="text-neutral-400 mt-1">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="bg-neutral-800/50 border-neutral-700 animate-pulse">
                            <CardContent className="p-6">
                                <div className="h-6 bg-neutral-700 rounded w-3/4 mb-2"></div>
                                <div className="h-4 bg-neutral-700 rounded w-1/2"></div>
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
                    <p className="text-neutral-400 mt-1">Manage blocked words per group</p>
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
            <div>
                <h1 className="text-3xl font-bold text-white">Blacklist Manager</h1>
                <p className="text-neutral-400 mt-1">
                    {selectedGroup
                        ? `Managing blacklist for ${selectedGroup.name}`
                        : "Select a group to manage blacklisted words"}
                </p>
            </div>

            {!selectedGroup ? (
                /* Group Selection */
                <div className="space-y-4">
                    <p className="text-neutral-500 text-sm">Select a group to manage its blacklist:</p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                className="bg-neutral-800/50 border-neutral-700 cursor-pointer hover:border-red-500/50 transition-colors"
                                onClick={() => loadBlacklist(group)}
                            >
                                <CardContent className="p-4 flex items-center gap-4">
                                    <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-red-500/20 to-orange-500/20 flex items-center justify-center">
                                        <IconUsers className="h-5 w-5 text-red-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-white font-medium truncate">{group.name}</h3>
                                        <p className="text-neutral-500 text-sm">{group.memberCount} members</p>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            ) : (
                /* Blacklist Management */
                <div className="space-y-6">
                    <div className="flex items-center gap-4 flex-wrap">
                        <Button
                            variant="outline"
                            onClick={() => setSelectedGroup(null)}
                            className="border-neutral-700 text-neutral-400"
                        >
                            ← Back to Groups
                        </Button>
                        <div className="relative flex-1 max-w-md">
                            <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                            <Input
                                placeholder="Search words..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-10 bg-neutral-800 border-neutral-700 text-white"
                            />
                        </div>
                    </div>

                    <Card className="bg-neutral-800/50 border-neutral-700">
                        <CardContent className="p-4">
                            <div className="flex gap-3">
                                <Input
                                    placeholder="Enter word or phrase to blacklist..."
                                    value={newWord}
                                    onChange={(e) => setNewWord(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleAddWord()}
                                    className="bg-neutral-900 border-neutral-700 text-white"
                                />
                                <Button
                                    onClick={handleAddWord}
                                    disabled={!newWord.trim()}
                                    className="bg-red-600 hover:bg-red-500 shrink-0"
                                >
                                    <IconPlus className="h-4 w-4 mr-2" />
                                    Add
                                </Button>
                            </div>
                            <p className="text-xs text-neutral-500 mt-2">
                                Messages containing blacklisted words will trigger a warning
                            </p>
                        </CardContent>
                    </Card>

                    {wordsLoading ? (
                        <div className="flex flex-wrap gap-2">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <div key={i} className="h-8 w-20 bg-neutral-700 rounded-full animate-pulse"></div>
                            ))}
                        </div>
                    ) : filteredWords.length === 0 ? (
                        <Card className="bg-neutral-800/50 border-neutral-700">
                            <CardContent className="p-12 text-center">
                                <IconShieldOff className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-neutral-400 mb-2">
                                    {search ? "No words found" : "No blacklisted words"}
                                </h3>
                                <p className="text-neutral-500 text-sm">
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
                                        className="group flex items-center gap-1 px-3 py-1.5 bg-red-500/20 border border-red-500/30 rounded-full"
                                    >
                                        <IconBan className="h-3 w-3 text-red-400" />
                                        <span className="text-red-300 text-sm">{word}</span>
                                        <button
                                            onClick={() => handleRemoveWord(word)}
                                            className="ml-1 p-0.5 rounded-full hover:bg-red-500/30 text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <IconX className="h-3 w-3" />
                                        </button>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}

                    {!wordsLoading && words.length > 0 && (
                        <p className="text-neutral-500 text-sm">
                            {words.length} word{words.length !== 1 ? "s" : ""} blacklisted
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
