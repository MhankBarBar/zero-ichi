"use client";

import * as React from "react";
import { createContext, useContext, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    IconCheck,
    IconAlertCircle,
    IconInfoCircle,
    IconAlertTriangle,
    IconX,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
    id: string;
    type: ToastType;
    title: string;
    message?: string;
    duration?: number;
}

interface ToastContextValue {
    toasts: Toast[];
    addToast: (toast: Omit<Toast, "id">) => void;
    removeToast: (id: string) => void;
    success: (title: string, message?: string) => void;
    error: (title: string, message?: string) => void;
    info: (title: string, message?: string) => void;
    warning: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const toastConfig: Record<
    ToastType,
    { icon: React.ComponentType<{ className?: string }>; bgClass: string; borderClass: string; iconClass: string }
> = {
    success: {
        icon: IconCheck,
        bgClass: "bg-green-500/10",
        borderClass: "border-green-500/30",
        iconClass: "text-green-400",
    },
    error: {
        icon: IconAlertCircle,
        bgClass: "bg-red-500/10",
        borderClass: "border-red-500/30",
        iconClass: "text-red-400",
    },
    info: {
        icon: IconInfoCircle,
        bgClass: "bg-blue-500/10",
        borderClass: "border-blue-500/30",
        iconClass: "text-blue-400",
    },
    warning: {
        icon: IconAlertTriangle,
        bgClass: "bg-amber-500/10",
        borderClass: "border-amber-500/30",
        iconClass: "text-amber-400",
    },
};

function ToastItem({
    toast,
    onRemove,
}: {
    toast: Toast;
    onRemove: (id: string) => void;
}) {
    const config = toastConfig[toast.type];
    const Icon = config.icon;

    React.useEffect(() => {
        const duration = toast.duration ?? 4000;
        if (duration > 0) {
            const timer = setTimeout(() => onRemove(toast.id), duration);
            return () => clearTimeout(timer);
        }
    }, [toast.id, toast.duration, onRemove]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
            className={cn(
                "relative flex items-start gap-3 w-full max-w-sm p-4 rounded-xl border backdrop-blur-md shadow-lg",
                config.bgClass,
                config.borderClass
            )}
        >
            <div className={cn("p-1.5 rounded-lg", config.bgClass)}>
                <Icon className={cn("h-4 w-4", config.iconClass)} />
            </div>

            <div className="flex-1 min-w-0">
                <p className="font-medium text-white text-sm">{toast.title}</p>
                {toast.message && (
                    <p className="text-xs text-neutral-400 mt-0.5 line-clamp-2">
                        {toast.message}
                    </p>
                )}
            </div>

            <button
                onClick={() => onRemove(toast.id)}
                className="shrink-0 p-1 rounded-lg hover:bg-white/10 text-neutral-500 hover:text-white transition-colors"
            >
                <IconX className="h-4 w-4" />
            </button>

            <motion.div
                initial={{ scaleX: 1 }}
                animate={{ scaleX: 0 }}
                transition={{ duration: (toast.duration ?? 4000) / 1000, ease: "linear" }}
                className={cn(
                    "absolute bottom-0 left-0 right-0 h-0.5 origin-left rounded-b-xl",
                    toast.type === "success" && "bg-green-500",
                    toast.type === "error" && "bg-red-500",
                    toast.type === "info" && "bg-blue-500",
                    toast.type === "warning" && "bg-amber-500"
                )}
            />
        </motion.div>
    );
}

function ToastContainer() {
    const context = useContext(ToastContext);
    if (!context) return null;

    const { toasts, removeToast } = context;

    return (
        <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
            <AnimatePresence mode="popLayout">
                {toasts.map((toast) => (
                    <div key={toast.id} className="pointer-events-auto">
                        <ToastItem toast={toast} onRemove={removeToast} />
                    </div>
                ))}
            </AnimatePresence>
        </div>
    );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const addToast = useCallback((toast: Omit<Toast, "id">) => {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
        setToasts((prev) => [...prev, { ...toast, id }]);
    }, []);

    const success = useCallback(
        (title: string, message?: string) => {
            addToast({ type: "success", title, message });
        },
        [addToast]
    );

    const error = useCallback(
        (title: string, message?: string) => {
            addToast({ type: "error", title, message });
        },
        [addToast]
    );

    const info = useCallback(
        (title: string, message?: string) => {
            addToast({ type: "info", title, message });
        },
        [addToast]
    );

    const warning = useCallback(
        (title: string, message?: string) => {
            addToast({ type: "warning", title, message });
        },
        [addToast]
    );

    return (
        <ToastContext.Provider
            value={{ toasts, addToast, removeToast, success, error, info, warning }}
        >
            {children}
            <ToastContainer />
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within a ToastProvider");
    }
    return context;
}

let globalToast: ToastContextValue | null = null;

export function setGlobalToast(toast: ToastContextValue) {
    globalToast = toast;
}

export const toast = {
    success: (title: string, message?: string) => globalToast?.success(title, message),
    error: (title: string, message?: string) => globalToast?.error(title, message),
    info: (title: string, message?: string) => globalToast?.info(title, message),
    warning: (title: string, message?: string) => globalToast?.warning(title, message),
};
