"use client";

import { api, WS_BASE } from "@/lib/api";
import { useCallback, useEffect, useRef, useState } from "react";

export interface WsEvent {
    type: string;
    data: Record<string, unknown>;
    timestamp: string;
}

/**
 * Hook for connecting to the dashboard WebSocket.
 * Provides real-time events and connection status.
 */
export function useWebSocket(maxEvents = 50) {
    const [events, setEvents] = useState<WsEvent[]>([]);
    const [connected, setConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

    const [reconnectTrigger, setReconnectTrigger] = useState(0);

    useEffect(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        let cancelled = false;

        const connect = async () => {
            try {
                const { token } = await api.getWsToken();
                if (cancelled) {
                    return;
                }

                const ws = new WebSocket(`${WS_BASE}/ws?token=${encodeURIComponent(token)}`);
                wsRef.current = ws;

                ws.onopen = () => setConnected(true);

                ws.onmessage = (e) => {
                    try {
                        const event: WsEvent = JSON.parse(e.data);
                        setEvents((prev) => [event, ...prev].slice(0, maxEvents));
                    } catch {
                        // Ignore parse errors
                    }
                };

                ws.onclose = () => {
                    setConnected(false);
                    reconnectTimer.current = setTimeout(() => {
                        setReconnectTrigger((prev) => prev + 1);
                    }, 3000);
                };

                ws.onerror = () => {
                    ws.close();
                };
            } catch {
                setConnected(false);
                reconnectTimer.current = setTimeout(() => {
                    setReconnectTrigger((prev) => prev + 1);
                }, 3000);
            }
        };

        void connect();

        return () => {
            cancelled = true;
            clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [maxEvents, reconnectTrigger]);

    const clearEvents = useCallback(() => setEvents([]), []);
    const lastEvent = events[0] || null;

    return { events, connected, clearEvents, lastEvent };
}
