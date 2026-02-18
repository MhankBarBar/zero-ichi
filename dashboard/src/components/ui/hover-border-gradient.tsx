"use client";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import React, { useCallback, useEffect, useState } from "react";

type Direction = "TOP" | "LEFT" | "BOTTOM" | "RIGHT";

export function HoverBorderGradient({
    children,
    containerClassName,
    className,
    duration = 1,
    clockwise = true,
    ...props
}: React.PropsWithChildren<
    {
        containerClassName?: string;
        className?: string;
        duration?: number;
        clockwise?: boolean;
    } & React.ButtonHTMLAttributes<HTMLButtonElement>
>) {
    const [hovered, setHovered] = useState<boolean>(false);
    const [direction, setDirection] = useState<Direction>("TOP");

    const rotateDirection = useCallback(
        (currentDirection: Direction): Direction => {
            const directions: Direction[] = ["TOP", "LEFT", "BOTTOM", "RIGHT"];
            const currentIndex = directions.indexOf(currentDirection);
            const nextIndex = clockwise
                ? (currentIndex - 1 + directions.length) % directions.length
                : (currentIndex + 1) % directions.length;
            return directions[nextIndex];
        },
        [clockwise],
    );

    const movingMap: Record<Direction, string> = {
        TOP: "radial-gradient(20.7% 50% at 50% 0%, #22c55e 0%, rgba(255, 255, 255, 0) 100%)",
        LEFT: "radial-gradient(16.6% 43.1% at 0% 50%, #22c55e 0%, rgba(255, 255, 255, 0) 100%)",
        BOTTOM: "radial-gradient(20.7% 50% at 50% 100%, #22c55e 0%, rgba(255, 255, 255, 0) 100%)",
        RIGHT: "radial-gradient(16.2% 41.199999999999996% at 100% 50%, #22c55e 0%, rgba(255, 255, 255, 0) 100%)",
    };

    const highlight =
        "radial-gradient(75% 181.15942028985506% at 50% 50%, #22c55e 0%, rgba(255, 255, 255, 0) 100%)";

    useEffect(() => {
        if (!hovered) {
            const interval = setInterval(() => {
                setDirection((prevState) => rotateDirection(prevState));
            }, duration * 1000);
            return () => clearInterval(interval);
        }
    }, [hovered, duration, rotateDirection]);

    return (
        <button
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            className={cn(
                "relative flex h-12 w-full flex-col flex-nowrap content-center items-center justify-center overflow-visible rounded-xl bg-neutral-900 decoration-clone p-px transition duration-500 hover:bg-neutral-800",
                containerClassName,
            )}
            {...props}
        >
            <div
                className={cn(
                    "z-10 flex h-full w-full items-center justify-center rounded-[inherit] bg-neutral-900 px-6 py-3 text-white",
                    className,
                )}
            >
                {children}
            </div>
            <motion.div
                className={cn("absolute inset-0 z-0 flex-none overflow-hidden rounded-[inherit]")}
                style={{
                    filter: "blur(2px)",
                    position: "absolute",
                    width: "100%",
                    height: "100%",
                }}
                initial={{ background: movingMap[direction] }}
                animate={{
                    background: hovered ? [movingMap[direction], highlight] : movingMap[direction],
                }}
                transition={{ ease: "linear", duration: duration ?? 1 }}
            />
            <div className="absolute inset-[2px] z-1 flex-none rounded-[inherit] bg-neutral-900" />
        </button>
    );
}
