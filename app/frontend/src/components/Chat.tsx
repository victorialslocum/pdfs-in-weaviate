"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import Source from "./Source";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: { object_id: string; collection: string }[];
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
        };

        const newMessages = [...messages, userMessage];
        setMessages(newMessages);
        setInput("");
        setIsLoading(true);

        try {
            const response = await fetch("http://127.0.0.1:8000/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                // Send the entire conversation history including the new message
                // Map to backend expected format if needed (here it matches: role, content)
                body: JSON.stringify({
                    messages: newMessages.map(msg => ({
                        role: msg.role,
                        content: msg.content
                    }))
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to fetch response");
            }

            const data = await response.json();

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: data.response || "I received your message but got no answer.",
                sources: data.sources || [],
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Error:", error);
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: "Sorry, something went wrong. Please try again.",
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen max-w-4xl mx-auto relative">
            {/* Header */}
            <header className="sticky top-0 z-10 backdrop-blur-xl bg-white/70 border-b border-slate-200/50 p-4 flex items-center gap-3 shadow-sm">
                <div className="p-2.5 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl shadow-lg shadow-indigo-500/20">
                    <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-xl font-bold text-slate-900 tracking-tight">Weaviate QA Chat</h1>
                    <p className="text-xs text-slate-500 font-medium flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-indigo-500" />
                        Powered by AI
                    </p>
                </div>
            </header>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
                <AnimatePresence initial={false} mode="popLayout">
                    {messages.length === 0 && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4"
                        >
                            <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-2">
                                <Bot className="w-8 h-8 text-indigo-600" />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-800">How can I help you today?</h2>
                            <p className="text-slate-500 max-w-md">
                                Ask me anything about your documents. I can analyze PDFs and provide answers with sources.
                            </p>
                        </motion.div>
                    )}

                    {messages.map((message) => (
                        <motion.div
                            key={message.id}
                            initial={{ opacity: 0, y: 20, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            className={cn(
                                "flex gap-4",
                                message.role === "user" ? "flex-row-reverse" : "flex-row"
                            )}
                        >
                            <div
                                className={cn(
                                    "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm",
                                    message.role === "user"
                                        ? "bg-slate-200"
                                        : "bg-gradient-to-br from-indigo-600 to-violet-600"
                                )}
                            >
                                {message.role === "user" ? (
                                    <User className="w-5 h-5 text-slate-600" />
                                ) : (
                                    <Bot className="w-5 h-5 text-white" />
                                )}
                            </div>
                            <div
                                className={cn(
                                    "p-5 rounded-2xl max-w-[85%] shadow-sm",
                                    message.role === "user"
                                        ? "bg-gradient-to-br from-indigo-600 to-violet-600 text-white rounded-tr-sm shadow-indigo-500/20"
                                        : "bg-white text-slate-700 border border-slate-100 rounded-tl-sm"
                                )}
                            >
                                {message.sources && message.sources.length > 0 && (
                                    <div className="w-full overflow-x-auto pb-4 mb-2 border-b border-slate-100/50">
                                        <div className="flex gap-4 w-max px-1">
                                            {message.sources.map((source, idx) => (
                                                <Source
                                                    key={`${source.object_id}-${idx}`}
                                                    objectId={source.object_id}
                                                    collection={source.collection}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div className={cn(
                                    "prose prose-sm max-w-none leading-relaxed",
                                    message.role === "user" ? "prose-invert" : "prose-slate"
                                )}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {message.content}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {isLoading && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex gap-4"
                    >
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div className="bg-white p-5 rounded-2xl rounded-tl-sm border border-slate-100 shadow-sm flex items-center gap-3">
                            <div className="flex gap-1">
                                <motion.div
                                    animate={{ scale: [1, 1.2, 1] }}
                                    transition={{ repeat: Infinity, duration: 1, delay: 0 }}
                                    className="w-2 h-2 bg-indigo-400 rounded-full"
                                />
                                <motion.div
                                    animate={{ scale: [1, 1.2, 1] }}
                                    transition={{ repeat: Infinity, duration: 1, delay: 0.2 }}
                                    className="w-2 h-2 bg-indigo-400 rounded-full"
                                />
                                <motion.div
                                    animate={{ scale: [1, 1.2, 1] }}
                                    transition={{ repeat: Infinity, duration: 1, delay: 0.4 }}
                                    className="w-2 h-2 bg-indigo-400 rounded-full"
                                />
                            </div>
                            <span className="text-sm text-slate-500 font-medium">Thinking...</span>
                        </div>
                    </motion.div>
                )}
                <div ref={messagesEndRef} className="h-4" />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-gradient-to-t from-slate-50 via-slate-50/90 to-transparent">
                <form onSubmit={handleSubmit} className="relative max-w-4xl mx-auto">
                    <div className="relative group">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask a question about your documents..."
                            className="w-full p-4 pr-14 bg-white border-0 shadow-xl shadow-slate-200/50 rounded-2xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-105 active:scale-95 shadow-md shadow-indigo-500/20"
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Send className="w-5 h-5" />
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
