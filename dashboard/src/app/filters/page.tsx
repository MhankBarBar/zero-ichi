"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    IconFilter,
    IconPlus,
    IconTrash,
    IconSearch,
    IconUsers,
    IconAlertCircle,
    IconX,
    IconDeviceFloppy,
    IconArrowRight
} from "@tabler/icons-react";
import { api, type Group, type Filter } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { motion, AnimatePresence } from "framer-motion";

interface FilterModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (trigger: string, response: string) => void;
}

function FilterModal({ isOpen, onClose, onSave }: FilterModalProps) {
    const [trigger, setTrigger] = useState("");
    const [response, setResponse] = useState("");

    const handleSave = () => {
        if (!trigger.trim() || !response.trim()) return;
        onSave(trigger.trim().toLowerCase(), response);
        setTrigger("");
        setResponse("");
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-neutral-900 border border-neutral-700 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl"
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">Create Filter</h2>
                    <button onClick={onClose} className="text-neutral-400 hover:text-white">
                        <IconX className="h-5 w-5" />
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-neutral-400 mb-2">
                            Trigger Word/Phrase
                        </label>
                        <Input
                            placeholder="e.g. hello, good morning"
                            value={trigger}
                            onChange={(e) => setTrigger(e.target.value)}
                            className="bg-neutral-800 border-neutral-700 text-white"
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                            The bot will respond when this word/phrase is detected
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-neutral-400 mb-2">
                            Auto Response
                        </label>
                        <textarea
                            placeholder="Enter the auto-reply message..."
                            value={response}
                            onChange={(e) => setResponse(e.target.value)}
                            rows={4}
                            className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                        />
                    </div>
                </div>

                <div className="flex gap-3 mt-6">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        className="flex-1 border-neutral-700 text-neutral-400"
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={!trigger.trim() || !response.trim()}
                        className="flex-1 bg-blue-600 hover:bg-blue-500"
                    >
                        <IconDeviceFloppy className="h-4 w-4 mr-2" />
                        Create Filter
                    </Button>
                </div>
            </motion.div>
        </div>
    );
}

export default function FiltersPage() {
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [filters, setFilters] = useState<Filter[]>([]);
    const [loading, setLoading] = useState(true);
    const [filtersLoading, setFiltersLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
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

    const loadFilters = async (group: Group) => {
        setSelectedGroup(group);
        setFiltersLoading(true);
        try {
            const data = await api.getFilters(group.id);
            setFilters(data.filters);
        } catch (err) {
            toast.error("Failed to load filters");
            console.error(err);
        } finally {
            setFiltersLoading(false);
        }
    };

    const handleCreateFilter = async (trigger: string, response: string) => {
        if (!selectedGroup) return;

        try {
            await api.createFilter(selectedGroup.id, trigger, response);
            setFilters(prev => [...prev, { trigger, response }]);
            toast.success("Filter created", `Trigger "${trigger}" is now active`);
        } catch (err: any) {
            toast.error("Failed to create filter", err.message);
        }
    };

    const handleDeleteFilter = async (trigger: string) => {
        if (!selectedGroup) return;

        try {
            await api.deleteFilter(selectedGroup.id, trigger);
            setFilters(prev => prev.filter(f => f.trigger !== trigger));
            toast.success("Filter deleted", `Trigger "${trigger}" has been removed`);
        } catch (err: any) {
            toast.error("Failed to delete filter", err.message);
        }
    };

    const filteredFilters = filters.filter(filter =>
        filter.trigger.toLowerCase().includes(search.toLowerCase()) ||
        filter.response.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Filters Manager</h1>
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
                    <h1 className="text-3xl font-bold text-white">Filters Manager</h1>
                    <p className="text-neutral-400 mt-1">Manage auto-reply filters</p>
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
                    <h1 className="text-3xl font-bold text-white">Filters Manager</h1>
                    <p className="text-neutral-400 mt-1">
                        {selectedGroup
                            ? `Managing filters for ${selectedGroup.name}`
                            : "Select a group to manage auto-reply filters"}
                    </p>
                </div>
                {selectedGroup && (
                    <Button
                        onClick={() => setModalOpen(true)}
                        className="bg-blue-600 hover:bg-blue-500"
                    >
                        <IconPlus className="h-4 w-4 mr-2" />
                        Add Filter
                    </Button>
                )}
            </div>

            {!selectedGroup ? (
                /* Group Selection */
                <div className="space-y-4">
                    <p className="text-neutral-500 text-sm">Select a group to manage its filters:</p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                className="bg-neutral-800/50 border-neutral-700 cursor-pointer hover:border-blue-500/50 transition-colors"
                                onClick={() => loadFilters(group)}
                            >
                                <CardContent className="p-4 flex items-center gap-4">
                                    <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                                        <IconUsers className="h-5 w-5 text-blue-400" />
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
                /* Filters List */
                <div className="space-y-4">
                    <div className="flex items-center gap-4">
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
                                placeholder="Search filters..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-10 bg-neutral-800 border-neutral-700 text-white"
                            />
                        </div>
                    </div>

                    {filtersLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map((i) => (
                                <Card key={i} className="bg-neutral-800/50 border-neutral-700 animate-pulse">
                                    <CardContent className="p-4">
                                        <div className="h-5 bg-neutral-700 rounded w-1/3 mb-2"></div>
                                        <div className="h-4 bg-neutral-700 rounded w-2/3"></div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : filteredFilters.length === 0 ? (
                        <Card className="bg-neutral-800/50 border-neutral-700">
                            <CardContent className="p-12 text-center">
                                <IconFilter className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-neutral-400 mb-2">
                                    {search ? "No filters found" : "No filters yet"}
                                </h3>
                                <p className="text-neutral-500 text-sm mb-4">
                                    {search
                                        ? "Try a different search term"
                                        : "Create auto-reply filters for this group"}
                                </p>
                                {!search && (
                                    <Button
                                        onClick={() => setModalOpen(true)}
                                        className="bg-blue-600 hover:bg-blue-500"
                                    >
                                        <IconPlus className="h-4 w-4 mr-2" />
                                        Create Filter
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            <AnimatePresence>
                                {filteredFilters.map((filter) => (
                                    <motion.div
                                        key={filter.trigger}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -20 }}
                                    >
                                        <Card className="bg-neutral-800/50 border-neutral-700 hover:border-neutral-600 transition-colors group">
                                            <CardContent className="p-4">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-3 mb-2">
                                                            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-sm font-medium rounded">
                                                                {filter.trigger}
                                                            </span>
                                                            <IconArrowRight className="h-4 w-4 text-neutral-600" />
                                                        </div>
                                                        <p className="text-neutral-400 text-sm line-clamp-2">
                                                            {filter.response}
                                                        </p>
                                                    </div>
                                                    <button
                                                        onClick={() => handleDeleteFilter(filter.trigger)}
                                                        className="p-2 rounded-lg hover:bg-red-500/20 text-neutral-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                                                    >
                                                        <IconTrash className="h-4 w-4" />
                                                    </button>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}
                </div>
            )}

            <FilterModal
                isOpen={modalOpen}
                onClose={() => setModalOpen(false)}
                onSave={handleCreateFilter}
            />
        </div>
    );
}
