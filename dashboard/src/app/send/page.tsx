"use client";

import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle, GlowCard } from "@/components/ui/card";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import {
    IconFile,
    IconMusic,
    IconPhoto,
    IconRefresh,
    IconSend,
    IconSticker,
    IconTrash,
    IconTypeface,
    IconUpload,
    IconVideo,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";

type MediaType = "text" | "image" | "video" | "audio" | "document" | "sticker";

interface SavedRecipient {
    jid: string;
    name: string;
}

const mediaTypes: {
    type: MediaType;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    hint: string;
}[] = [
    { type: "text", label: "Text", icon: IconTypeface, hint: "Plain text" },
    { type: "image", label: "Image", icon: IconPhoto, hint: "JPG, PNG, WEBP" },
    { type: "video", label: "Video", icon: IconVideo, hint: "MP4" },
    { type: "audio", label: "Audio", icon: IconMusic, hint: "MP3, OGG" },
    { type: "document", label: "Doc", icon: IconFile, hint: "Any file" },
    { type: "sticker", label: "Sticker", icon: IconSticker, hint: "PNG, WEBP" },
];

function FileUpload({
    activeType,
    file,
    onFileChange,
}: {
    activeType: MediaType;
    file: File | null;
    onFileChange: (file: File | null) => void;
}) {
    const getAcceptTypes = (): Record<string, string[]> | undefined => {
        switch (activeType) {
            case "image":
                return { "image/*": [] };
            case "video":
                return { "video/*": [] };
            case "audio":
                return { "audio/*": [] };
            case "sticker":
                return { "image/*": [] };
            default:
                return undefined;
        }
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        multiple: false,
        accept: getAcceptTypes(),
        onDrop: (acceptedFiles) => {
            if (acceptedFiles.length > 0) {
                onFileChange(acceptedFiles[0]);
            }
        },
    });

    const currentType = mediaTypes.find((m) => m.type === activeType);

    return (
        <div
            {...getRootProps()}
            className={`relative cursor-pointer rounded-xl border-2 border-dashed transition-all ${
                isDragActive
                    ? "border-green-500 bg-green-500/10"
                    : file
                      ? "border-green-500/50 bg-green-500/5"
                      : "border-neutral-700 hover:border-neutral-500"
            }`}
        >
            <input {...getInputProps()} />

            <div className="p-8">
                <AnimatePresence mode="wait">
                    {file ? (
                        <motion.div
                            key="file"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex items-center gap-4"
                        >
                            <div className="rounded-xl bg-green-500/20 p-3">
                                {currentType && (
                                    <currentType.icon className="h-6 w-6 text-green-400" />
                                )}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="truncate font-medium text-white">{file.name}</p>
                                <p className="text-sm text-neutral-500">
                                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                                </p>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onFileChange(null);
                                }}
                            >
                                <IconTrash className="h-4 w-4" />
                            </Button>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="empty"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center py-4 text-center"
                        >
                            <div className="mb-4 rounded-full bg-neutral-800 p-4">
                                <IconUpload className="h-8 w-8 text-neutral-400" />
                            </div>
                            <p className="font-medium text-white">
                                {isDragActive ? "Drop it here!" : `Upload ${activeType}`}
                            </p>
                            <p className="mt-1 text-sm text-neutral-500">
                                Drag & drop or click • {currentType?.hint}
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

export default function SendPage() {
    const [activeType, setActiveType] = useState<MediaType>("text");
    const [recipient, setRecipient] = useState("");
    const [recipientName, setRecipientName] = useState("");
    const [savedRecipients, setSavedRecipients] = useState<SavedRecipient[]>([]);
    const [message, setMessage] = useState("");
    const [caption, setCaption] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [sending, setSending] = useState(false);
    const toast = useToast();

    useEffect(() => {
        const saved = localStorage.getItem("saved_recipients");
        if (saved) {
            try {
                setSavedRecipients(JSON.parse(saved));
            } catch (e) {
                console.error("Failed to parse saved recipients");
            }
        }
    }, []);

    const saveRecipient = () => {
        if (!recipient) return;
        const newRecipients = [
            { jid: recipient, name: recipientName || recipient },
            ...savedRecipients.filter((r) => r.jid !== recipient),
        ].slice(0, 10);

        setSavedRecipients(newRecipients);
        localStorage.setItem("saved_recipients", JSON.stringify(newRecipients));
        setRecipientName("");
        toast.success("Saved!", "Recipient added to quick access");
    };

    const removeRecipient = (jid: string) => {
        const newRecipients = savedRecipients.filter((r) => r.jid !== jid);
        setSavedRecipients(newRecipients);
        localStorage.setItem("saved_recipients", JSON.stringify(newRecipients));
    };

    const resetForm = () => {
        setMessage("");
        setCaption("");
        setFile(null);
    };

    const handleSubmit = async () => {
        if (!recipient) {
            toast.error("Missing recipient", "Enter a phone number or group ID");
            return;
        }

        setSending(true);

        try {
            if (activeType === "text") {
                if (!message) throw new Error("Message content is required");
                await api.sendMessage(recipient, message);
            } else {
                if (!file) throw new Error(`Please select a ${activeType} file`);
                await api.sendMedia(recipient, activeType, file, caption);
            }

            // Auto-save recipient if not already saved
            const alreadySaved = savedRecipients.some((r) => r.jid === recipient);
            if (!alreadySaved) {
                const newRecipient = {
                    jid: recipient,
                    name: recipientName || recipient.replace(/@.*$/, "").slice(-6),
                };
                const newRecipients = [...savedRecipients, newRecipient];
                setSavedRecipients(newRecipients);
                localStorage.setItem("saved_recipients", JSON.stringify(newRecipients));
            }

            toast.success("Sent!", "Message delivered successfully");
            resetForm();
        } catch (err: any) {
            toast.error("Failed to send", err.message || "Something went wrong");
        } finally {
            setSending(false);
        }
    };

    const isFormValid = recipient && (activeType === "text" ? message : file);

    return (
        <div className="mx-auto max-w-3xl space-y-6">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
                <h1 className="text-3xl font-bold text-white">Send Message</h1>
                <p className="mt-1 text-neutral-500">Send text, images, videos, and more</p>
            </motion.div>

            <div className="space-y-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-base text-white">Recipient</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex flex-col gap-2 sm:flex-row">
                                <Input
                                    placeholder="Phone or Group ID (e.g. 628123456789)"
                                    value={recipient}
                                    onChange={(e) => setRecipient(e.target.value)}
                                    className="h-11 flex-1 border-neutral-700 bg-neutral-800 font-mono text-sm text-white"
                                />
                                <Input
                                    placeholder="Label (optional)"
                                    value={recipientName}
                                    onChange={(e) => setRecipientName(e.target.value)}
                                    className="h-11 border-neutral-700 bg-neutral-800 text-white sm:w-40"
                                />
                            </div>

                            {savedRecipients.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {savedRecipients.map((r) => (
                                        <button
                                            key={r.jid}
                                            onClick={() => setRecipient(r.jid)}
                                            className={`flex items-center gap-1.5 rounded-full py-1.5 pr-1.5 pl-3 text-xs font-medium transition-all ${
                                                recipient === r.jid
                                                    ? "bg-green-500/20 text-green-400 ring-1 ring-green-500/50"
                                                    : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700 hover:text-white"
                                            }`}
                                        >
                                            {r.name}
                                            <span
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    removeRecipient(r.jid);
                                                }}
                                                className="rounded-full p-0.5 hover:bg-red-500/20 hover:text-red-400"
                                            >
                                                <IconX className="h-3 w-3" />
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </GlowCard>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                        <CardContent className="p-6">
                            <div className="mb-6 flex gap-1 overflow-x-auto rounded-xl bg-neutral-800/50 p-1">
                                {mediaTypes.map((item) => {
                                    const Icon = item.icon;
                                    const isActive = activeType === item.type;
                                    return (
                                        <button
                                            key={item.type}
                                            onClick={() => {
                                                setActiveType(item.type);
                                                resetForm();
                                            }}
                                            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-all ${
                                                isActive
                                                    ? "bg-white text-black shadow-lg"
                                                    : "text-neutral-400 hover:bg-neutral-700/50 hover:text-white"
                                            }`}
                                        >
                                            <Icon className="h-4 w-4" />
                                            <span className="hidden sm:inline">{item.label}</span>
                                        </button>
                                    );
                                })}
                            </div>

                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={activeType}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    transition={{ duration: 0.15 }}
                                    className="space-y-4"
                                >
                                    {activeType === "text" ? (
                                        <textarea
                                            placeholder="Type your message here..."
                                            value={message}
                                            onChange={(e) => setMessage(e.target.value)}
                                            className="min-h-[200px] w-full resize-none rounded-xl border border-neutral-700 bg-neutral-800/50 p-4 text-base text-white transition-all placeholder:text-neutral-600 focus:border-green-500/50 focus:ring-2 focus:ring-green-500/50 focus:outline-none"
                                        />
                                    ) : (
                                        <>
                                            <FileUpload
                                                activeType={activeType}
                                                file={file}
                                                onFileChange={setFile}
                                            />

                                            {(activeType === "image" ||
                                                activeType === "video" ||
                                                activeType === "document") && (
                                                <Input
                                                    placeholder="Caption (optional)"
                                                    value={caption}
                                                    onChange={(e) => setCaption(e.target.value)}
                                                    className="h-11 border-neutral-700 bg-neutral-800/50 text-white"
                                                />
                                            )}
                                        </>
                                    )}
                                </motion.div>
                            </AnimatePresence>

                            <div className="mt-6 flex flex-col gap-3 border-t border-neutral-800 pt-6 sm:flex-row">
                                <HoverBorderGradient
                                    containerClassName="flex-1 rounded-xl"
                                    className={`flex w-full items-center justify-center gap-2 font-semibold ${
                                        !isFormValid || sending ? "opacity-50" : ""
                                    }`}
                                    disabled={!isFormValid || sending}
                                    onClick={handleSubmit}
                                >
                                    {sending ? (
                                        <>
                                            <IconRefresh className="h-5 w-5 animate-spin" />
                                            Sending...
                                        </>
                                    ) : (
                                        <>
                                            <IconSend className="h-5 w-5" />
                                            Send{" "}
                                            {activeType === "text"
                                                ? "Message"
                                                : activeType.charAt(0).toUpperCase() +
                                                  activeType.slice(1)}
                                        </>
                                    )}
                                </HoverBorderGradient>
                                <Button
                                    variant="outline"
                                    className="h-12 border-neutral-700 px-6 text-neutral-400 hover:bg-neutral-800 hover:text-white"
                                    onClick={resetForm}
                                >
                                    Clear
                                </Button>
                            </div>
                        </CardContent>
                    </GlowCard>
                </motion.div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
            >
                <GlowCard className="border-neutral-800 bg-neutral-900/50 backdrop-blur-sm">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-bold tracking-widest text-white uppercase">
                            Help & Tips
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-neutral-500">
                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                            <div>
                                <p className="mb-1 font-medium text-neutral-300">Direct Numbers</p>
                                <p>Use full international format without '+' or spaces.</p>
                                <code className="mt-2 block rounded-lg bg-neutral-800 px-3 py-2 font-mono text-xs text-green-400">
                                    628123456789
                                </code>
                            </div>
                            <div>
                                <p className="mb-1 font-medium text-neutral-300">Group IDs</p>
                                <p>Group JIDs usually end with @g.us.</p>
                                <code className="mt-2 block rounded-lg bg-neutral-800 px-3 py-2 font-mono text-xs text-green-400">
                                    12345@g.us
                                </code>
                            </div>
                            <div>
                                <p className="mb-2 font-medium text-neutral-300">
                                    Supported Formats
                                </p>
                                <ul className="space-y-1.5">
                                    <li className="flex items-center gap-2">
                                        <IconPhoto className="h-3.5 w-3.5 text-green-400" />
                                        <span>Image: JPG, PNG, WEBP</span>
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <IconVideo className="h-3.5 w-3.5 text-purple-400" />
                                        <span>Video: MP4</span>
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <IconMusic className="h-3.5 w-3.5 text-amber-400" />
                                        <span>Audio: MP3, OGG</span>
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <IconSticker className="h-3.5 w-3.5 text-pink-400" />
                                        <span>Sticker: PNG, JPG, WEBP</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </CardContent>
                </GlowCard>
            </motion.div>
        </div>
    );
}
