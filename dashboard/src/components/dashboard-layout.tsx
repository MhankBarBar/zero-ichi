"use client";

import { cn } from "@/lib/utils";
import {
    IconBan,
    IconCalendarEvent,
    IconChartBar,
    IconCommand,
    IconFileText,
    IconFilter,
    IconFlag,
    IconHeart,
    IconHome,
    IconLogout,
    IconMenu2,
    IconNote,
    IconSend,
    IconSettings,
    IconSparkles,
    IconUsers,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "motion/react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";

const navLinks = [
    { label: "Dashboard", href: "/", icon: <IconHome className="h-5 w-5" /> },
    { label: "Send Message", href: "/send", icon: <IconSend className="h-5 w-5" /> },
    { label: "Configuration", href: "/config", icon: <IconSettings className="h-5 w-5" /> },
    { label: "Commands", href: "/commands", icon: <IconCommand className="h-5 w-5" /> },
    { label: "Groups", href: "/groups", icon: <IconUsers className="h-5 w-5" /> },
    { label: "Notes", href: "/notes", icon: <IconNote className="h-5 w-5" /> },
    { label: "Filters", href: "/filters", icon: <IconFilter className="h-5 w-5" /> },
    { label: "Tasks", href: "/tasks", icon: <IconCalendarEvent className="h-5 w-5" /> },
    { label: "Blacklist", href: "/blacklist", icon: <IconBan className="h-5 w-5" /> },
    { label: "Reports", href: "/reports", icon: <IconFlag className="h-5 w-5" /> },
    { label: "Digest", href: "/digest", icon: <IconCalendarEvent className="h-5 w-5" /> },
    { label: "Automations", href: "/automations", icon: <IconSparkles className="h-5 w-5" /> },
    { label: "Analytics", href: "/analytics", icon: <IconChartBar className="h-5 w-5" /> },
    { label: "Welcome", href: "/welcome", icon: <IconHeart className="h-5 w-5" /> },
    { label: "Logs", href: "/logs", icon: <IconFileText className="h-5 w-5" /> },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const pathname = usePathname();

    if (pathname === "/login") {
        return <>{children}</>;
    }

    return (
        <div className="min-h-screen bg-neutral-900">
            <div className="flex items-center justify-between border-b border-neutral-700 bg-neutral-800 p-4 md:hidden">
                <Link href="/" className="flex items-center gap-2">
                    <Image
                        src="/logo.png"
                        alt="Zero Ichi"
                        width={32}
                        height={32}
                        className="h-8 w-8 rounded-lg object-cover"
                    />
                    <span className="text-lg font-bold text-white">Zero Ichi</span>
                </Link>
                <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="p-2 text-neutral-400 hover:text-white"
                >
                    {mobileMenuOpen ? (
                        <IconX className="h-6 w-6" />
                    ) : (
                        <IconMenu2 className="h-6 w-6" />
                    )}
                </button>
            </div>

            <AnimatePresence>
                {mobileMenuOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setMobileMenuOpen(false)}
                            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
                        />
                        <motion.div
                            initial={{ x: "-100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "-100%" }}
                            transition={{ type: "spring", bounce: 0, duration: 0.3 }}
                            className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-neutral-800 bg-neutral-900 shadow-2xl md:hidden"
                        >
                            <div className="flex items-center justify-between border-b border-neutral-800 bg-neutral-900/50 p-4 backdrop-blur-md">
                                <Link
                                    href="/"
                                    onClick={() => setMobileMenuOpen(false)}
                                    className="flex items-center gap-2"
                                >
                                    <Image
                                        src="/logo.png"
                                        alt="Zero Ichi"
                                        width={32}
                                        height={32}
                                        className="h-8 w-8 rounded-lg object-cover"
                                    />
                                    <span className="text-lg font-bold text-white">Zero Ichi</span>
                                </Link>
                                <button
                                    onClick={() => setMobileMenuOpen(false)}
                                    className="rounded-lg p-1 text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-white"
                                >
                                    <IconX className="h-5 w-5" />
                                </button>
                            </div>

                            <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
                                {navLinks.map((link) => (
                                    <Link
                                        key={link.href}
                                        href={link.href}
                                        onClick={() => setMobileMenuOpen(false)}
                                        className={cn(
                                            "flex items-center gap-3 rounded-lg px-3 py-3 transition-all",
                                            pathname === link.href
                                                ? "border border-green-500/20 bg-green-500/10 font-medium text-green-400"
                                                : "border border-transparent text-neutral-400 hover:bg-neutral-800 hover:text-white",
                                        )}
                                    >
                                        {link.icon}
                                        <span className="text-sm">{link.label}</span>
                                    </Link>
                                ))}
                            </nav>

                            <div className="border-t border-neutral-800 bg-neutral-900/50 p-4 backdrop-blur-md">
                                <button
                                    onClick={() => {
                                        localStorage.removeItem("dashboard_auth");
                                        window.location.href = "/login";
                                    }}
                                    className="flex w-full items-center gap-3 rounded-lg border border-transparent px-3 py-3 text-neutral-400 transition-all hover:border-red-500/20 hover:bg-red-500/10 hover:text-red-400"
                                >
                                    <IconLogout className="h-5 w-5" />
                                    <span className="text-sm font-medium">Logout</span>
                                </button>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            <div className="flex">
                <motion.aside
                    className="sticky top-0 left-0 z-40 hidden h-screen flex-col border-r border-neutral-700 bg-neutral-800 md:flex"
                    animate={{ width: sidebarOpen ? 240 : 72 }}
                    onMouseEnter={() => setSidebarOpen(true)}
                    onMouseLeave={() => setSidebarOpen(false)}
                >
                    <Link
                        href="/"
                        className="flex items-center gap-2 border-b border-neutral-700 p-4"
                    >
                        <Image
                            src="/logo.png"
                            alt="Zero Ichi"
                            width={40}
                            height={40}
                            className="h-10 w-10 shrink-0 rounded-lg object-cover"
                        />
                        <motion.span
                            animate={{
                                opacity: sidebarOpen ? 1 : 0,
                                display: sidebarOpen ? "block" : "none",
                            }}
                            className="text-lg font-bold whitespace-nowrap text-white"
                        >
                            Zero Ichi
                        </motion.span>
                    </Link>

                    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
                        {navLinks.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors",
                                    pathname === link.href
                                        ? "bg-green-600/20 text-green-400"
                                        : "text-neutral-400 hover:bg-neutral-700 hover:text-white",
                                )}
                            >
                                <span className="shrink-0">{link.icon}</span>
                                <motion.span
                                    animate={{
                                        opacity: sidebarOpen ? 1 : 0,
                                        display: sidebarOpen ? "block" : "none",
                                    }}
                                    className="text-sm whitespace-nowrap"
                                >
                                    {link.label}
                                </motion.span>
                            </Link>
                        ))}
                    </nav>

                    <div className="space-y-2 border-t border-neutral-700 p-4">
                        <button
                            onClick={() => {
                                localStorage.removeItem("dashboard_auth");
                                window.location.href = "/login";
                            }}
                            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-neutral-400 transition-all hover:bg-red-500/10 hover:text-red-400"
                        >
                            <IconLogout className="h-5 w-5 shrink-0" />
                            <motion.span
                                animate={{
                                    opacity: sidebarOpen ? 1 : 0,
                                    display: sidebarOpen ? "block" : "none",
                                }}
                                className="text-sm whitespace-nowrap"
                            >
                                Logout
                            </motion.span>
                        </button>
                    </div>
                </motion.aside>

                <main className="min-h-screen flex-1 overflow-x-hidden">
                    <div className="max-w-full overflow-hidden p-4 md:p-8">{children}</div>
                </main>
            </div>
        </div>
    );
}
