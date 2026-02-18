"use client";

import { Button } from "@/components/ui/button";
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react";
import React, { Component, ReactNode } from "react";

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="flex min-h-[200px] flex-col items-center justify-center rounded-xl border border-neutral-800 bg-neutral-900/50 p-8">
                    <div className="mb-4 rounded-full bg-red-500/20 p-4">
                        <IconAlertTriangle className="h-8 w-8 text-red-400" />
                    </div>
                    <h3 className="mb-2 text-lg font-semibold text-white">Something went wrong</h3>
                    <p className="mb-4 max-w-md text-center text-sm text-neutral-400">
                        {this.state.error?.message || "An unexpected error occurred"}
                    </p>
                    <Button onClick={this.handleReset} variant="outline" className="gap-2">
                        <IconRefresh className="h-4 w-4" />
                        Try again
                    </Button>
                </div>
            );
        }

        return this.props.children;
    }
}

export function withErrorBoundary<P extends object>(
    WrappedComponent: React.ComponentType<P>,
    fallback?: ReactNode,
) {
    return function WithErrorBoundary(props: P) {
        return (
            <ErrorBoundary fallback={fallback}>
                <WrappedComponent {...props} />
            </ErrorBoundary>
        );
    };
}

export function CardSkeleton({ className = "" }: { className?: string }) {
    return (
        <div
            className={`animate-pulse rounded-xl border border-neutral-800 bg-neutral-800/50 ${className}`}
        >
            <div className="space-y-4 p-6">
                <div className="h-4 w-1/3 rounded bg-neutral-700" />
                <div className="h-8 w-1/2 rounded bg-neutral-700" />
                <div className="h-3 w-2/3 rounded bg-neutral-700" />
            </div>
        </div>
    );
}

export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
    return (
        <div className="flex animate-pulse items-center gap-4 rounded-lg bg-neutral-800/30 p-4">
            {Array.from({ length: columns }).map((_, i) => (
                <div
                    key={i}
                    className="h-4 flex-1 rounded bg-neutral-700"
                    style={{ maxWidth: i === 0 ? "40%" : "20%" }}
                />
            ))}
        </div>
    );
}

export function PageSkeleton() {
    return (
        <div className="animate-pulse space-y-6">
            <div className="flex items-center justify-between">
                <div className="space-y-2">
                    <div className="h-8 w-48 rounded bg-neutral-700" />
                    <div className="h-4 w-64 rounded bg-neutral-700" />
                </div>
                <div className="h-10 w-24 rounded bg-neutral-700" />
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                    <CardSkeleton key={i} />
                ))}
            </div>

            <div className="h-64 rounded-xl border border-neutral-800 bg-neutral-800/50" />
        </div>
    );
}
