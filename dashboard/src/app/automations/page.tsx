"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CustomSelect } from "@/components/ui/custom-select";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { api, type AutomationRule, type Group } from "@/lib/api";
import {
    IconAlertCircle,
    IconBolt,
    IconPlus,
    IconSearch,
    IconTrash,
    IconUsers,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

const triggerOptions = [
    { label: "Contains", value: "contains" },
    { label: "Regex", value: "regex" },
    { label: "Link", value: "link" },
];

const actionOptions = [
    { label: "Reply", value: "reply" },
    { label: "Warn", value: "warn" },
    { label: "Delete", value: "delete" },
    { label: "Kick", value: "kick" },
    { label: "Mute", value: "mute" },
];

export default function AutomationsPage() {
    const toast = useToast();
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [rules, setRules] = useState<AutomationRule[]>([]);
    const [loading, setLoading] = useState(true);
    const [rulesLoading, setRulesLoading] = useState(false);
    const [search, setSearch] = useState("");

    const [name, setName] = useState("");
    const [triggerType, setTriggerType] = useState<"contains" | "regex" | "link">("contains");
    const [triggerValue, setTriggerValue] = useState("");
    const [actionType, setActionType] = useState<"reply" | "warn" | "delete" | "kick" | "mute">(
        "reply",
    );
    const [actionValue, setActionValue] = useState("");

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

    const loadRules = async (group: Group) => {
        try {
            setSelectedGroup(group);
            setRulesLoading(true);
            const res = await api.getAutomations(group.id);
            setRules(res.rules);
        } catch {
            toast.error("Failed to load automation rules");
        } finally {
            setRulesLoading(false);
        }
    };

    const createRule = async () => {
        if (!selectedGroup) return;
        if (triggerType !== "link" && !triggerValue.trim()) {
            toast.warning("Trigger value is required");
            return;
        }

        try {
            const payload: Omit<AutomationRule, "id"> = {
                name: name.trim() || "",
                enabled: true,
                trigger_type: triggerType,
                trigger_value: triggerValue.trim(),
                action_type: actionType,
                action_value: actionValue.trim(),
            };
            const res = await api.createAutomation(selectedGroup.id, payload);
            setRules((prev) => [...prev, res.rule]);
            setName("");
            setTriggerValue("");
            setActionValue("");
            toast.success("Rule created", res.rule.id);
        } catch {
            toast.error("Failed to create rule");
        }
    };

    const toggleRule = async (rule: AutomationRule) => {
        if (!selectedGroup) return;
        try {
            const res = await api.updateAutomation(selectedGroup.id, rule.id, { enabled: !rule.enabled });
            setRules((prev) => prev.map((r) => (r.id === rule.id ? res.rule : r)));
            toast.success(`Rule ${res.rule.enabled ? "enabled" : "disabled"}`, res.rule.id);
        } catch {
            toast.error("Failed to update rule");
        }
    };

    const deleteRule = async (rule: AutomationRule) => {
        if (!selectedGroup) return;
        try {
            await api.deleteAutomation(selectedGroup.id, rule.id);
            setRules((prev) => prev.filter((r) => r.id !== rule.id));
            toast.success("Rule deleted", rule.id);
        } catch {
            toast.error("Failed to delete rule");
        }
    };

    const filteredRules = useMemo(() => {
        const q = search.toLowerCase().trim();
        if (!q) return rules;
        return rules.filter((rule) => {
            return (
                rule.id.toLowerCase().includes(q) ||
                rule.name.toLowerCase().includes(q) ||
                rule.trigger_value.toLowerCase().includes(q) ||
                rule.action_type.toLowerCase().includes(q)
            );
        });
    }, [rules, search]);

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Automations</h1>
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
                <h1 className="text-3xl font-bold text-white">Automations</h1>
                <p className="mt-1 text-neutral-400">
                    {selectedGroup
                        ? `Managing automation rules for ${selectedGroup.name}`
                        : "Build no-code trigger and action rules per group"}
                </p>
            </div>

            {!selectedGroup ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {groups.map((group) => (
                        <Card
                            key={group.id}
                            className="cursor-pointer border-neutral-700 bg-neutral-800/50 transition-colors hover:border-violet-500/40"
                            onClick={() => loadRules(group)}
                        >
                            <CardContent className="flex items-center gap-4 p-4">
                                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-cyan-500/20">
                                    <IconUsers className="h-5 w-5 text-violet-300" />
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
                        <div className="relative min-w-[220px] max-w-md flex-1">
                            <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                            <Input
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search by id, name, trigger"
                                className="border-neutral-700 bg-neutral-800 pl-9 text-white"
                            />
                        </div>
                    </div>

                    <Card className="border-neutral-700 bg-neutral-800/50">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-white">
                                <IconBolt className="h-5 w-5 text-violet-400" />
                                Create Rule
                            </CardTitle>
                            <CardDescription>
                                Configure trigger and action. Link trigger ignores trigger value.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-4 md:grid-cols-2">
                                <Input
                                    placeholder="Rule name (optional)"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="border-neutral-700 bg-neutral-900 text-white"
                                />
                                <CustomSelect
                                    options={triggerOptions}
                                    value={triggerType}
                                    onChange={(value) =>
                                        setTriggerType(value as "contains" | "regex" | "link")
                                    }
                                    className="w-full"
                                />

                                <Input
                                    placeholder={
                                        triggerType === "link"
                                            ? "Not required for link trigger"
                                            : "Trigger value"
                                    }
                                    value={triggerValue}
                                    onChange={(e) => setTriggerValue(e.target.value)}
                                    className="border-neutral-700 bg-neutral-900 text-white"
                                    disabled={triggerType === "link"}
                                />

                                <CustomSelect
                                    options={actionOptions}
                                    value={actionType}
                                    onChange={(value) =>
                                        setActionType(
                                            value as "reply" | "warn" | "delete" | "kick" | "mute",
                                        )
                                    }
                                    className="w-full"
                                />
                            </div>

                            <Input
                                placeholder="Action value (reply text, optional for non-reply)"
                                value={actionValue}
                                onChange={(e) => setActionValue(e.target.value)}
                                className="border-neutral-700 bg-neutral-900 text-white"
                            />

                            <Button onClick={createRule} className="bg-violet-600 hover:bg-violet-500">
                                <IconPlus className="mr-2 h-4 w-4" /> Add Rule
                            </Button>
                        </CardContent>
                    </Card>

                    {rulesLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map((i) => (
                                <Card
                                    key={i}
                                    className="animate-pulse border-neutral-700 bg-neutral-800/40"
                                >
                                    <CardContent className="space-y-3 p-4">
                                        <div className="h-4 w-24 rounded bg-neutral-700" />
                                        <div className="h-4 w-full rounded bg-neutral-700" />
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : filteredRules.length === 0 ? (
                        <Card className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="p-12 text-center">
                                <IconAlertCircle className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                                <h3 className="mb-2 text-lg font-medium text-neutral-300">
                                    No automation rules
                                </h3>
                                <p className="text-sm text-neutral-500">
                                    Create your first rule using the form above.
                                </p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            <AnimatePresence>
                                {filteredRules.map((rule) => (
                                    <motion.div
                                        key={rule.id}
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -8 }}
                                    >
                                        <Card className="border-neutral-700 bg-neutral-800/40">
                                            <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
                                                <div className="min-w-0 flex-1 text-sm text-neutral-300">
                                                    <div className="mb-1 flex items-center gap-2">
                                                        <span className="font-mono text-white">{rule.id}</span>
                                                        <span className="rounded bg-neutral-700 px-2 py-0.5 text-xs text-neutral-200">
                                                            {rule.name || "Unnamed rule"}
                                                        </span>
                                                    </div>
                                                    <p className="truncate text-neutral-300">
                                                        if <span className="text-violet-300">{rule.trigger_type}</span>
                                                        {" = "}
                                                        <span className="text-neutral-100">
                                                            {rule.trigger_value || "(link trigger)"}
                                                        </span>
                                                        {" => "}
                                                        <span className="text-cyan-300">{rule.action_type}</span>
                                                    </p>
                                                    {rule.action_value ? (
                                                        <p className="mt-1 truncate text-xs text-neutral-500">
                                                            action value: {rule.action_value}
                                                        </p>
                                                    ) : null}
                                                </div>

                                                <div className="flex items-center gap-2">
                                                    <div className="flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-900/60 px-2 py-1">
                                                        <span className="text-xs text-neutral-400">Enabled</span>
                                                        <Switch
                                                            checked={rule.enabled}
                                                            onCheckedChange={() => toggleRule(rule)}
                                                        />
                                                    </div>

                                                    <Button
                                                        size="icon"
                                                        variant="outline"
                                                        className="border-red-500/40 text-red-300 hover:bg-red-500/10"
                                                        onClick={() => deleteRule(rule)}
                                                    >
                                                        <IconTrash className="h-4 w-4" />
                                                    </Button>
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
