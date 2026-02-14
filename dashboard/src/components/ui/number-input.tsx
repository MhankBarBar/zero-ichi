"use client";

import * as React from "react";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { cn } from "@/lib/utils";

interface NumberInputProps {
    value: number;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
    step?: number;
    disabled?: boolean;
    className?: string;
    label?: string;
    description?: string;
}

export function NumberInput({
    value,
    onChange,
    min = 0,
    max = 999,
    step = 1,
    disabled = false,
    className,
    label,
    description,
}: NumberInputProps) {
    const handleIncrement = () => {
        if (value + step <= max) {
            onChange(value + step);
        }
    };

    const handleDecrement = () => {
        if (value - step >= min) {
            onChange(value - step);
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = parseInt(e.target.value, 10);
        if (!isNaN(newValue) && newValue >= min && newValue <= max) {
            onChange(newValue);
        } else if (e.target.value === "") {
            onChange(min);
        }
    };

    return (
        <div className={cn("space-y-2", className)}>
            {label && (
                <label className="text-sm font-medium text-neutral-300">{label}</label>
            )}
            <div className="flex items-center">
                <button
                    type="button"
                    onClick={handleDecrement}
                    disabled={disabled || value <= min}
                    className={cn(
                        "h-10 w-10 rounded-l-lg flex items-center justify-center",
                        "bg-neutral-800 border border-r-0 border-neutral-700",
                        "text-neutral-400 hover:text-white hover:bg-neutral-700",
                        "transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                        "focus:outline-none focus:ring-2 focus:ring-green-500/50"
                    )}
                >
                    <IconMinus className="h-4 w-4" />
                </button>

                <input
                    type="number"
                    value={value}
                    onChange={handleInputChange}
                    min={min}
                    max={max}
                    step={step}
                    disabled={disabled}
                    className={cn(
                        "h-10 w-20 text-center text-white font-medium",
                        "bg-neutral-800 border-y border-neutral-700",
                        "focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                        "[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    )}
                />

                <button
                    type="button"
                    onClick={handleIncrement}
                    disabled={disabled || value >= max}
                    className={cn(
                        "h-10 w-10 rounded-r-lg flex items-center justify-center",
                        "bg-neutral-800 border border-l-0 border-neutral-700",
                        "text-neutral-400 hover:text-white hover:bg-neutral-700",
                        "transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                        "focus:outline-none focus:ring-2 focus:ring-green-500/50"
                    )}
                >
                    <IconPlus className="h-4 w-4" />
                </button>
            </div>
            {description && (
                <p className="text-xs text-neutral-500">{description}</p>
            )}
        </div>
    );
}
