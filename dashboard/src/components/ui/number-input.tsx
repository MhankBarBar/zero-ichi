"use client";

import { cn } from "@/lib/utils";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import * as React from "react";

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
            {label && <label className="text-sm font-medium text-neutral-300">{label}</label>}
            <div className="flex items-center">
                <button
                    type="button"
                    onClick={handleDecrement}
                    disabled={disabled || value <= min}
                    className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-l-lg",
                        "border border-r-0 border-neutral-700 bg-neutral-800",
                        "text-neutral-400 hover:bg-neutral-700 hover:text-white",
                        "transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                        "focus:ring-2 focus:ring-green-500/50 focus:outline-none",
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
                        "h-10 w-20 text-center font-medium text-white",
                        "border-y border-neutral-700 bg-neutral-800",
                        "focus:border-green-500 focus:ring-2 focus:ring-green-500/50 focus:outline-none",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
                    )}
                />

                <button
                    type="button"
                    onClick={handleIncrement}
                    disabled={disabled || value >= max}
                    className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-r-lg",
                        "border border-l-0 border-neutral-700 bg-neutral-800",
                        "text-neutral-400 hover:bg-neutral-700 hover:text-white",
                        "transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                        "focus:ring-2 focus:ring-green-500/50 focus:outline-none",
                    )}
                >
                    <IconPlus className="h-4 w-4" />
                </button>
            </div>
            {description && <p className="text-xs text-neutral-500">{description}</p>}
        </div>
    );
}
