"use client";

import { IconChevronDown } from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

interface Option {
    label: string;
    value: string;
}

interface CustomSelectProps {
    options: Option[];
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

export function CustomSelect({
    options,
    value,
    onChange,
    placeholder = "Select option",
    className = "",
}: CustomSelectProps) {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const selectedOption = options.find((opt) => opt.value === value);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div className={`relative w-48 ${className}`} ref={containerRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex w-full items-center justify-between rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-white transition-colors outline-none hover:border-neutral-600 focus:ring-2 focus:ring-green-500/20"
            >
                <span className="truncate">
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
                    <IconChevronDown className="h-4 w-4 text-neutral-400" />
                </motion.div>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.15 }}
                        className="absolute z-50 mt-2 max-h-60 w-full overflow-hidden overflow-y-auto rounded-lg border border-neutral-700 bg-neutral-800 shadow-xl"
                    >
                        {options.map((option) => (
                            <div
                                key={option.value}
                                onClick={() => {
                                    onChange(option.value);
                                    setIsOpen(false);
                                }}
                                className={`cursor-pointer px-3 py-2 text-sm transition-colors ${
                                    option.value === value
                                        ? "bg-green-500/10 text-green-400"
                                        : "text-neutral-300 hover:bg-neutral-700/50 hover:text-white"
                                }`}
                            >
                                {option.label}
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
