"use client";

import React, { Component, ReactNode } from "react";
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react";
import { Button } from "@/components/ui/button";

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
                <div className="min-h-[200px] flex flex-col items-center justify-center p-8 bg-neutral-900/50 rounded-xl border border-neutral-800">
                    <div className="p-4 rounded-full bg-red-500/20 mb-4">
                        <IconAlertTriangle className="h-8 w-8 text-red-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">
                        Something went wrong
                    </h3>
                    <p className="text-sm text-neutral-400 text-center mb-4 max-w-md">
                        {this.state.error?.message || "An unexpected error occurred"}
                    </p>
                    <Button
                        onClick={this.handleReset}
                        variant="outline"
                        className="gap-2"
                    >
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
    fallback?: ReactNode
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
            className={`bg-neutral-800/50 rounded-xl border border-neutral-800 animate-pulse ${className}`}
        >
            <div className="p-6 space-y-4">
                <div className="h-4 bg-neutral-700 rounded w-1/3" />
                <div className="h-8 bg-neutral-700 rounded w-1/2" />
                <div className="h-3 bg-neutral-700 rounded w-2/3" />
            </div>
        </div>
    );
}

export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
    return (
        <div className="flex items-center gap-4 p-4 bg-neutral-800/30 rounded-lg animate-pulse">
            {Array.from({ length: columns }).map((_, i) => (
                <div
                    key={i}
                    className="h-4 bg-neutral-700 rounded flex-1"
                    style={{ maxWidth: i === 0 ? "40%" : "20%" }}
                />
            ))}
        </div>
    );
}

export function PageSkeleton() {
    return (
        <div className="space-y-6 animate-pulse">
            {/* Header skeleton */}
            <div className="flex justify-between items-center">
                <div className="space-y-2">
                    <div className="h-8 bg-neutral-700 rounded w-48" />
                    <div className="h-4 bg-neutral-700 rounded w-64" />
                </div>
                <div className="h-10 bg-neutral-700 rounded w-24" />
            </div>

            {/* Stats row skeleton */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <CardSkeleton key={i} />
                ))}
            </div>

            {/* Content skeleton */}
            <div className="h-64 bg-neutral-800/50 rounded-xl border border-neutral-800" />
        </div>
    );
}
