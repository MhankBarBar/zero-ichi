"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, type Group, type ReportItem } from "@/lib/api";
import {
    IconAlertCircle,
    IconCheck,
    IconFileText,
    IconFlag,
    IconMusic,
    IconPhoto,
    IconRefresh,
    IconSearch,
    IconUsers,
    IconVideo,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

type StatusFilter = "all" | "open" | "resolved" | "dismissed";

const STATUS_BADGE: Record<StatusFilter, string> = {
    all: "bg-neutral-700 text-neutral-200",
    open: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
    resolved: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
    dismissed: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
};

function userPart(jid?: string) {
    return (jid || "").split("@")[0] || "-";
}

function MediaBadge({ mediaType }: { mediaType?: string }) {
    const mt = (mediaType || "").toLowerCase();
    if (!mt) return null;

    const map = {
        image: { icon: IconPhoto, cls: "text-sky-300 border-sky-500/30 bg-sky-500/15" },
        video: { icon: IconVideo, cls: "text-violet-300 border-violet-500/30 bg-violet-500/15" },
        audio: { icon: IconMusic, cls: "text-amber-300 border-amber-500/30 bg-amber-500/15" },
        document: {
            icon: IconFileText,
            cls: "text-emerald-300 border-emerald-500/30 bg-emerald-500/15",
        },
        sticker: { icon: IconPhoto, cls: "text-pink-300 border-pink-500/30 bg-pink-500/15" },
    } as const;

    const entry = map[mt as keyof typeof map] ?? map.document;
    const Icon = entry.icon;

    return (
        <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs ${entry.cls}`}>
            <Icon className="h-3.5 w-3.5" />
            {mt}
        </span>
    );
}

function CollapsibleText({ text, limit = 220 }: { text: string; limit?: number }) {
    const [expanded, setExpanded] = useState(false);
    const normalized = (text || "").trim();
    const tooLong = normalized.length > limit || normalized.includes("\n");
    const preview = tooLong && !expanded ? `${normalized.slice(0, limit).trimEnd()}...` : normalized;

    return (
        <div className="space-y-1">
            <p className="whitespace-pre-wrap break-words text-sm text-neutral-300">{preview}</p>
            {tooLong && (
                <button
                    type="button"
                    className="text-xs text-amber-300 hover:text-amber-200"
                    onClick={() => setExpanded((v) => !v)}
                >
                    {expanded ? "Show less" : "Show more"}
                </button>
            )}
        </div>
    );
}

export default function ReportsPage() {
    const toast = useToast();
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [reports, setReports] = useState<ReportItem[]>([]);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
    const [loading, setLoading] = useState(true);
    const [reportsLoading, setReportsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [refreshing, setRefreshing] = useState(false);

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

    const loadReports = async (group: Group, nextStatus: StatusFilter = statusFilter) => {
        try {
            setSelectedGroup(group);
            setReportsLoading(true);
            const data = await api.getReports(group.id, nextStatus === "all" ? "" : nextStatus);
            setReports(data.reports);
        } catch (err) {
            toast.error("Failed to load reports");
            console.error(err);
        } finally {
            setReportsLoading(false);
        }
    };

    useEffect(() => {
        if (!selectedGroup) return;
        async function refreshFilteredReports() {
            try {
                setReportsLoading(true);
                const data = await api.getReports(
                    selectedGroup.id,
                    statusFilter === "all" ? "" : statusFilter,
                );
                setReports(data.reports);
            } catch (err) {
                toast.error("Failed to load reports");
                console.error(err);
            } finally {
                setReportsLoading(false);
            }
        }

        refreshFilteredReports();
    }, [selectedGroup, statusFilter, toast]);

    const filteredReports = useMemo(() => {
        const q = search.toLowerCase().trim();
        if (!q) return reports;
        return reports.filter((r) => {
            return (
                r.id.toLowerCase().includes(q) ||
                r.reason.toLowerCase().includes(q) ||
                r.target_jid.toLowerCase().includes(q) ||
                r.reporter_name.toLowerCase().includes(q)
            );
        });
    }, [reports, search]);

    const handleRefresh = async () => {
        if (!selectedGroup) return;
        try {
            setRefreshing(true);
            await loadReports(selectedGroup, statusFilter);
        } finally {
            setRefreshing(false);
        }
    };

    const updateStatus = async (report: ReportItem, status: "resolved" | "dismissed") => {
        if (!selectedGroup) return;
        try {
            await api.updateReportStatus(selectedGroup.id, report.id, status);
            setReports((prev) => prev.map((r) => (r.id === report.id ? { ...r, status } : r)));
            toast.success("Report updated", `${report.id} marked as ${status}`);
        } catch (err) {
            toast.error("Failed to update report status");
            console.error(err);
        }
    };

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Reports</h1>
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

    if (error) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Reports</h1>
                    <p className="mt-1 text-neutral-400">Review member reports by group</p>
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
                <h1 className="text-3xl font-bold text-white">Reports</h1>
                <p className="mt-1 text-neutral-400">
                    {selectedGroup
                        ? `Reviewing reports for ${selectedGroup.name}`
                        : "Select a group to review moderation reports"}
                </p>
            </div>

            {!selectedGroup ? (
                <div className="space-y-4">
                    <p className="text-sm text-neutral-500">Choose a group:</p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                onClick={() => loadReports(group)}
                                className="cursor-pointer border-neutral-700 bg-neutral-800/50 transition-colors hover:border-amber-500/40"
                            >
                                <CardContent className="flex items-center gap-4 p-4">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20">
                                        <IconUsers className="h-5 w-5 text-amber-300" />
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
                </div>
            ) : (
                <div className="space-y-6">
                    <div className="flex flex-wrap items-center gap-3">
                        <Button
                            variant="outline"
                            onClick={() => {
                                setSelectedGroup(null);
                                setReports([]);
                                setSearch("");
                            }}
                            className="border-neutral-700 text-neutral-400"
                        >
                            ← Back to Groups
                        </Button>

                        {(["all", "open", "resolved", "dismissed"] as StatusFilter[]).map((status) => (
                            <Button
                                key={status}
                                variant={statusFilter === status ? "default" : "outline"}
                                onClick={() => setStatusFilter(status)}
                                className={
                                    statusFilter === status
                                        ? "bg-white text-black hover:bg-neutral-200"
                                        : "border-neutral-700 text-neutral-400"
                                }
                            >
                                {status.charAt(0).toUpperCase() + status.slice(1)}
                            </Button>
                        ))}

                        <Button
                            variant="outline"
                            onClick={handleRefresh}
                            disabled={refreshing || reportsLoading}
                            className="border-neutral-700 text-neutral-400"
                        >
                            <IconRefresh
                                className={`mr-2 h-4 w-4 ${refreshing || reportsLoading ? "animate-spin" : ""}`}
                            />
                            Refresh
                        </Button>

                        <div className="relative min-w-[220px] max-w-md flex-1">
                            <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                            <Input
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search by ID, reason, target, reporter"
                                className="border-neutral-700 bg-neutral-800 pl-9 text-white"
                            />
                        </div>
                    </div>

                    {reportsLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map((i) => (
                                <Card
                                    key={i}
                                    className="animate-pulse border-neutral-700 bg-neutral-800/40"
                                >
                                    <CardContent className="space-y-3 p-4">
                                        <div className="h-4 w-24 rounded bg-neutral-700" />
                                        <div className="h-4 w-full rounded bg-neutral-700" />
                                        <div className="h-4 w-2/3 rounded bg-neutral-700" />
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : filteredReports.length === 0 ? (
                        <Card className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="p-12 text-center">
                                <IconFlag className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                                <h3 className="mb-2 text-lg font-medium text-neutral-300">No reports found</h3>
                                <p className="text-sm text-neutral-500">
                                    {search
                                        ? "Try a different search term"
                                        : "No reports match the current filter"}
                                </p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            <AnimatePresence>
                                {filteredReports.map((report) => {
                                    const status = (report.status as StatusFilter) || "open";
                                    const targetPn = report.target_pn || "";
                                    const targetLid = report.target_lid || "";
                                    const reporterPn = report.reporter_pn || "";
                                    const reporterLid = report.reporter_lid || "";

                                    const targetNumber =
                                        report.target_number || userPart(targetPn) || userPart(report.target_jid);
                                    const reporterNumber =
                                        report.reporter_number ||
                                        userPart(reporterPn) ||
                                        userPart(report.reporter_jid);

                                    const createdAt = new Date(report.created_at).toLocaleString();
                                    return (
                                        <motion.div
                                            key={report.id}
                                            initial={{ opacity: 0, y: 8 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -8 }}
                                        >
                                            <Card className="border-neutral-700 bg-neutral-800/40">
                                                <CardContent className="space-y-3 p-4">
                                                    <div className="flex items-center justify-between gap-3">
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-mono text-sm text-white">
                                                                {report.id}
                                                            </span>
                                                            <span
                                                                className={`rounded px-2 py-0.5 text-xs ${STATUS_BADGE[status]}`}
                                                            >
                                                                {status}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-neutral-500">{createdAt}</p>
                                                    </div>

                                                    <CollapsibleText
                                                        text={report.reason || "No reason provided"}
                                                    />

                                                    {report.evidence_text ? (
                                                        <div className="rounded-lg border border-neutral-700 bg-neutral-900/70 p-3 text-xs text-neutral-400">
                                                            <p className="mb-2 text-[11px] uppercase tracking-wide text-neutral-500">
                                                                Evidence
                                                            </p>
                                                            <CollapsibleText
                                                                text={report.evidence_text}
                                                                limit={320}
                                                            />
                                                        </div>
                                                    ) : null}

                                                    <div className="text-xs text-neutral-500">
                                                        target: @{targetNumber}
                                                        {report.target_name
                                                            ? ` (${report.target_name})`
                                                            : ""}
                                                        {" • "}
                                                        reporter: @{reporterNumber}
                                                        {report.reporter_name
                                                            ? ` (${report.reporter_name})`
                                                            : ""}
                                                    </div>

                                                    {report.evidence_media_type ? (
                                                        <div className="flex items-center gap-2">
                                                            <MediaBadge mediaType={report.evidence_media_type} />
                                                            {report.evidence_caption ? (
                                                                <span className="text-xs text-neutral-500">
                                                                    {report.evidence_caption}
                                                                </span>
                                                            ) : null}
                                                        </div>
                                                    ) : null}

                                                    <div className="flex flex-wrap gap-2 text-[11px] text-neutral-500">
                                                        <span className="rounded border border-neutral-700 bg-neutral-900/70 px-2 py-0.5">
                                                            target PN: {targetPn || "-"}
                                                        </span>
                                                        <span className="rounded border border-neutral-700 bg-neutral-900/70 px-2 py-0.5">
                                                            target LID: {targetLid || "-"}
                                                        </span>
                                                        <span className="rounded border border-neutral-700 bg-neutral-900/70 px-2 py-0.5">
                                                            reporter PN: {reporterPn || "-"}
                                                        </span>
                                                        <span className="rounded border border-neutral-700 bg-neutral-900/70 px-2 py-0.5">
                                                            reporter LID: {reporterLid || "-"}
                                                        </span>
                                                    </div>

                                                    {status === "open" && (
                                                        <div className="flex flex-wrap gap-2">
                                                            <Button
                                                                size="sm"
                                                                className="bg-emerald-600 hover:bg-emerald-500"
                                                                onClick={() =>
                                                                    updateStatus(report, "resolved")
                                                                }
                                                            >
                                                                <IconCheck className="mr-1 h-4 w-4" /> Resolve
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                className="border-red-500/50 text-red-300"
                                                                onClick={() =>
                                                                    updateStatus(report, "dismissed")
                                                                }
                                                            >
                                                                <IconX className="mr-1 h-4 w-4" /> Dismiss
                                                            </Button>
                                                        </div>
                                                    )}
                                                </CardContent>
                                            </Card>
                                        </motion.div>
                                    );
                                })}
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
