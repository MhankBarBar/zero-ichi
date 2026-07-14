"use client";

import {
    api,
    type HealthStatus,
    type IncomingWebhookKey,
    type WebhookDelivery,
    type WebhookItem,
} from "@/lib/api";
import { useWebSocket } from "@/hooks/use-websocket";
import { useEffect, useMemo, useState } from "react";

const INCOMING_ACTIONS = ["send_message", "emit_event"];

export default function WebhooksPage() {
    const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
    const [availableEvents, setAvailableEvents] = useState<string[]>([]);
    const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
    const [name, setName] = useState("Main Webhook");
    const [url, setUrl] = useState("");
    const [secret, setSecret] = useState("");
    const [maxFailures, setMaxFailures] = useState(10);

    const [incomingKeys, setIncomingKeys] = useState<IncomingWebhookKey[]>([]);
    const [incomingName, setIncomingName] = useState("Incoming Key");
    const [incomingRate, setIncomingRate] = useState(30);
    const [incomingActions, setIncomingActions] = useState<string[]>(["send_message"]);
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [editingWebhookId, setEditingWebhookId] = useState<number | null>(null);
    const [editingWebhookName, setEditingWebhookName] = useState("");
    const [editingWebhookUrl, setEditingWebhookUrl] = useState("");
    const [editingWebhookMaxFailures, setEditingWebhookMaxFailures] = useState(10);
    const [editingWebhookEnabled, setEditingWebhookEnabled] = useState(true);
    const [editingWebhookEvents, setEditingWebhookEvents] = useState<string[]>([]);
    const [editingIncomingKeyId, setEditingIncomingKeyId] = useState<number | null>(null);
    const [editingIncomingKeyName, setEditingIncomingKeyName] = useState("");
    const [editingIncomingKeyRate, setEditingIncomingKeyRate] = useState(30);
    const [editingIncomingKeyEnabled, setEditingIncomingKeyEnabled] = useState(true);
    const [editingIncomingActions, setEditingIncomingActions] = useState<string[]>([]);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [deliveries, setDeliveries] = useState<Record<number, WebhookDelivery[]>>({});
    const { lastEvent } = useWebSocket(20);

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
            const [hooksRes, incomingRes, healthRes] = await Promise.all([
                api.getWebhooks(),
                api.getIncomingWebhookKeys(),
                api.getHealth(),
            ]);
            setWebhooks(hooksRes.webhooks || []);
            setAvailableEvents(hooksRes.available_events || []);
            setIncomingKeys(incomingRes.keys || []);
            setHealth(healthRes);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load webhook data");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadWebhooks();
    }, []);

    useEffect(() => {
        if (!lastEvent) return;
        if (["config_update", "webhook_test"].includes(lastEvent.type)) {
            void loadWebhooks();
        }
    }, [lastEvent]);

    const toggleEvent = (eventName: string) => {
        setSelectedEvents((prev) =>
            prev.includes(eventName) ? prev.filter((e) => e !== eventName) : [...prev, eventName],
        );
    };

    const toggleIncomingAction = (action: string) => {
        setIncomingActions((prev) =>
            prev.includes(action) ? prev.filter((v) => v !== action) : [...prev, action],
        );
    };

    const toggleEditingWebhookEvent = (eventName: string) => {
        setEditingWebhookEvents((prev) =>
            prev.includes(eventName) ? prev.filter((e) => e !== eventName) : [...prev, eventName],
        );
    };

    const toggleEditingIncomingAction = (action: string) => {
        setEditingIncomingActions((prev) =>
            prev.includes(action) ? prev.filter((v) => v !== action) : [...prev, action],
        );
    };

    const createWebhook = async () => {
        setError("");
        setSuccess("");
        if (!url.trim()) {
            setError("Webhook URL is required");
            return;
        }

        try {
            const res = await api.createWebhook({
                name: name.trim() || "Webhook",
                url: url.trim(),
                events: selectedEvents.length ? selectedEvents : ["*"],
                secret: secret.trim() || undefined,
                enabled: true,
                max_failures: maxFailures,
            });
            setSuccess(`Webhook created. Secret: ${res.secret}`);
            setUrl("");
            setSecret("");
            setSelectedEvents([]);
            setMaxFailures(10);
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create webhook");
        }
    };

    const createIncomingKey = async () => {
        setError("");
        setSuccess("");
        try {
            const res = await api.createIncomingWebhookKey({
                name: incomingName.trim() || "Incoming Key",
                allowed_actions: incomingActions.length ? incomingActions : ["send_message"],
                rate_limit_per_minute: Math.max(1, incomingRate),
                enabled: true,
            });
            setSuccess(`Incoming webhook key created. Token: ${res.key.token}`);
            setIncomingName("Incoming Key");
            setIncomingRate(30);
            setIncomingActions(["send_message"]);
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create incoming key");
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

    const startEditWebhook = (hook: WebhookItem) => {
        setEditingWebhookId(hook.id);
        setEditingWebhookName(hook.name);
        setEditingWebhookUrl(hook.url);
        setEditingWebhookMaxFailures(hook.max_failures);
        setEditingWebhookEnabled(hook.enabled);
        setEditingWebhookEvents(hook.events || []);
    };

    const cancelEditWebhook = () => {
        setEditingWebhookId(null);
        setEditingWebhookName("");
        setEditingWebhookUrl("");
        setEditingWebhookMaxFailures(10);
        setEditingWebhookEnabled(true);
        setEditingWebhookEvents([]);
    };

    const saveWebhookEdit = async (hookId: number) => {
        try {
            await api.updateWebhook(hookId, {
                name: editingWebhookName.trim() || "Webhook",
                url: editingWebhookUrl.trim(),
                events: editingWebhookEvents.length ? editingWebhookEvents : ["*"],
                enabled: editingWebhookEnabled,
                max_failures: Math.max(1, editingWebhookMaxFailures),
            });
            cancelEditWebhook();
            await loadWebhooks();
            setSuccess("Webhook updated");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to save webhook");
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

    const rotateWebhookSecret = async (hook: WebhookItem) => {
        try {
            const res = await api.rotateWebhookSecret(hook.id);
            setSuccess(`New secret for ${hook.name}: ${res.secret}`);
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to rotate webhook secret");
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

    const replayDelivery = async (webhookId: number, deliveryId: number) => {
        try {
            const result = await api.replayWebhookDelivery(webhookId, deliveryId);
            setSuccess(result.success ? "Delivery replayed" : "Replay failed");
            await loadDeliveries(webhookId);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to replay delivery");
        }
    };

    const rotateIncomingKey = async (key: IncomingWebhookKey) => {
        try {
            const res = await api.rotateIncomingWebhookKey(key.id);
            setSuccess(`New incoming token: ${res.token}`);
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to rotate incoming key");
        }
    };

    const toggleIncomingKey = async (key: IncomingWebhookKey) => {
        try {
            await api.updateIncomingWebhookKey(key.id, { enabled: !key.enabled });
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to update incoming key");
        }
    };

    const startEditIncomingKey = (key: IncomingWebhookKey) => {
        setEditingIncomingKeyId(key.id);
        setEditingIncomingKeyName(key.name);
        setEditingIncomingKeyRate(key.rate_limit_per_minute);
        setEditingIncomingKeyEnabled(key.enabled);
        setEditingIncomingActions(key.allowed_actions || []);
    };

    const cancelEditIncomingKey = () => {
        setEditingIncomingKeyId(null);
        setEditingIncomingKeyName("");
        setEditingIncomingKeyRate(30);
        setEditingIncomingKeyEnabled(true);
        setEditingIncomingActions([]);
    };

    const saveIncomingKeyEdit = async (keyId: number) => {
        try {
            await api.updateIncomingWebhookKey(keyId, {
                name: editingIncomingKeyName.trim() || "Incoming Key",
                allowed_actions: editingIncomingActions.length
                    ? editingIncomingActions
                    : ["send_message"],
                rate_limit_per_minute: Math.max(1, editingIncomingKeyRate),
                enabled: editingIncomingKeyEnabled,
            });
            cancelEditIncomingKey();
            await loadWebhooks();
            setSuccess("Incoming webhook key updated");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to save incoming key");
        }
    };

    const deleteIncomingKey = async (key: IncomingWebhookKey) => {
        if (!confirm(`Delete incoming key \"${key.name}\"?`)) {
            return;
        }
        try {
            await api.deleteIncomingWebhookKey(key.id);
            await loadWebhooks();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete incoming key");
        }
    };

    return (
        <div className="space-y-6 text-white">
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h1 className="text-2xl font-semibold">Webhooks</h1>
                <p className="mt-2 text-sm text-neutral-400">
                    Manage outgoing event webhooks and incoming trigger keys.
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
                    <p className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                        Dispatcher
                    </p>
                    <p className="mt-2 text-2xl font-semibold text-white">
                        {loading || !health ? "—" : health.webhooks.running ? "Running" : "Stopped"}
                    </p>
                    <p className="mt-1 text-sm text-neutral-500">Webhook delivery worker state</p>
                </div>
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
                    <p className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                        Queue Size
                    </p>
                    <p className="mt-2 text-2xl font-semibold text-white">
                        {loading || !health ? "—" : health.webhooks.queue_size}
                    </p>
                    <p className="mt-1 text-sm text-neutral-500">Queued webhook events</p>
                </div>
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
                    <p className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                        Dropped Events
                    </p>
                    <p className="mt-2 text-2xl font-semibold text-white">
                        {loading || !health ? "—" : (health.webhooks.dropped_events ?? 0)}
                    </p>
                    <p className="mt-1 text-sm text-neutral-500">
                        Events dropped because queue was full
                    </p>
                </div>
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
                    <p className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                        Disabled Hooks
                    </p>
                    <p className="mt-2 text-2xl font-semibold text-white">
                        {loading || !health ? "—" : (health.webhooks.disabled_hook_count ?? 0)}
                    </p>
                    <p className="mt-1 text-sm text-neutral-500">
                        Endpoints currently auto-disabled or turned off
                    </p>
                </div>
            </div>

            {health?.webhooks.last_error ? (
                <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">
                    Last webhook worker error: {health.webhooks.last_error}
                </div>
            ) : null}

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h2 className="mb-4 text-lg font-medium">Create Outgoing Webhook</h2>
                <div className="grid gap-3 md:grid-cols-3">
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
                    <input
                        type="number"
                        min={1}
                        value={maxFailures}
                        onChange={(e) => setMaxFailures(Math.max(1, Number(e.target.value) || 1))}
                        placeholder="Max Failures"
                        className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <div className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-xs text-neutral-400 md:col-span-2">
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
                    Create Outgoing Webhook
                </button>
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h2 className="mb-4 text-lg font-medium">Incoming Webhook Keys</h2>

                <div className="grid gap-3 md:grid-cols-3">
                    <input
                        value={incomingName}
                        onChange={(e) => setIncomingName(e.target.value)}
                        placeholder="Key name"
                        className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <input
                        type="number"
                        min={1}
                        value={incomingRate}
                        onChange={(e) => setIncomingRate(Math.max(1, Number(e.target.value) || 1))}
                        placeholder="Rate/min"
                        className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                    />
                    <button
                        onClick={() => void createIncomingKey()}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
                    >
                        Create Incoming Key
                    </button>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                    {INCOMING_ACTIONS.map((actionName) => {
                        const active = incomingActions.includes(actionName);
                        return (
                            <button
                                key={actionName}
                                onClick={() => toggleIncomingAction(actionName)}
                                className={`rounded-md border px-2 py-1 text-xs ${
                                    active
                                        ? "border-sky-500 bg-sky-500/20 text-sky-300"
                                        : "border-neutral-700 bg-neutral-900 text-neutral-300"
                                }`}
                            >
                                {actionName}
                            </button>
                        );
                    })}
                </div>

                <div className="mt-4 space-y-2">
                    {incomingKeys.map((key) => (
                        <div
                            key={key.id}
                            className="rounded-lg border border-neutral-800 bg-neutral-950/60 p-3 text-xs"
                        >
                            {editingIncomingKeyId === key.id ? (
                                <div className="space-y-3">
                                    <div className="grid gap-3 md:grid-cols-3">
                                        <input
                                            value={editingIncomingKeyName}
                                            onChange={(e) =>
                                                setEditingIncomingKeyName(e.target.value)
                                            }
                                            className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                                        />
                                        <input
                                            type="number"
                                            min={1}
                                            value={editingIncomingKeyRate}
                                            onChange={(e) =>
                                                setEditingIncomingKeyRate(
                                                    Math.max(1, Number(e.target.value) || 1),
                                                )
                                            }
                                            className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                                        />
                                        <label className="flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm">
                                            <input
                                                type="checkbox"
                                                checked={editingIncomingKeyEnabled}
                                                onChange={(e) =>
                                                    setEditingIncomingKeyEnabled(e.target.checked)
                                                }
                                            />
                                            Enabled
                                        </label>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        {INCOMING_ACTIONS.map((actionName) => {
                                            const active =
                                                editingIncomingActions.includes(actionName);
                                            return (
                                                <button
                                                    key={actionName}
                                                    onClick={() =>
                                                        toggleEditingIncomingAction(actionName)
                                                    }
                                                    className={`rounded-md border px-2 py-1 text-xs ${
                                                        active
                                                            ? "border-sky-500 bg-sky-500/20 text-sky-300"
                                                            : "border-neutral-700 bg-neutral-900 text-neutral-300"
                                                    }`}
                                                >
                                                    {actionName}
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => void saveIncomingKeyEdit(key.id)}
                                            className="rounded-md bg-emerald-600 px-3 py-1 text-white"
                                        >
                                            Save
                                        </button>
                                        <button
                                            onClick={cancelEditIncomingKey}
                                            className="rounded-md border border-neutral-700 px-3 py-1"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <p className="text-sm font-medium text-white">{key.name}</p>
                                        <p className="text-neutral-400">
                                            actions: {key.allowed_actions.join(", ")} • rate/min:{" "}
                                            {key.rate_limit_per_minute}
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => startEditIncomingKey(key)}
                                            className="rounded-md border border-neutral-700 px-2 py-1"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            onClick={() => void toggleIncomingKey(key)}
                                            className="rounded-md border border-neutral-700 px-2 py-1"
                                        >
                                            {key.enabled ? "Disable" : "Enable"}
                                        </button>
                                        <button
                                            onClick={() => void rotateIncomingKey(key)}
                                            className="rounded-md border border-neutral-700 px-2 py-1"
                                        >
                                            Rotate
                                        </button>
                                        <button
                                            onClick={() => void deleteIncomingKey(key)}
                                            className="rounded-md border border-red-800 px-2 py-1 text-red-300"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                    {incomingKeys.length === 0 ? (
                        <p className="text-sm text-neutral-500">No incoming keys created yet.</p>
                    ) : null}
                </div>
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5">
                <h2 className="mb-4 text-lg font-medium">Configured Outgoing Endpoints</h2>
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
                            {editingWebhookId === hook.id ? (
                                <div className="space-y-3">
                                    <div className="grid gap-3 md:grid-cols-2">
                                        <input
                                            value={editingWebhookName}
                                            onChange={(e) => setEditingWebhookName(e.target.value)}
                                            className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                                        />
                                        <input
                                            value={editingWebhookUrl}
                                            onChange={(e) => setEditingWebhookUrl(e.target.value)}
                                            className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                                        />
                                        <input
                                            type="number"
                                            min={1}
                                            value={editingWebhookMaxFailures}
                                            onChange={(e) =>
                                                setEditingWebhookMaxFailures(
                                                    Math.max(1, Number(e.target.value) || 1),
                                                )
                                            }
                                            className="rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm"
                                        />
                                        <label className="flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm">
                                            <input
                                                type="checkbox"
                                                checked={editingWebhookEnabled}
                                                onChange={(e) =>
                                                    setEditingWebhookEnabled(e.target.checked)
                                                }
                                            />
                                            Enabled
                                        </label>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        {availableEvents.map((eventName) => {
                                            const active = editingWebhookEvents.includes(eventName);
                                            return (
                                                <button
                                                    key={eventName}
                                                    onClick={() =>
                                                        toggleEditingWebhookEvent(eventName)
                                                    }
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
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => void saveWebhookEdit(hook.id)}
                                            className="rounded-md bg-emerald-600 px-3 py-1 text-white"
                                        >
                                            Save
                                        </button>
                                        <button
                                            onClick={cancelEditWebhook}
                                            className="rounded-md border border-neutral-700 px-3 py-1"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div>
                                            <p className="font-medium">{hook.name}</p>
                                            <p className="text-xs text-neutral-400">{hook.url}</p>
                                            <p className="mt-1 text-xs text-neutral-500">
                                                Events: {hook.events.join(", ") || "*"}
                                            </p>
                                            <p className="mt-1 text-xs text-neutral-500">
                                                Failures: {hook.failure_count}/{hook.max_failures}
                                                {hook.disabled_reason
                                                    ? ` • ${hook.disabled_reason}`
                                                    : ""}
                                            </p>
                                            {hook.last_error ? (
                                                <p className="mt-1 text-xs text-red-400">
                                                    Last error: {hook.last_error}
                                                </p>
                                            ) : null}
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                onClick={() => startEditWebhook(hook)}
                                                className="rounded-md border border-neutral-700 px-3 py-1 text-xs"
                                            >
                                                Edit
                                            </button>
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
                                                onClick={() => void rotateWebhookSecret(hook)}
                                                className="rounded-md border border-neutral-700 px-3 py-1 text-xs"
                                            >
                                                Rotate Secret
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
                                                    className="flex items-center justify-between gap-2 text-xs"
                                                >
                                                    <span className="text-neutral-400">
                                                        #{d.id} {d.event_type} • attempt {d.attempt}
                                                    </span>
                                                    <div className="flex items-center gap-2">
                                                        <span
                                                            className={
                                                                d.success
                                                                    ? "text-emerald-400"
                                                                    : "text-red-400"
                                                            }
                                                        >
                                                            {d.success
                                                                ? `OK${d.status_code ? ` (${d.status_code})` : ""}`
                                                                : d.error || "Failed"}
                                                        </span>
                                                        <button
                                                            onClick={() =>
                                                                void replayDelivery(hook.id, d.id)
                                                            }
                                                            className="rounded border border-neutral-700 px-2 py-0.5 text-[11px]"
                                                        >
                                                            Replay
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : null}
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {error ? <p className="text-sm text-red-400">{error}</p> : null}
            {success ? <p className="text-sm text-emerald-400">{success}</p> : null}
        </div>
    );
}
