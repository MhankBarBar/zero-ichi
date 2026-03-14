"use client";

import { api, type WebhookDelivery, type WebhookItem } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";

export default function WebhooksPage() {
    const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
    const [availableEvents, setAvailableEvents] = useState<string[]>([]);
    const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
    const [name, setName] = useState("Main Webhook");
    const [url, setUrl] = useState("");
    const [secret, setSecret] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [deliveries, setDeliveries] = useState<Record<number, WebhookDelivery[]>>({});

    const selectedLabel = useMemo(() => {
        if (selectedEvents.length === 0) {
            return "No events selected";
        }
        return selectedEvents.join(", ");
    }, [selectedEvents]);

    const loadWebhooks = async () => {
        setLoading(true);
        setError("");
        try {
            const res = await api.getWebhooks();
            setWebhooks(res.webhooks || []);
            setAvailableEvents(res.available_events || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load webhooks");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadWebhooks();
    }, []);

    const toggleEvent = (eventName: string) => {
        setSelectedEvents((prev) =>
            prev.includes(eventName) ? prev.filter((e) => e !== eventName) : [...prev, eventName],
        );
    };

    const createWebhook = async () => {
        setError("");
        setSuccess("");
        if (!url.trim()) {
            setError("URL is required");
            return;
        }

        try {
            const res = await api.createWebhook({
                name: name.trim() || "Webhook",
                url: url.trim(),
                events: selectedEvents.length ? selectedEvents : ["*"],
                secret: secret.trim() || undefined,
                enabled: true,
            });
            setSuccess(`Webhook created. Secret: ${res.secret}`);
            setUrl("");
            setSecret("");
            setSelectedEvents([]);
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create webhook");
        }
    };

    const toggleWebhook = async (hook: WebhookItem) => {
        try {
            await api.updateWebhook(hook.id, { enabled: !hook.enabled });
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to update webhook");
        }
    };

    const removeWebhook = async (hook: WebhookItem) => {
        if (!confirm(`Delete webhook \"${hook.name}\"?`)) {
            return;
        }
        try {
            await api.deleteWebhook(hook.id);
            await loadWebhooks();
            setDeliveries((prev) => {
                const next = { ...prev };
                delete next[hook.id];
                return next;
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete webhook");
        }
    };

    const testWebhook = async (hook: WebhookItem) => {
        try {
            await api.testWebhook(hook.id);
            await loadDeliveries(hook.id);
            setSuccess(`Test sent to ${hook.name}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to test webhook");
        }
    };

    const loadDeliveries = async (webhookId: number) => {
        try {
            const res = await api.getWebhookDeliveries(webhookId, 20);
            setDeliveries((prev) => ({ ...prev, [webhookId]: res.deliveries || [] }));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load deliveries");
        }
    };

    return (
        <div className="space-y-6 text-white">
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h1 className="text-2xl font-semibold">Webhooks</h1>
                <p className="mt-2 text-sm text-neutral-400">
                    Send bot events to external services (CI, Discord, Slack, custom apps).
                </p>
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h2 className="mb-4 text-lg font-medium">Create Webhook</h2>
                <div className="grid gap-3 md:grid-cols-2">
                    <input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Name"
                        className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <input
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://example.com/webhook"
                        className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <input
                        value={secret}
                        onChange={(e) => setSecret(e.target.value)}
                        placeholder="Secret (optional)"
                        className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <div className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-xs text-neutral-400">
                        {selectedLabel}
                    </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                    {availableEvents.map((eventName) => {
                        const active = selectedEvents.includes(eventName);
                        return (
                            <button
                                key={eventName}
                                onClick={() => toggleEvent(eventName)}
                                className={`rounded-md border px-2 py-1 text-xs ${
                                    active
                                        ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                                        : "border-neutral-700 bg-neutral-900 text-neutral-300"
                                }`}
                            >
                                {eventName}
                            </button>
                        );
                    })}
                </div>

                <button
                    onClick={() => void createWebhook()}
                    className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
                >
                    Create
                </button>

                {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}
                {success ? <p className="mt-3 text-sm text-emerald-400">{success}</p> : null}
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h2 className="mb-4 text-lg font-medium">Configured Endpoints</h2>
                {loading ? <p className="text-sm text-neutral-400">Loading...</p> : null}
                {!loading && webhooks.length === 0 ? (
                    <p className="text-sm text-neutral-500">No webhooks yet.</p>
                ) : null}

                <div className="space-y-4">
                    {webhooks.map((hook) => (
                        <div
                            key={hook.id}
                            className="rounded-lg border border-neutral-800 bg-neutral-950/60 p-4"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div>
                                    <p className="font-medium">{hook.name}</p>
                                    <p className="text-xs text-neutral-400">{hook.url}</p>
                                    <p className="mt-1 text-xs text-neutral-500">
                                        Events: {hook.events.join(", ") || "*"}
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => void toggleWebhook(hook)}
                                        className="rounded-md border border-neutral-700 px-3 py-1 text-xs"
                                    >
                                        {hook.enabled ? "Disable" : "Enable"}
                                    </button>
                                    <button
                                        onClick={() => void testWebhook(hook)}
                                        className="rounded-md border border-neutral-700 px-3 py-1 text-xs"
                                    >
                                        Test
                                    </button>
                                    <button
                                        onClick={() => void loadDeliveries(hook.id)}
                                        className="rounded-md border border-neutral-700 px-3 py-1 text-xs"
                                    >
                                        Deliveries
                                    </button>
                                    <button
                                        onClick={() => void removeWebhook(hook)}
                                        className="rounded-md border border-red-800 px-3 py-1 text-xs text-red-300"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>

                            {deliveries[hook.id] ? (
                                <div className="mt-3 space-y-1 border-t border-neutral-800 pt-3">
                                    {deliveries[hook.id].slice(0, 8).map((d) => (
                                        <div
                                            key={d.id}
                                            className="flex items-center justify-between text-xs"
                                        >
                                            <span className="text-neutral-400">
                                                {d.event_type} • attempt {d.attempt}
                                            </span>
                                            <span
                                                className={
                                                    d.success ? "text-emerald-400" : "text-red-400"
                                                }
                                            >
                                                {d.success
                                                    ? `OK${d.status_code ? ` (${d.status_code})` : ""}`
                                                    : d.error || "Failed"}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : null}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
