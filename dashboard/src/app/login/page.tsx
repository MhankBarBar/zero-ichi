"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { IconLock, IconUser, IconAlertCircle, IconRefresh } from "@tabler/icons-react";
import { motion } from "framer-motion";

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
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/status`, {
                headers: {
                    "Authorization": `Basic ${auth}`
                }
            });

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
        <div className="min-h-screen flex items-center justify-center bg-black p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-md"
            >
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-green-500 mb-4 shadow-lg shadow-green-500/20">
                        <IconLock className="h-8 w-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Zero Ichi</h1>
                    <p className="text-neutral-500 mt-2">Dashboard Login</p>
                </div>

                <Card className="bg-neutral-900/50 backdrop-blur-sm border-neutral-800">
                    <CardHeader>
                        <CardTitle className="text-white text-lg">Login</CardTitle>
                        <CardDescription>Enter your credentials to access the dashboard</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleLogin} className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-neutral-500 uppercase tracking-widest">Username</label>
                                <div className="relative">
                                    <IconUser className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                                    <Input
                                        placeholder="Username"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="bg-neutral-800 border-neutral-700 text-white pl-10 h-11"
                                        required
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-neutral-500 uppercase tracking-widest">Password</label>
                                <div className="relative">
                                    <IconLock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                                    <Input
                                        type="password"
                                        placeholder="Password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="bg-neutral-800 border-neutral-700 text-white pl-10 h-11"
                                        required
                                    />
                                </div>
                            </div>

                            {error && (
                                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2 text-red-400 text-sm">
                                    <IconAlertCircle className="h-4 w-4 shrink-0" />
                                    <p>{error}</p>
                                </div>
                            )}

                            <Button
                                type="submit"
                                className="w-full h-11 bg-green-600 hover:bg-green-500 text-white font-bold gap-2 mt-4"
                                disabled={loading}
                            >
                                {loading ? <IconRefresh className="h-4 w-4 animate-spin" /> : null}
                                {loading ? "Authenticating..." : "Access Dashboard"}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                <p className="text-center text-neutral-600 text-xs mt-8">
                    Credentials can be set in your <span className="font-mono text-neutral-500">.env</span> file
                </p>
            </motion.div>
        </div>
    );
}
