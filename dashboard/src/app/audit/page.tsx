"use client";

import { useWebSocket } from "@/hooks/use-websocket";
import { api, type AuditLogItem } from "@/lib/api";
import { useCallback, useEffect, useState } from "react";

export default function AuditPage() {
    const [logs, setLogs] = useState<AuditLogItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [actionFilter, setActionFilter] = useState("");
    const { lastEvent } = useWebSocket(40);

    const fetchLogs = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const res = await api.getAuditLogs(200, actionFilter.trim());
            setLogs(res.logs || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load audit logs");
        } finally {
            setLoading(false);
        }
    }, [actionFilter]);

    useEffect(() => {
        void fetchLogs();
    }, [fetchLogs]);

    useEffect(() => {
        if (!lastEvent) return;
        if (["config_update", "command_update", "group_update", "webhook_test"].includes(lastEvent.type)) {
            void fetchLogs();
        }
    }, [lastEvent, fetchLogs]);

    return (
        <div className="space-y-6 text-white">
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h1 className="text-2xl font-semibold">Audit Logs</h1>
                <p className="mt-2 text-sm text-neutral-400">
                    Timeline of sensitive dashboard and webhook actions.
                </p>
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <div className="flex flex-wrap items-center gap-2">
                    <input
                        value={actionFilter}
                        onChange={(e) => setActionFilter(e.target.value)}
                        placeholder="Filter by action (e.g. webhook.update)"
                        className="min-w-[260px] flex-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <button
                        onClick={() => void fetchLogs()}
                        className="rounded-lg bg-neutral-800 px-4 py-2 text-sm hover:bg-neutral-700"
                    >
                        Refresh
                    </button>
                </div>

                {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}
                {loading ? <p className="mt-3 text-sm text-neutral-400">Loading...</p> : null}

                {!loading && logs.length === 0 ? (
                    <p className="mt-3 text-sm text-neutral-500">No audit logs found.</p>
                ) : null}

                <div className="mt-4 space-y-2">
                    {logs.map((log) => (
                        <div
                            key={log.id}
                            className="rounded-lg border border-neutral-800 bg-neutral-950/60 p-3 text-sm"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-medium text-emerald-300">{log.action}</span>
                                <span className="text-xs text-neutral-500">{log.created_at}</span>
                            </div>
                            <p className="mt-1 text-xs text-neutral-400">
                                actor: {log.actor} • resource: {log.resource}
                            </p>
                            {Object.keys(log.details || {}).length > 0 ? (
                                <pre className="mt-2 overflow-x-auto rounded border border-neutral-800 bg-black/30 p-2 text-xs text-neutral-300">
                                    {JSON.stringify(log.details, null, 2)}
                                </pre>
                            ) : null}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
