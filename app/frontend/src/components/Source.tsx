import { useState, useEffect } from "react";
import { FileText, Calendar, ExternalLink, Loader2 } from "lucide-react";

interface SourceProps {
    objectId: string;
    collection: string;
}

interface SourceData {
    title?: string;
    date?: string;
    abstract?: string;
    pdf_url?: string;
    chunk_text?: string;
    pdf_title?: string;
    pdf_date?: string;
    [key: string]: any;
}

export default function Source({ objectId, collection }: SourceProps) {
    const [data, setData] = useState<SourceData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        const fetchSource = async () => {
            try {
                const response = await fetch("http://127.0.0.1:8000/api/sources", {
                    method: "POST", // Changed to POST because we're sending a body
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ object_id: objectId, collection: collection }),
                });

                if (!response.ok) throw new Error("Failed to fetch source");
                const result = await response.json();
                setData(result);
            } catch (err) {
                console.error(err);
                setError(true);
            } finally {
                setLoading(false);
            }
        };

        fetchSource();
    }, [objectId, collection]);

    if (loading) {
        return (
            <div className="min-w-[280px] h-32 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-center">
                <Loader2 className="w-5 h-5 text-slate-300 animate-spin" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="min-w-[280px] p-4 bg-red-50 rounded-xl border border-red-100 text-red-400 text-sm">
                Failed to load source
            </div>
        );
    }

    // Determine display values based on whether it's a chunk or a full PDF
    const isChunk = collection === "PDFchunks1";
    const title = isChunk ? data.pdf_title : data.title;
    const date = isChunk ? data.pdf_date : data.date;
    const content = isChunk ? data.chunk_text : data.abstract;
    const url = data.pdf_url;

    return (
        <div className="min-w-[280px] max-w-[320px] p-4 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col gap-2 snap-start">
            <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 text-indigo-600">
                    <FileText className="w-4 h-4" />
                    <span className="text-xs font-semibold uppercase tracking-wider">
                        {isChunk ? "Excerpt" : "Document"}
                    </span>
                </div>
                {date && (
                    <div className="flex items-center gap-1 text-slate-400 text-xs">
                        <Calendar className="w-3 h-3" />
                        <span>{date}</span>
                    </div>
                )}
            </div>

            <h3 className="font-medium text-slate-900 text-sm line-clamp-2 leading-snug" title={title}>
                {title || "Untitled Document"}
            </h3>

            <p className="text-xs text-slate-500 line-clamp-3 leading-relaxed">
                {content}
            </p>

            {url && (
                <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-auto pt-2 flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                >
                    View PDF <ExternalLink className="w-3 h-3" />
                </a>
            )}
        </div>
    );
}
