"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, type Group, type Note } from "@/lib/api";
import {
    IconAlertCircle,
    IconDeviceFloppy,
    IconEdit,
    IconFile,
    IconFileText,
    IconNote,
    IconPhoto,
    IconPlus,
    IconSearch,
    IconTrash,
    IconUpload,
    IconUsers,
    IconVideo,
    IconVolume,
    IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

interface NoteModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (name: string, content: string, file: File | null) => void;
    editingNote?: Note | null;
}

function NoteModal({ isOpen, onClose, onSave, editingNote }: NoteModalProps) {
    const [name, setName] = useState(editingNote?.name || "");
    const [content, setContent] = useState(editingNote?.content || "");
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = (selectedFile: File) => {
        setFile(selectedFile);
        if (selectedFile.type.startsWith("image/")) {
            const url = URL.createObjectURL(selectedFile);
            setPreview(url);
        } else {
            setPreview(null);
        }
    };

    const handleSave = () => {
        if (!name.trim()) return;
        if (!content.trim() && !file) return;
        onSave(name.trim(), content, file);
        onClose();
    };

    if (!isOpen) return null;

    const fileTypeLabel = file
        ? file.name.endsWith(".webp")
            ? "Sticker"
            : file.type.split("/")[0]
        : null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="mx-4 w-full max-w-lg rounded-2xl border border-neutral-700 bg-neutral-900 p-6 shadow-2xl"
            >
                <div className="mb-6 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">
                        {editingNote ? "Edit Note" : "Create Note"}
                    </h2>
                    <button onClick={onClose} className="text-neutral-400 hover:text-white">
                        <IconX className="h-5 w-5" />
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Note Name
                        </label>
                        <Input
                            placeholder="e.g. rules, welcome, faq"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            disabled={!!editingNote}
                            className="border-neutral-700 bg-neutral-800 text-white"
                        />
                        <p className="mt-1 text-xs text-neutral-500">
                            Users can retrieve this note using #{name || "notename"}
                        </p>
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Content (caption)
                        </label>
                        <textarea
                            placeholder="Enter note content or caption..."
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={4}
                            className="w-full resize-none rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-white placeholder-neutral-500 focus:ring-2 focus:ring-green-500 focus:outline-none"
                        />
                    </div>

                    <div>
                        <label className="mb-2 block text-sm font-medium text-neutral-400">
                            Media (optional)
                        </label>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*,video/*,audio/*,.webp,.pdf,.doc,.docx"
                            className="hidden"
                            onChange={(e) =>
                                e.target.files?.[0] && handleFileSelect(e.target.files[0])
                            }
                        />
                        {file ? (
                            <div className="rounded-lg border border-neutral-700 bg-neutral-800 p-3">
                                {preview && (
                                    <div className="relative mb-2 h-40 w-full">
                                        <Image
                                            src={preview}
                                            alt="Preview"
                                            fill
                                            className="rounded object-contain"
                                            unoptimized
                                        />
                                    </div>
                                )}
                                <div className="flex items-center justify-between">
                                    <div className="flex min-w-0 items-center gap-2">
                                        <span className="shrink-0 rounded bg-green-500/20 px-2 py-0.5 text-xs text-green-400 capitalize">
                                            {fileTypeLabel}
                                        </span>
                                        <span className="truncate text-sm text-neutral-300">
                                            {file.name}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => {
                                            setFile(null);
                                            setPreview(null);
                                        }}
                                        className="ml-2 shrink-0 text-neutral-400 hover:text-red-400"
                                    >
                                        <IconX className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className="w-full rounded-lg border-2 border-dashed border-neutral-700 bg-neutral-800/50 p-6 text-center transition-colors hover:border-green-500/50"
                            >
                                <IconUpload className="mx-auto mb-2 h-8 w-8 text-neutral-500" />
                                <p className="text-sm text-neutral-400">
                                    Click to upload image, sticker, video, or audio
                                </p>
                                <p className="mt-1 text-xs text-neutral-600">
                                    Supports: jpg, png, webp, mp4, mp3, pdf
                                </p>
                            </button>
                        )}
                    </div>
                </div>

                <div className="mt-6 flex gap-3">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        className="flex-1 border-neutral-700 text-neutral-400"
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={!name.trim() || (!content.trim() && !file)}
                        className="flex-1 bg-green-600 hover:bg-green-500"
                    >
                        <IconDeviceFloppy className="mr-2 h-4 w-4" />
                        {editingNote ? "Update" : "Save"}
                    </Button>
                </div>
            </motion.div>
        </div>
    );
}

export default function NotesPage() {
    const [groups, setGroups] = useState<Group[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [notes, setNotes] = useState<Note[]>([]);
    const [loading, setLoading] = useState(true);
    const [notesLoading, setNotesLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editingNote, setEditingNote] = useState<Note | null>(null);
    const toast = useToast();

    useEffect(() => {
        async function fetchGroups() {
            try {
                setLoading(true);
                const data = await api.getGroups();
                setGroups(data.groups);
                setError(null);
            } catch (err) {
                setError("Failed to load groups. Is the API server running?");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchGroups();
    }, []);

    const loadNotes = async (group: Group) => {
        setSelectedGroup(group);
        setNotesLoading(true);
        try {
            const data = await api.getNotes(group.id);
            setNotes(data.notes);
        } catch (err) {
            toast.error("Failed to load notes");
            console.error(err);
        } finally {
            setNotesLoading(false);
        }
    };

    const handleSaveNote = async (name: string, content: string, file: File | null) => {
        if (!selectedGroup) return;

        try {
            if (editingNote) {
                await api.updateNote(selectedGroup.id, name, content);
                if (file) {
                    const result = await api.uploadNoteMedia(selectedGroup.id, name, file);
                    setNotes((prev) =>
                        prev.map((n) =>
                            n.name === name
                                ? {
                                      ...n,
                                      content,
                                      media_type: result.media_type as any,
                                      media_path: result.media_path,
                                  }
                                : n,
                        ),
                    );
                } else {
                    setNotes((prev) => prev.map((n) => (n.name === name ? { ...n, content } : n)));
                }
                toast.success("Note updated", `#${name} has been updated`);
            } else {
                let mediaType = "text";
                if (file) {
                    if (file.type.startsWith("image/")) mediaType = "image";
                    else if (file.type.startsWith("video/")) mediaType = "video";
                    else if (file.type.startsWith("audio/")) mediaType = "audio";
                    else if (file.name.endsWith(".webp")) mediaType = "sticker";
                    else if (file.type === "application/pdf") mediaType = "document";
                }

                await api.createNote(selectedGroup.id, name, content, mediaType);

                let mediaPath: string | null = null;
                if (file) {
                    const result = await api.uploadNoteMedia(selectedGroup.id, name, file);
                    mediaType = result.media_type;
                    mediaPath = result.media_path;
                }

                setNotes((prev) => [
                    ...prev,
                    {
                        name,
                        content,
                        media_type: mediaType as any,
                        media_path: mediaPath,
                    },
                ]);
                toast.success("Note created", `#${name} is now available`);
            }
            setEditingNote(null);
        } catch (err: any) {
            toast.error("Failed to save note", err.message);
        }
    };

    const handleDeleteNote = async (noteName: string) => {
        if (!selectedGroup) return;

        try {
            await api.deleteNote(selectedGroup.id, noteName);
            setNotes((prev) => prev.filter((n) => n.name !== noteName));
            toast.success("Note deleted", `#${noteName} has been removed`);
        } catch (err: any) {
            toast.error("Failed to delete note", err.message);
        }
    };

    const filteredNotes = notes.filter(
        (note) =>
            note.name.toLowerCase().includes(search.toLowerCase()) ||
            note.content.toLowerCase().includes(search.toLowerCase()),
    );

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Notes Manager</h1>
                    <p className="mt-1 text-neutral-400">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card
                            key={i}
                            className="animate-pulse border-neutral-700 bg-neutral-800/50"
                        >
                            <CardContent className="p-6">
                                <div className="mb-2 h-6 w-3/4 rounded bg-neutral-700"></div>
                                <div className="h-4 w-1/2 rounded bg-neutral-700"></div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Notes Manager</h1>
                    <p className="mt-1 text-neutral-400">Manage saved notes for each group</p>
                </div>
                <Card className="border-red-500/20 bg-red-500/10">
                    <CardContent className="flex items-center gap-3 p-6">
                        <IconAlertCircle className="h-5 w-5 text-red-400" />
                        <p className="text-red-400">{error}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Notes Manager</h1>
                    <p className="mt-1 text-neutral-400">
                        {selectedGroup
                            ? `Managing notes for ${selectedGroup.name}`
                            : "Select a group to manage notes"}
                    </p>
                </div>
                {selectedGroup && (
                    <Button
                        onClick={() => {
                            setEditingNote(null);
                            setModalOpen(true);
                        }}
                        className="bg-green-600 hover:bg-green-500"
                    >
                        <IconPlus className="mr-2 h-4 w-4" />
                        Add Note
                    </Button>
                )}
            </div>

            {!selectedGroup ? (
                /* Group Selection */
                <div className="space-y-4">
                    <p className="text-sm text-neutral-500">Select a group to manage its notes:</p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                className="cursor-pointer border-neutral-700 bg-neutral-800/50 transition-colors hover:border-green-500/50"
                                onClick={() => loadNotes(group)}
                            >
                                <CardContent className="flex items-center gap-4 p-4">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-500/20 to-blue-500/20">
                                        <IconUsers className="h-5 w-5 text-green-400" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <h3 className="truncate font-medium text-white">
                                            {group.name}
                                        </h3>
                                        <p className="text-sm text-neutral-500">
                                            {group.memberCount} members
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            ) : (
                /* Notes List */
                <div className="space-y-4">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="outline"
                            onClick={() => setSelectedGroup(null)}
                            className="border-neutral-700 text-neutral-400"
                        >
                            ← Back to Groups
                        </Button>
                        <div className="relative max-w-md flex-1">
                            <IconSearch className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                            <Input
                                placeholder="Search notes..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="border-neutral-700 bg-neutral-800 pl-10 text-white"
                            />
                        </div>
                    </div>

                    {notesLoading ? (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {[1, 2, 3].map((i) => (
                                <Card
                                    key={i}
                                    className="animate-pulse border-neutral-700 bg-neutral-800/50"
                                >
                                    <CardContent className="p-6">
                                        <div className="mb-3 h-6 w-1/2 rounded bg-neutral-700"></div>
                                        <div className="h-16 rounded bg-neutral-700"></div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : filteredNotes.length === 0 ? (
                        <Card className="border-neutral-700 bg-neutral-800/50">
                            <CardContent className="p-12 text-center">
                                <IconNote className="mx-auto mb-4 h-12 w-12 text-neutral-600" />
                                <h3 className="mb-2 text-lg font-medium text-neutral-400">
                                    {search ? "No notes found" : "No notes yet"}
                                </h3>
                                <p className="mb-4 text-sm text-neutral-500">
                                    {search
                                        ? "Try a different search term"
                                        : "Create your first note for this group"}
                                </p>
                                {!search && (
                                    <Button
                                        onClick={() => {
                                            setEditingNote(null);
                                            setModalOpen(true);
                                        }}
                                        className="bg-green-600 hover:bg-green-500"
                                    >
                                        <IconPlus className="mr-2 h-4 w-4" />
                                        Create Note
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            <AnimatePresence>
                                {filteredNotes.map((note) => (
                                    <motion.div
                                        key={note.name}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -20 }}
                                    >
                                        <Card className="group border-neutral-700 bg-neutral-800/50 transition-colors hover:border-neutral-600">
                                            <CardHeader className="pb-2">
                                                <div className="flex items-center justify-between">
                                                    <CardTitle className="flex items-center gap-2 text-lg text-white">
                                                        <IconNote className="h-4 w-4 text-green-400" />
                                                        #{note.name}
                                                    </CardTitle>
                                                    <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                                                        <button
                                                            onClick={() => {
                                                                setEditingNote(note);
                                                                setModalOpen(true);
                                                            }}
                                                            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-700 hover:text-white"
                                                        >
                                                            <IconEdit className="h-4 w-4" />
                                                        </button>
                                                        <button
                                                            onClick={() =>
                                                                handleDeleteNote(note.name)
                                                            }
                                                            className="rounded-lg p-1.5 text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
                                                        >
                                                            <IconTrash className="h-4 w-4" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="mb-2 flex items-center gap-1.5">
                                                    {note.media_type === "image" && (
                                                        <IconPhoto className="h-3.5 w-3.5 text-blue-400" />
                                                    )}
                                                    {note.media_type === "video" && (
                                                        <IconVideo className="h-3.5 w-3.5 text-purple-400" />
                                                    )}
                                                    {note.media_type === "audio" && (
                                                        <IconVolume className="h-3.5 w-3.5 text-yellow-400" />
                                                    )}
                                                    {note.media_type === "document" && (
                                                        <IconFile className="h-3.5 w-3.5 text-orange-400" />
                                                    )}
                                                    {note.media_type === "text" && (
                                                        <IconFileText className="h-3.5 w-3.5 text-neutral-500" />
                                                    )}
                                                    <span className="text-xs text-neutral-500 capitalize">
                                                        {note.media_type}
                                                    </span>
                                                </div>
                                                <p className="line-clamp-3 text-sm whitespace-pre-wrap text-neutral-400">
                                                    {note.content}
                                                </p>
                                            </CardContent>
                                        </Card>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}
                </div>
            )}

            <NoteModal
                key={editingNote?.name || "new"}
                isOpen={modalOpen}
                onClose={() => {
                    setModalOpen(false);
                    setEditingNote(null);
                }}
                onSave={handleSaveNote}
                editingNote={editingNote}
            />
        </div>
    );
}
