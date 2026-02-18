"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, type Filter, type Group } from "@/lib/api";
import {
    IconAlertCircle,
    IconArrowRight,
    IconDeviceFloppy,
    IconFilter,
    IconPlus,
    IconSearch,
    IconTrash,
    IconUsers,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

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
                className="mx-4 w-full max-w-lg rounded-2xl border border-neutral-700 bg-neutral-900 p-6 shadow-2xl"
            >
                <div className="mb-6 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Create Filter</h2>
                    <button onClick={onClose} className="text-neutral-400 hover:text-white">
                        <IconX className="h-5 w-5" />
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Trigger Word/Phrase
                        </label>
                        <Input
                            placeholder="e.g. hello, good morning"
                            value={trigger}
                            onChange={(e) => setTrigger(e.target.value)}
                            className="border-neutral-700 bg-neutral-800 text-white"
                        />
                        <p className="mt-1 text-xs text-neutral-500">
                            The bot will respond when this word/phrase is detected
                        </p>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Auto Response
                        </label>
                        <textarea
                            placeholder="Enter the auto-reply message..."
                            value={response}
                            onChange={(e) => setResponse(e.target.value)}
                            rows={4}
                            className="w-full resize-none rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-white placeholder-neutral-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                    </div>
                </div>

                <div className="mt-6 flex gap-3">
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
                        <IconDeviceFloppy className="mr-2 h-4 w-4" />
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
            setFilters((prev) => [...prev, { trigger, response }]);
            toast.success("Filter created", `Trigger "${trigger}" is now active`);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Failed to create filter", message);
        }
    };

    const handleDeleteFilter = async (trigger: string) => {
        if (!selectedGroup) return;

        try {
            await api.deleteFilter(selectedGroup.id, trigger);
            setFilters((prev) => prev.filter((f) => f.trigger !== trigger));
            toast.success("Filter deleted", `Trigger "${trigger}" has been removed`);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "An unknown error occurred";
            toast.error("Failed to delete filter", message);
        }
    };

    const filteredFilters = filters.filter(
        (filter) =>
            filter.trigger.toLowerCase().includes(search.toLowerCase()) ||
            filter.response.toLowerCase().includes(search.toLowerCase()),
    );

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Filters Manager</h1>
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
                    <h1 className="text-3xl font-bold text-white">Filters Manager</h1>
                    <p className="mt-1 text-neutral-400">Manage auto-reply filters</p>
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
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Filters Manager</h1>
                    <p className="mt-1 text-neutral-400">
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
                        <IconPlus className="mr-2 h-4 w-4" />
                        Add Filter
                    </Button>
                )}
            </div>

            {!selectedGroup ? (
                /* Group Selection */
                <div className="space-y-4">
                    <p className="text-sm text-neutral-500">
                        Select a group to manage its filters:
                    </p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                className="cursor-pointer border-neutral-700 bg-neutral-800/50 transition-colors hover:border-blue-500/50"
                                onClick={() => loadFilters(group)}
                            >
                                <CardContent className="flex items-center gap-4 p-4">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20">
                                        <IconUsers className="h-5 w-5 text-blue-400" />
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
                        <div className="relative max-w-md flex-1">
                            <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                            <Input
                                placeholder="Search filters..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="border-neutral-700 bg-neutral-800 pl-10 text-white"
                            />
                        </div>
                    </div>

                    {filtersLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map((i) => (
                                <Card
                                    key={i}
                                    className="animate-pulse border-neutral-700 bg-neutral-800/50"
                                >
                                    <CardContent className="p-4">
                                        <div className="mb-2 h-5 w-1/3 rounded bg-neutral-700"></div>
                                        <div className="h-4 w-2/3 rounded bg-neutral-700"></div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : filteredFilters.length === 0 ? (
                        <Card className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="p-12 text-center">
                                <IconFilter className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                                <h3 className="mb-2 text-lg font-medium text-neutral-400">
                                    {search ? "No filters found" : "No filters yet"}
                                </h3>
                                <p className="mb-4 text-sm text-neutral-500">
                                    {search
                                        ? "Try a different search term"
                                        : "Create auto-reply filters for this group"}
                                </p>
                                {!search && (
                                    <Button
                                        onClick={() => setModalOpen(true)}
                                        className="bg-blue-600 hover:bg-blue-500"
                                    >
                                        <IconPlus className="mr-2 h-4 w-4" />
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
                                        <Card className="group border-neutral-700 bg-neutral-800/50 transition-colors hover:border-neutral-600">
                                            <CardContent className="p-4">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="min-w-0 flex-1">
                                                        <div className="mb-2 flex items-center gap-3">
                                                            <span className="rounded bg-blue-500/20 px-2 py-1 text-sm font-medium text-blue-400">
                                                                {filter.trigger}
                                                            </span>
                                                            <IconArrowRight className="h-4 w-4 text-neutral-600" />
                                                        </div>
                                                        <p className="line-clamp-2 text-sm text-neutral-400">
                                                            {filter.response}
                                                        </p>
                                                    </div>
                                                    <button
                                                        onClick={() =>
                                                            handleDeleteFilter(filter.trigger)
                                                        }
                                                        className="rounded-lg p-2 text-neutral-400 opacity-0 transition-all group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400"
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
