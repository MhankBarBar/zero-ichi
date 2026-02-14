"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    IconNote,
    IconPlus,
    IconTrash,
    IconEdit,
    IconSearch,
    IconUsers,
    IconAlertCircle,
    IconX,
    IconDeviceFloppy
} from "@tabler/icons-react";
import { api, type Group, type Note } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { motion, AnimatePresence } from "framer-motion";

interface NoteModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (name: string, content: string) => void;
    editingNote?: Note | null;
}

function NoteModal({ isOpen, onClose, onSave, editingNote }: NoteModalProps) {
    const [name, setName] = useState("");
    const [content, setContent] = useState("");

    useEffect(() => {
        if (editingNote) {
            setName(editingNote.name);
            setContent(editingNote.content);
        } else {
            setName("");
            setContent("");
        }
    }, [editingNote, isOpen]);

    const handleSave = () => {
        if (!name.trim() || !content.trim()) return;
        onSave(name.trim(), content);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-neutral-900 border border-neutral-700 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl"
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">
                        {editingNote ? "Edit Note" : "Create Note"}
                    </h2>
                    <button onClick={onClose} className="text-neutral-400 hover:text-white">
                        <IconX className="h-5 w-5" />
                    </button>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-neutral-400 mb-2">
                            Note Name
                        </label>
                        <Input
                            placeholder="e.g. rules, welcome, faq"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            disabled={!!editingNote}
                            className="bg-neutral-800 border-neutral-700 text-white"
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                            Users can retrieve this note using #{name || "notename"}
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-neutral-400 mb-2">
                            Content
                        </label>
                        <textarea
                            placeholder="Enter note content..."
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={6}
                            className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
                        />
                    </div>
                </div>

                <div className="flex gap-3 mt-6">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        className="flex-1 border-neutral-700 text-neutral-400"
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={!name.trim() || !content.trim()}
                        className="flex-1 bg-green-600 hover:bg-green-500"
                    >
                        <IconDeviceFloppy className="h-4 w-4 mr-2" />
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

    const handleSaveNote = async (name: string, content: string) => {
        if (!selectedGroup) return;

        try {
            if (editingNote) {
                await api.updateNote(selectedGroup.id, name, content);
                setNotes(prev => prev.map(n =>
                    n.name === name ? { ...n, content } : n
                ));
                toast.success("Note updated", `#${name} has been updated`);
            } else {
                await api.createNote(selectedGroup.id, name, content);
                setNotes(prev => [...prev, { name, content, media_type: "text" }]);
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
            setNotes(prev => prev.filter(n => n.name !== noteName));
            toast.success("Note deleted", `#${noteName} has been removed`);
        } catch (err: any) {
            toast.error("Failed to delete note", err.message);
        }
    };

    const filteredNotes = notes.filter(note =>
        note.name.toLowerCase().includes(search.toLowerCase()) ||
        note.content.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Notes Manager</h1>
                    <p className="text-neutral-400 mt-1">Loading groups...</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="bg-neutral-800/50 border-neutral-700 animate-pulse">
                            <CardContent className="p-6">
                                <div className="h-6 bg-neutral-700 rounded w-3/4 mb-2"></div>
                                <div className="h-4 bg-neutral-700 rounded w-1/2"></div>
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
                    <p className="text-neutral-400 mt-1">Manage saved notes for each group</p>
                </div>
                <Card className="bg-red-500/10 border-red-500/20">
                    <CardContent className="p-6 flex items-center gap-3">
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
                    <p className="text-neutral-400 mt-1">
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
                        <IconPlus className="h-4 w-4 mr-2" />
                        Add Note
                    </Button>
                )}
            </div>

            {!selectedGroup ? (
                /* Group Selection */
                <div className="space-y-4">
                    <p className="text-neutral-500 text-sm">Select a group to manage its notes:</p>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {groups.map((group) => (
                            <Card
                                key={group.id}
                                className="bg-neutral-800/50 border-neutral-700 cursor-pointer hover:border-green-500/50 transition-colors"
                                onClick={() => loadNotes(group)}
                            >
                                <CardContent className="p-4 flex items-center gap-4">
                                    <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-green-500/20 to-blue-500/20 flex items-center justify-center">
                                        <IconUsers className="h-5 w-5 text-green-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-white font-medium truncate">{group.name}</h3>
                                        <p className="text-neutral-500 text-sm">{group.memberCount} members</p>
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
                        <div className="relative flex-1 max-w-md">
                            <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                            <Input
                                placeholder="Search notes..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-10 bg-neutral-800 border-neutral-700 text-white"
                            />
                        </div>
                    </div>

                    {notesLoading ? (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {[1, 2, 3].map((i) => (
                                <Card key={i} className="bg-neutral-800/50 border-neutral-700 animate-pulse">
                                    <CardContent className="p-6">
                                        <div className="h-6 bg-neutral-700 rounded w-1/2 mb-3"></div>
                                        <div className="h-16 bg-neutral-700 rounded"></div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : filteredNotes.length === 0 ? (
                        <Card className="bg-neutral-800/50 border-neutral-700">
                            <CardContent className="p-12 text-center">
                                <IconNote className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-neutral-400 mb-2">
                                    {search ? "No notes found" : "No notes yet"}
                                </h3>
                                <p className="text-neutral-500 text-sm mb-4">
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
                                        <IconPlus className="h-4 w-4 mr-2" />
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
                                        <Card className="bg-neutral-800/50 border-neutral-700 hover:border-neutral-600 transition-colors group">
                                            <CardHeader className="pb-2">
                                                <div className="flex items-center justify-between">
                                                    <CardTitle className="text-lg text-white flex items-center gap-2">
                                                        <IconNote className="h-4 w-4 text-green-400" />
                                                        #{note.name}
                                                    </CardTitle>
                                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button
                                                            onClick={() => {
                                                                setEditingNote(note);
                                                                setModalOpen(true);
                                                            }}
                                                            className="p-1.5 rounded-lg hover:bg-neutral-700 text-neutral-400 hover:text-white"
                                                        >
                                                            <IconEdit className="h-4 w-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteNote(note.name)}
                                                            className="p-1.5 rounded-lg hover:bg-red-500/20 text-neutral-400 hover:text-red-400"
                                                        >
                                                            <IconTrash className="h-4 w-4" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </CardHeader>
                                            <CardContent>
                                                <p className="text-neutral-400 text-sm line-clamp-3 whitespace-pre-wrap">
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
