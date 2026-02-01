"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

interface UseCachedFetchOptions {
    cacheTime?: number;
    refetchOnMount?: boolean;
    enabled?: boolean;
}

const cache = new Map<string, CacheEntry<unknown>>();

/**
 * Custom hook for fetching data with caching support
 */
export function useCachedFetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    options: UseCachedFetchOptions = {}
): {
    data: T | null;
    loading: boolean;
    error: Error | null;
    refetch: () => Promise<void>;
} {
    const {
        cacheTime = 30000,
        refetchOnMount = false,
        enabled = true,
    } = options;

    const [data, setData] = useState<T | null>(() => {
        const cached = cache.get(key) as CacheEntry<T> | undefined;
        if (cached && Date.now() - cached.timestamp < cacheTime) {
            return cached.data;
        }
        return null;
    });
    const [loading, setLoading] = useState(!data);
    const [error, setError] = useState<Error | null>(null);
    const isMounted = useRef(true);

    const fetchData = useCallback(async () => {
        if (!enabled) return;

        setLoading(true);
        setError(null);

        try {
            const result = await fetcher();
            if (isMounted.current) {
                setData(result);
                cache.set(key, { data: result, timestamp: Date.now() });
            }
        } catch (err) {
            if (isMounted.current) {
                setError(err instanceof Error ? err : new Error("Unknown error"));
            }
        } finally {
            if (isMounted.current) {
                setLoading(false);
            }
        }
    }, [key, fetcher, enabled]);

    useEffect(() => {
        isMounted.current = true;

        const cached = cache.get(key) as CacheEntry<T> | undefined;
        const isStale = !cached || Date.now() - cached.timestamp >= cacheTime;

        if (enabled && (isStale || refetchOnMount)) {
            fetchData();
        }

        return () => {
            isMounted.current = false;
        };
    }, [key, cacheTime, enabled, fetchData, refetchOnMount]);

    return {
        data,
        loading,
        error,
        refetch: fetchData,
    };
}

/**
 * Clear specific cache entries or all cache
 */
export function clearCache(key?: string): void {
    if (key) {
        cache.delete(key);
    } else {
        cache.clear();
    }
}

/**
 * Invalidate cache by pattern
 */
export function invalidateCache(pattern: RegExp | string): void {
    const keys = Array.from(cache.keys());
    for (const key of keys) {
        if (typeof pattern === "string" ? key.includes(pattern) : pattern.test(key)) {
            cache.delete(key);
        }
    }
}

/**
 * Hook to detect mobile viewport
 */
export function useIsMobile(breakpoint = 768): boolean {
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(window.innerWidth < breakpoint);
        };

        checkMobile();
        window.addEventListener("resize", checkMobile);
        return () => window.removeEventListener("resize", checkMobile);
    }, [breakpoint]);

    return isMobile;
}

/**
 * Hook for debounced values
 */
export function useDebounce<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);

    return debouncedValue;
}

/**
 * Hook for throttled callback
 */
export function useThrottle<T extends (...args: unknown[]) => unknown>(
    callback: T,
    delay: number
): T {
    const lastRun = useRef(Date.now());
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    return useCallback(
        ((...args: Parameters<T>) => {
            const now = Date.now();
            if (now - lastRun.current >= delay) {
                lastRun.current = now;
                callback(...args);
            } else {
                if (timeoutRef.current) {
                    clearTimeout(timeoutRef.current);
                }
                timeoutRef.current = setTimeout(
                    () => {
                        lastRun.current = Date.now();
                        callback(...args);
                    },
                    delay - (now - lastRun.current)
                );
            }
        }) as T,
        [callback, delay]
    );
}
