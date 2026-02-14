"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  IconHome,
  IconSettings,
  IconCommand,
  IconUsers,
  IconFileText,

  IconMenu2,
  IconX,
  IconSend,
  IconLogout,
  IconNote,
  IconFilter,
  IconCalendarEvent,
  IconBan,
  IconChartBar,
  IconHeart,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";

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
  { label: "Analytics", href: "/analytics", icon: <IconChartBar className="h-5 w-5" /> },
  { label: "Welcome", href: "/welcome", icon: <IconHeart className="h-5 w-5" /> },
  { label: "Logs", href: "/logs", icon: <IconFileText className="h-5 w-5" /> },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  if (pathname === "/login") {
    return <>{children}</>;
  }


  return (
    <div className="min-h-screen bg-neutral-900">
      <div className="md:hidden flex items-center justify-between p-4 bg-neutral-800 border-b border-neutral-700">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/logo.png" alt="Zero Ichi" width={32} height={32} className="h-8 w-8 rounded-lg object-cover" />
          <span className="font-bold text-lg text-white">Zero Ichi</span>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-neutral-400 hover:text-white"
        >
          {mobileMenuOpen ? <IconX className="h-6 w-6" /> : <IconMenu2 className="h-6 w-6" />}
        </button>
      </div>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="md:hidden fixed inset-0 top-[65px] z-50 bg-neutral-900/95 backdrop-blur-sm"
          >
            <nav className="p-4 flex flex-col gap-2 h-full">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center gap-3 py-3 px-4 rounded-lg transition-colors",
                    pathname === link.href
                      ? "bg-green-600 text-white"
                      : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
                  )}
                >
                  {link.icon}
                  <span className="text-base">{link.label}</span>
                </Link>
              ))}

              <button
                onClick={() => {
                  localStorage.removeItem("dashboard_auth");
                  window.location.href = "/login";
                }}
                className="flex items-center gap-3 py-3 px-4 rounded-lg text-neutral-400 hover:bg-red-500/10 hover:text-red-400 transition-all mt-4"
              >
                <IconLogout className="h-5 w-5" />
                <span className="text-base">Logout</span>
              </button>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex">
        <motion.aside
          className="hidden md:flex flex-col h-screen bg-neutral-800 border-r border-neutral-700 sticky top-0 left-0 z-40"
          animate={{ width: sidebarOpen ? 240 : 72 }}
          onMouseEnter={() => setSidebarOpen(true)}
          onMouseLeave={() => setSidebarOpen(false)}
        >
          <Link href="/" className="flex items-center gap-2 p-4 border-b border-neutral-700">
            <Image src="/logo.png" alt="Zero Ichi" width={40} height={40} className="h-10 w-10 rounded-lg object-cover shrink-0" />
            <motion.span
              animate={{ opacity: sidebarOpen ? 1 : 0, display: sidebarOpen ? "block" : "none" }}
              className="font-bold text-lg text-white whitespace-nowrap"
            >
              Zero Ichi
            </motion.span>
          </Link>

          <nav className="flex-1 p-3 flex flex-col gap-1 overflow-y-auto">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-3 py-2.5 px-3 rounded-lg transition-colors",
                  pathname === link.href
                    ? "bg-green-600/20 text-green-400"
                    : "text-neutral-400 hover:bg-neutral-700 hover:text-white"
                )}
              >
                <span className="shrink-0">{link.icon}</span>
                <motion.span
                  animate={{ opacity: sidebarOpen ? 1 : 0, display: sidebarOpen ? "block" : "none" }}
                  className="text-sm whitespace-nowrap"
                >
                  {link.label}
                </motion.span>
              </Link>
            ))}
          </nav>

          <div className="p-4 border-t border-neutral-700 space-y-2">
            <button
              onClick={() => {
                localStorage.removeItem("dashboard_auth");
                window.location.href = "/login";
              }}
              className="flex items-center gap-3 w-full py-2 px-3 rounded-lg text-neutral-400 hover:bg-red-500/10 hover:text-red-400 transition-all"
            >
              <IconLogout className="h-5 w-5 shrink-0" />
              <motion.span
                animate={{ opacity: sidebarOpen ? 1 : 0, display: sidebarOpen ? "block" : "none" }}
                className="text-sm whitespace-nowrap"
              >
                Logout
              </motion.span>
            </button>
          </div>

        </motion.aside>

        <main className="flex-1 min-h-screen overflow-x-hidden">
          <div className="p-4 md:p-8 max-w-full overflow-hidden">{children}</div>
        </main>
      </div>
    </div>
  );
}
