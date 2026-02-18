"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { IconAlertCircle, IconLock, IconRefresh, IconUser } from "@tabler/icons-react";
import { motion } from "framer-motion";
import { useState } from "react";

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const auth = btoa(`${username}:${password}`);

        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/status`,
                {
                    headers: {
                        Authorization: `Basic ${auth}`,
                    },
                },
            );

            if (res.ok) {
                localStorage.setItem("dashboard_auth", auth);
                window.location.href = "/";
            } else {
                setError("Invalid username or password");
            }
        } catch (err) {
            setError("Failed to connect to API server");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-black p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-md"
            >
                <div className="mb-8 text-center">
                    <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-green-500 shadow-lg shadow-green-500/20">
                        <IconLock className="h-8 w-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white">Zero Ichi</h1>
                    <p className="mt-2 text-neutral-500">Dashboard Login</p>
                </div>

                <Card className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                    <CardHeader>
                        <CardTitle className="text-lg text-white">Login</CardTitle>
                        <CardDescription>
                            Enter your credentials to access the dashboard
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleLogin} className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-bold tracking-widest text-neutral-500 uppercase">
                                    Username
                                </label>
                                <div className="relative">
                                    <IconUser className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                                    <Input
                                        placeholder="Username"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="h-11 border-neutral-700 bg-neutral-800 pl-10 text-white"
                                        required
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold tracking-widest text-neutral-500 uppercase">
                                    Password
                                </label>
                                <div className="relative">
                                    <IconLock className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                                    <Input
                                        type="password"
                                        placeholder="Password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="h-11 border-neutral-700 bg-neutral-800 pl-10 text-white"
                                        required
                                    />
                                </div>
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
                                    <IconAlertCircle className="h-4 w-4 shrink-0" />
                                    <p>{error}</p>
                                </div>
                            )}

                            <Button
                                type="submit"
                                className="mt-4 h-11 w-full gap-2 bg-green-600 font-bold text-white hover:bg-green-500"
                                disabled={loading}
                            >
                                {loading ? <IconRefresh className="h-4 w-4 animate-spin" /> : null}
                                {loading ? "Authenticating..." : "Access Dashboard"}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                <p className="mt-8 text-center text-xs text-neutral-600">
                    Credentials can be set in your{" "}
                    <span className="font-mono text-neutral-500">.env</span> file
                </p>
            </motion.div>
        </div>
    );
}
