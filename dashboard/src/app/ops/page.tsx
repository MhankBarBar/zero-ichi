"use client";

import { api, type HealthStatus } from "@/lib/api";
import { useWebSocket } from "@/hooks/use-websocket";
import {
    IconAlertCircle,
    IconDatabase,
    IconHeartbeat,
    IconPlugConnected,
    IconRefresh,
    IconWebhook,
} from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";

function HealthBadge({ ok, good, bad }: { ok: boolean; good: string; bad: string }) {
    return (
        <span
            className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                ok ? "bg-emerald-500/15 text-emerald-300" : "bg-red-500/15 text-red-300"
            }`}
        >
            {ok ? good : bad}
        </span>
    );
}

export default function OpsPage() {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const { events, connected } = useWebSocket(20);

    const fetchHealth = useCallback(async () => {
        setError("");
        try {
            const res = await api.getHealth();
            setHealth(res);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load ops health");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void fetchHealth();
    }, [fetchHealth]);

    useEffect(() => {
        if (!events.length) return;
        const latest = events[0];
        if (
            ["config_update", "command_update", "group_update", "webhook_test"].includes(
                latest.type,
            )
        ) {
            void fetchHealth();
        }
    }, [events, fetchHealth]);

    return (
        <div className="space-y-6 text-white">
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-semibold">Ops Health</h1>
                        <p className="mt-2 text-sm text-neutral-400">
                            Runtime health, webhook queue state, and backend operator metrics.
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <HealthBadge
                            ok={connected}
                            good="Live WS connected"
                            bad="Live WS disconnected"
                        />
                        <button
                            onClick={() => void fetchHealth()}
                            className="inline-flex items-center gap-2 rounded-lg bg-neutral-800 px-4 py-2 text-sm hover:bg-neutral-700"
                        >
                            <IconRefresh className="h-4 w-4" />
                            Refresh
                        </button>
                    </div>
                </div>
            </div>

            {error ? (
                <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
                    {error}
                </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                    <div className="mb-3 flex items-center gap-2 text-neutral-300">
                        <IconHeartbeat className="h-5 w-5 text-emerald-400" />
                        <h2 className="text-lg font-medium">Service</h2>
                    </div>
                    {loading || !health ? (
                        <p className="text-sm text-neutral-400">Loading...</p>
                    ) : (
                        <div className="space-y-3 text-sm">
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Overall</span>
                                <HealthBadge
                                    ok={health.status === "ok"}
                                    good="OK"
                                    bad={health.status}
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Live updates</span>
                                <HealthBadge ok={connected} good="Connected" bad="Disconnected" />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Recent events buffered</span>
                                <span>{events.length}</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                    <div className="mb-3 flex items-center gap-2 text-neutral-300">
                        <IconDatabase className="h-5 w-5 text-blue-400" />
                        <h2 className="text-lg font-medium">Database</h2>
                    </div>
                    {loading || !health ? (
                        <p className="text-sm text-neutral-400">Loading...</p>
                    ) : (
                        <div className="space-y-3 text-sm">
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Status</span>
                                <HealthBadge
                                    ok={health.database.ok}
                                    good="Healthy"
                                    bad="Degraded"
                                />
                            </div>
                            <div>
                                <p className="text-neutral-400">Endpoint</p>
                                <code className="mt-1 block overflow-x-auto rounded bg-black/30 px-2 py-1 text-xs text-neutral-300">
                                    {health.database.url}
                                </code>
                            </div>
                            {health.database.error ? (
                                <div>
                                    <p className="text-neutral-400">Error</p>
                                    <p className="mt-1 text-xs text-red-300">
                                        {health.database.error}
                                    </p>
                                </div>
                            ) : null}
                        </div>
                    )}
                </div>

                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                    <div className="mb-3 flex items-center gap-2 text-neutral-300">
                        <IconWebhook className="h-5 w-5 text-purple-400" />
                        <h2 className="text-lg font-medium">Webhooks</h2>
                    </div>
                    {loading || !health ? (
                        <p className="text-sm text-neutral-400">Loading...</p>
                    ) : (
                        <div className="space-y-3 text-sm">
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Dispatcher</span>
                                <HealthBadge
                                    ok={health.webhooks.running}
                                    good="Running"
                                    bad="Stopped"
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Queue size</span>
                                <span>{health.webhooks.queue_size}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Dropped events</span>
                                <span>{health.webhooks.dropped_events ?? 0}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-neutral-400">Disabled hooks</span>
                                <span>{health.webhooks.disabled_hook_count ?? 0}</span>
                            </div>
                            {health.webhooks.last_error ? (
                                <div>
                                    <p className="text-neutral-400">Last error</p>
                                    <p className="mt-1 text-xs text-red-300">
                                        {health.webhooks.last_error}
                                    </p>
                                </div>
                            ) : (
                                <div className="flex items-center gap-2 text-xs text-neutral-500">
                                    <IconPlugConnected className="h-4 w-4 text-emerald-400" />
                                    No recent webhook error
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <div className="mb-4 flex items-center gap-2">
                    <IconAlertCircle className="h-5 w-5 text-amber-400" />
                    <h2 className="text-lg font-medium">Recent Live Events</h2>
                </div>
                {!events.length ? (
                    <p className="text-sm text-neutral-500">No live events yet.</p>
                ) : (
                    <div className="space-y-2">
                        {events.slice(0, 10).map((event, index) => (
                            <div
                                key={`${event.timestamp}-${event.type}-${index}`}
                                className="rounded-lg border border-neutral-800 bg-black/20 p-3 text-sm"
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <span className="font-medium text-emerald-300">
                                        {event.type}
                                    </span>
                                    <span className="text-xs text-neutral-500">
                                        {event.timestamp}
                                    </span>
                                </div>
                                <pre className="mt-2 overflow-x-auto text-xs text-neutral-400">
                                    {JSON.stringify(event.data, null, 2)}
                                </pre>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
