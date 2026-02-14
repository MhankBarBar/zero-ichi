"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { WS_BASE } from "@/lib/api";

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

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        try {
            const ws = new WebSocket(`${WS_BASE}/ws`);
            wsRef.current = ws;

            ws.onopen = () => setConnected(true);

            ws.onmessage = (e) => {
                try {
                    const event: WsEvent = JSON.parse(e.data);
                    setEvents((prev) => [event, ...prev].slice(0, maxEvents));
                } catch {
                }
            };

            ws.onclose = () => {
                setConnected(false);
                reconnectTimer.current = setTimeout(connect, 3000);
            };

            ws.onerror = () => {
                ws.close();
            };
        } catch {
            reconnectTimer.current = setTimeout(connect, 3000);
        }
    }, [maxEvents]);

    useEffect(() => {
        connect();
        return () => {
            clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [connect]);

    const clearEvents = useCallback(() => setEvents([]), []);

    return { events, connected, clearEvents };
}
