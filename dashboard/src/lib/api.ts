/**
 * API client for the Ichi Zero Dashboard
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export interface TopCommand {
    command: string;
    count: number;
}

export interface TimelineEntry {
    date: string;
    count: number;
}

export interface AnalyticsCommands {
    top_commands: TopCommand[];
    total: number;
    days: number;
    group_id?: string;
}

export interface AnalyticsTimeline {
    timeline: TimelineEntry[];
    command: string;
    days: number;
    group_id?: string;
}

export interface BotStatus {
    status: "online" | "offline";
    bot_name: string;
    prefix: string;
    uptime: string;
}

export interface Config {
    bot: {
        name: string;
        prefix: string;
        login_method: string;
        owner_jid: string;
        auto_read: boolean;
        auto_react: boolean;
    };
    features: {
        anti_delete: boolean;
        anti_link: boolean;
        welcome: boolean;
        notes: boolean;
        filters: boolean;
        blacklist: boolean;
        warnings: boolean;
    };
    logging: {
        log_messages: boolean;
        verbose: boolean;
        level: string;
    };
    anti_delete: {
        forward_to: string;
        cache_ttl: number;
    };
    warnings: {
        limit: number;
        action: string;
    };
}

export interface AIConfig {
    enabled: boolean;
    provider: string;
    model: string;
    trigger_mode: string;
    owner_only: boolean;
    has_api_key: boolean;
    
}

export interface Command {
    name: string;
    description: string;
    category: string;
    enabled: boolean;
}

export interface Group {
    id: string;
    name: string;
    memberCount: number;
    isAdmin: boolean;
    settings: {
        antilink: boolean;
        welcome: boolean;
        mute: boolean;
    };
    
}

export interface LogEntry {
    id: string;
    timestamp: string;
    level: "info" | "warning" | "error" | "debug";
    message: string;
}

export interface Stats {
    messagesTotal: number;
    commandsUsed: number;
    activeGroups: number;
    scheduledTasks: number;
    uptime: string;
}

export interface ScheduledTask {
    id: string;
    type: "reminder" | "auto_message" | "recurring";
    chat_jid: string;
    message: string;
    trigger_time?: string;
    cron_expression?: string;
    interval_minutes?: number;
    enabled: boolean;
    created_at?: string;
}

export interface Note {
    name: string;
    content: string;
    media_type: "text" | "image" | "video" | "audio" | "document" | "sticker";
    media_path: string | null;
}

export interface Filter {
    trigger: string;
    response: string;
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };

    if (options?.headers) {
        const customHeaders = options.headers as Record<string, string>;
        Object.assign(headers, customHeaders);
    }

    if (typeof window !== "undefined") {
        const auth = localStorage.getItem("dashboard_auth");
        if (auth) {
            headers["Authorization"] = `Basic ${auth}`;
        }
    }

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            signal: controller.signal,
            headers,
        });
        if (res.status === 401) {
            if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
                window.location.href = "/login";
            }
            throw new Error("Unauthorized");
        }
        if (!res.ok) {
            throw new Error(`API Error: ${res.status} ${res.statusText}`);
        }

        return await res.json();
    } finally {
        clearTimeout(timeoutId);
    }
}

export interface RateLimitConfig {
    enabled: boolean;
    user_cooldown: number;
    command_cooldown: number;
    burst_limit: number;
    burst_window: number;
}

export interface WelcomeConfig {
    enabled: boolean;
    message: string;
}

export const api = {
    getStatus: () => fetchAPI<BotStatus>("/api/status"),

    getConfig: () => fetchAPI<Config>("/api/config"),
    updateConfig: (section: string, key: string, value: unknown) =>
        fetchAPI("/api/config", {
            method: "PUT",
            body: JSON.stringify({ section, key, value }),
        }),
    getCommands: () => fetchAPI<{ commands: Command[] }>("/api/commands"),
    toggleCommand: (name: string, enabled: boolean) =>
        fetchAPI(`/api/commands/${name}`, {
            method: "PATCH",
            body: JSON.stringify({ name, enabled }),
        }),

    getGroups: () => fetchAPI<{ groups: Group[] }>("/api/groups"),
    getGroup: (id: string) => fetchAPI<Group>(`/api/groups/${id}`),
    updateGroup: (id: string, settings: Group["settings"]) =>
        fetchAPI(`/api/groups/${id}`, {
            method: "PUT",
            body: JSON.stringify(settings),
        }),
    bulkUpdateGroups: (
        groupIds: string[],
        action: "antilink" | "welcome" | "mute",
        value: boolean,
    ) =>
        fetchAPI("/api/groups/bulk", {
            method: "POST",
            body: JSON.stringify({ group_ids: groupIds, action, value }),
        }),

    getStats: () => fetchAPI<Stats>("/api/stats"),

    sendMessage: (to: string, text: string) =>
        fetchAPI("/api/send-message", {
            method: "POST",
            body: JSON.stringify({ to, text }),
        }),

    sendMedia: (to: string, type: string, file: File, caption: string = "") => {
        const formData = new FormData();
        formData.append("to", to);
        formData.append("type", type);
        formData.append("caption", caption);
        formData.append("file", file);

        const auth = typeof window !== "undefined" ? localStorage.getItem("dashboard_auth") : null;
        const headers: Record<string, string> = {};
        if (auth) {
            headers["Authorization"] = `Basic ${auth}`;
        }

        return fetch(`${API_BASE}/api/send-media`, {
            method: "POST",
            body: formData,
            headers,
        }).then((res) => {
            if (res.status === 401) {
                if (typeof window !== "undefined") window.location.href = "/login";
                throw new Error("Unauthorized");
            }
            if (!res.ok) throw new Error(`API Error: ${res.status}`);
            return res.json();
        });
    },

    getAuthStatus: () =>
        fetchAPI<{
            is_logged_in: boolean;
            is_pairing: boolean;
            pair_code: string | null;
            has_qr: boolean;
            login_method: string;
        }>("/api/auth/status"),
    
    getQR: () => fetchAPI<{ qr: string | null }>("/api/auth/qr"),
    
    startPairing: (phone: string) =>
        fetchAPI("/api/auth/pair", {
            method: "POST",
            body: JSON.stringify({ phone }),
        }),

    getLogs: (limit = 100, level?: string, source: string = "bot") =>
        fetchAPI<{ logs: LogEntry[]; source: string }>(
            `/api/logs?limit=${limit}&source=${source}${level ? `&level=${level}` : ""}`,
        ),
    
    getRateLimit: () => fetchAPI<RateLimitConfig>("/api/ratelimit"),
    updateRateLimit: (config: RateLimitConfig) =>
        fetchAPI("/api/ratelimit", {
            method: "PUT",
            body: JSON.stringify(config),
        }),

    getWelcome: (groupId: string) => fetchAPI<WelcomeConfig>(`/api/groups/${groupId}/welcome`),
    updateWelcome: (groupId: string, config: WelcomeConfig) =>
        fetchAPI(`/api/groups/${groupId}/welcome`, {
            method: "PUT",
            body: JSON.stringify(config),
        }),
    getGoodbye: (groupId: string) => fetchAPI<WelcomeConfig>(`/api/groups/${groupId}/goodbye`),
    updateGoodbye: (groupId: string, config: WelcomeConfig) =>
        fetchAPI(`/api/groups/${groupId}/goodbye`, {
            method: "PUT",
            body: JSON.stringify(config),
        }),

    getTasks: () => fetchAPI<{ tasks: ScheduledTask[]; count: number }>("/api/tasks"),
    deleteTask: (taskId: string) => fetchAPI(`/api/tasks/${taskId}`, { method: "DELETE" }),
    toggleTask: (taskId: string, enabled: boolean) =>
        fetchAPI(`/api/tasks/${taskId}/toggle?enabled=${enabled}`, {
            method: "PUT",
        }),
    createTask: (task: {
        type: "reminder" | "auto_message" | "recurring";
        chat_jid: string;
        message: string;
        trigger_time?: string;
        interval_minutes?: number;
        cron_expression?: string;
    }) =>
        fetchAPI<{ success: boolean; task: ScheduledTask }>("/api/tasks", {
            method: "POST",
            body: JSON.stringify(task),
        }),

    getNotes: (groupId: string) =>
        fetchAPI<{ notes: Note[]; count: number }>(
            `/api/groups/${encodeURIComponent(groupId)}/notes`,
        ),
    createNote: (groupId: string, name: string, content: string, mediaType?: string) =>
        fetchAPI(`/api/groups/${encodeURIComponent(groupId)}/notes`, {
            method: "POST",
            body: JSON.stringify({ name, content, media_type: mediaType || "text" }),
        }),
    updateNote: (groupId: string, noteName: string, content: string, mediaType?: string) =>
        fetchAPI(
            `/api/groups/${encodeURIComponent(groupId)}/notes/${encodeURIComponent(noteName)}`,
            {
                method: "PUT",
                body: JSON.stringify({ content, media_type: mediaType || "text" }),
            },
        ),
    deleteNote: (groupId: string, noteName: string) =>
        fetchAPI(
            `/api/groups/${encodeURIComponent(groupId)}/notes/${encodeURIComponent(noteName)}`,
            {
                method: "DELETE",
            },
        ),
    uploadNoteMedia: async (groupId: string, noteName: string, file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        const headers: Record<string, string> = {};
        const username =
            typeof window !== "undefined" ? localStorage.getItem("dashboard_username") || "" : "";
        const password =
            typeof window !== "undefined" ? localStorage.getItem("dashboard_password") || "" : "";
        if (username && password) {
            headers["Authorization"] = `Basic ${btoa(`${username}:${password}`)}`;
        }
        const res = await fetch(
            `${API_BASE}/api/groups/${encodeURIComponent(groupId)}/notes/${encodeURIComponent(noteName)}/media`,
            { method: "POST", body: formData, headers },
        );
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<{ success: boolean; media_type: string; media_path: string }>;
    },
    getNoteMediaUrl: (groupId: string, noteName: string) =>
        `${API_BASE}/api/groups/${encodeURIComponent(groupId)}/notes/${encodeURIComponent(noteName)}/media`,

    getFilters: (groupId: string) =>
        fetchAPI<{ filters: Filter[]; count: number }>(
            `/api/groups/${encodeURIComponent(groupId)}/filters`,
        ),
    createFilter: (groupId: string, trigger: string, response: string) =>
        fetchAPI(`/api/groups/${encodeURIComponent(groupId)}/filters`, {
            method: "POST",
            body: JSON.stringify({ trigger, response }),
        }),
    deleteFilter: (groupId: string, trigger: string) =>
        fetchAPI(
            `/api/groups/${encodeURIComponent(groupId)}/filters/${encodeURIComponent(trigger)}`,
            {
                method: "DELETE",
            },
        ),

    getBlacklist: (groupId: string) =>
        fetchAPI<{ words: string[]; count: number }>(
            `/api/groups/${encodeURIComponent(groupId)}/blacklist`,
        ),
    addBlacklistWord: (groupId: string, word: string) =>
        fetchAPI(`/api/groups/${encodeURIComponent(groupId)}/blacklist`, {
            method: "POST",
            body: JSON.stringify({ word }),
        }),
    removeBlacklistWord: (groupId: string, word: string) =>
        fetchAPI(
            `/api/groups/${encodeURIComponent(groupId)}/blacklist/${encodeURIComponent(word)}`,
            {
                method: "DELETE",
            },
        ),

    getTopCommands: (days = 7, groupId?: string) => {
        const query = new URLSearchParams({ days: days.toString() });
        if (groupId) query.set("group_id", groupId);
        return fetchAPI<AnalyticsCommands>(`/api/analytics/commands?${query}`);
    },

    getTimeline: (command = "", days = 7, groupId?: string) => {
        const query = new URLSearchParams({ days: days.toString() });
        if (command) query.set("command", command);
        if (groupId) query.set("group_id", groupId);
        return fetchAPI<AnalyticsTimeline>(`/api/analytics/timeline?${query}`);
    },

    leaveGroup: (groupId: string) =>
        fetchAPI(`/api/groups/${encodeURIComponent(groupId)}/leave`, {
            method: "POST",
        }),

    getAIConfig: () => fetchAPI<AIConfig>("/api/ai-config"),
    updateAIConfig: (config: Omit<AIConfig, "has_api_key">) =>
        fetchAPI("/api/ai-config", {
            method: "PUT",
            body: JSON.stringify(config),
        }),
};
