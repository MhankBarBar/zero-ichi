"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { IconAlertCircle, IconClock } from "@tabler/icons-react";
import { api, type Config, type RateLimitConfig } from "@/lib/api";
import { NumberInput } from "@/components/ui/number-input";
import { useToast } from "@/components/ui/toast";

export default function ConfigPage() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [config, setConfig] = useState<Config | null>(null);
    const [rateLimit, setRateLimit] = useState<RateLimitConfig | null>(null);
    const toast = useToast();

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const [configData, rateLimitData] = await Promise.all([
                    api.getConfig(),
                    api.getRateLimit().catch(() => null),
                ]);
                setConfig(configData);
                setRateLimit(rateLimitData);
                setError(null);
            } catch (err) {
                setError("Failed to load config. Is the API server running?");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);



    const friendlyLabels: Record<string, Record<string, string>> = {
        bot: { name: "Bot Name", prefix: "Command Prefix", auto_read: "Auto Read" },
        features: { anti_delete: "Anti-Delete", anti_link: "Anti-Link", welcome: "Welcome Messages", notes: "Notes", warnings: "Warnings" },
        logging: { log_messages: "Message Logging", verbose: "Debug Mode" },
        warnings: { limit: "Warning Limit" },
    };

    const updateConfig = async (section: string, key: string, value: unknown) => {
        try {
            await api.updateConfig(section, key, value);
            setConfig((prev) => {
                if (!prev) return prev;
                const sectionData = prev[section as keyof Config];
                if (typeof sectionData === "object" && sectionData !== null) {
                    return {
                        ...prev,
                        [section]: {
                            ...sectionData,
                            [key]: value,
                        },
                    };
                }
                return prev;
            });

            const label = friendlyLabels[section]?.[key] || key;
            if (typeof value === "boolean") {
                if (value) {
                    toast.success(`${label} enabled`);
                } else {
                    toast.warning(`${label} disabled`);
                }
            } else {
                toast.success("Settings saved", `${label} updated`);
            }
        } catch (err) {
            toast.error("Failed to save", "Could not update configuration");
            console.error("Failed to update config:", err);
        }
    };

    const updateRateLimit = async (key: keyof RateLimitConfig, value: number | boolean) => {
        if (!rateLimit) return;
        const newConfig = { ...rateLimit, [key]: value };
        setRateLimit(newConfig);
        try {
            await api.updateRateLimit(newConfig);
            if (key === "enabled") {
                if (value) {
                    toast.success("Rate Limiting enabled");
                } else {
                    toast.warning("Rate Limiting disabled");
                }
            } else {
                toast.success("Rate limit updated");
            }
        } catch (err) {
            toast.error("Failed to save", "Could not update rate limit");
            console.error("Failed to update rate limit:", err);
        }
    };

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Configuration</h1>
                    <p className="text-neutral-400 mt-1">Loading...</p>
                </div>
                <div className="grid gap-6">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="bg-neutral-800/50 border-neutral-700">
                            <CardContent className="py-8">
                                <div className="h-4 w-32 bg-neutral-700 animate-pulse rounded mb-4" />
                                <div className="h-4 w-48 bg-neutral-700 animate-pulse rounded" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    if (error || !config) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Configuration</h1>
                    <p className="text-neutral-400 mt-1">Manage your bot settings</p>
                </div>
                <Card className="bg-red-900/30 border-red-700/50">
                    <CardContent className="flex items-center gap-4 py-4">
                        <IconAlertCircle className="h-6 w-6 text-red-400" />
                        <div>
                            <h3 className="font-semibold text-white">Error</h3>
                            <p className="text-sm text-red-400">{error}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const sections = [
        {
            title: "Bot",
            description: "Basic bot settings",
            settings: [
                { section: "bot", key: "name", label: "Bot Name", type: "text", value: config.bot.name, description: "Display name for the bot" },
                { section: "bot", key: "prefix", label: "Command Prefix", type: "text", value: config.bot.prefix, description: "Character(s) that trigger commands" },
                { section: "bot", key: "auto_read", label: "Auto Read", type: "toggle", value: config.bot.auto_read, description: "Mark messages as read automatically" },
            ],
        },
        {
            title: "Features",
            description: "Enable or disable bot features",
            settings: [
                { section: "features", key: "anti_delete", label: "Anti-Delete", type: "toggle", value: config.features.anti_delete, description: "Save deleted messages" },
                { section: "features", key: "anti_link", label: "Anti-Link", type: "toggle", value: config.features.anti_link, description: "Remove messages with links" },
                { section: "features", key: "welcome", label: "Welcome Messages", type: "toggle", value: config.features.welcome, description: "Greet new members" },
                { section: "features", key: "notes", label: "Notes", type: "toggle", value: config.features.notes, description: "Enable #notes system" },
                { section: "features", key: "warnings", label: "Warnings", type: "toggle", value: config.features.warnings, description: "Warning system" },
            ],
        },
        {
            title: "Logging",
            description: "Logging configuration",
            settings: [
                { section: "logging", key: "log_messages", label: "Log Messages", type: "toggle", value: config.logging.log_messages, description: "Log incoming messages" },
                { section: "logging", key: "verbose", label: "Verbose Mode", type: "toggle", value: config.logging.verbose, description: "Enable debug logging" },
            ],
        },
        {
            title: "Warnings",
            description: "Warning system settings",
            settings: [
                { section: "warnings", key: "limit", label: "Warning Limit", type: "number", value: config.warnings.limit, description: "Max warnings before action" },
            ],
        },
    ];

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold text-white">Configuration</h1>
                <p className="text-neutral-400 mt-1">Manage your bot settings</p>
            </div>

            {rateLimit && (
                <GlowCard className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 border-green-700/50">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <IconClock className="h-5 w-5 text-green-400" />
                            <CardTitle className="text-white">Rate Limiting</CardTitle>
                        </div>
                        <CardDescription>Prevent spam and abuse with cooldowns</CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between py-3 border-b border-neutral-700/50">
                            <div className="space-y-0.5">
                                <label className="text-sm font-medium text-white">Enable Rate Limiting</label>
                                <p className="text-xs text-neutral-500">Apply cooldowns between commands</p>
                            </div>
                            <Switch
                                checked={rateLimit.enabled}
                                onCheckedChange={(checked) => updateRateLimit("enabled", checked)}
                            />
                        </div>
                        <div className="grid gap-6 md:grid-cols-2">
                            <NumberInput
                                label="User Cooldown (seconds)"
                                value={rateLimit.user_cooldown}
                                onChange={(v) => updateRateLimit("user_cooldown", v)}
                                min={0}
                                max={60}
                                step={1}
                                disabled={!rateLimit.enabled}
                                description="Time between any commands from same user"
                            />
                            <NumberInput
                                label="Command Cooldown (seconds)"
                                value={rateLimit.command_cooldown}
                                onChange={(v) => updateRateLimit("command_cooldown", v)}
                                min={0}
                                max={60}
                                step={1}
                                disabled={!rateLimit.enabled}
                                description="Cooldown for same command per user"
                            />
                            <NumberInput
                                label="Burst Limit"
                                value={rateLimit.burst_limit}
                                onChange={(v) => updateRateLimit("burst_limit", v)}
                                min={1}
                                max={50}
                                step={1}
                                disabled={!rateLimit.enabled}
                                description="Max commands in burst window"
                            />
                            <NumberInput
                                label="Burst Window (seconds)"
                                value={rateLimit.burst_window}
                                onChange={(v) => updateRateLimit("burst_window", v)}
                                min={1}
                                max={120}
                                step={1}
                                disabled={!rateLimit.enabled}
                                description="Time window for burst limit"
                            />
                        </div>
                    </CardContent>
                </GlowCard>
            )}

            <div className="grid gap-6">
                {sections.map((section) => (
                    <GlowCard key={section.title} className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                        <CardHeader>
                            <CardTitle className="text-white">{section.title}</CardTitle>
                            <CardDescription>{section.description}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {section.settings.map((setting) => (
                                <div
                                    key={setting.key}
                                    className="flex items-center justify-between py-3 border-b border-neutral-700/50 last:border-0"
                                >
                                    <div className="space-y-0.5">
                                        <label className="text-sm font-medium text-white">
                                            {setting.label}
                                        </label>
                                        {setting.description && (
                                            <p className="text-xs text-neutral-500">{setting.description}</p>
                                        )}
                                    </div>
                                    <div>
                                        {setting.type === "toggle" ? (
                                            <Switch
                                                checked={setting.value as boolean}
                                                onCheckedChange={(checked) =>
                                                    updateConfig(setting.section, setting.key, checked)
                                                }
                                            />
                                        ) : setting.type === "number" ? (
                                            <NumberInput
                                                value={setting.value as number}
                                                onChange={(v) =>
                                                    updateConfig(setting.section, setting.key, v)
                                                }
                                                min={1}
                                                max={10}
                                            />
                                        ) : (
                                            <Input
                                                type="text"
                                                value={setting.value as string}
                                                onChange={(e) =>
                                                    updateConfig(setting.section, setting.key, e.target.value)
                                                }
                                                className="w-48 bg-neutral-700 border-neutral-600 text-white"
                                            />
                                        )}
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </GlowCard>
                ))}
            </div>
        </div>
    );
}
