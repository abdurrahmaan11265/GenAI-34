"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Upload, FileText, X, Globe, Lock, Loader2, AlertCircle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/Sidebar";
import { getToken } from "@/lib/auth";
import { createBook, uploadBookFile } from "@/lib/api";
import { ApiError } from "@/lib/api-client";

const MAX_SIZE_MB = 50;
const ALLOWED_EXT = [".pdf", ".epub", ".txt"];

export default function UploadPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [file, setFile]         = useState<File | null>(null);
  const [title, setTitle]       = useState("");
  const [author, setAuthor]     = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError]       = useState("");
  const [uploadPct, setUploadPct] = useState(0);

  const handleFile = (f: File) => {
    const ext = f.name.substring(f.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXT.includes(ext)) {
      setError("Unsupported format. Please upload PDF, EPUB, or TXT.");
      return;
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File too large (max ${MAX_SIZE_MB} MB).`);
      return;
    }
    setError("");
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.(pdf|epub|txt)$/i, ""));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) { setError("Please add a title."); return; }
    if (!file) { setError("Please select a file."); return; }

    const token = getToken(session);
    setUploading(true);
    setError("");

    try {
      // Step 1: create the book record
      const { book } = await createBook(token, {
        title: title.trim(),
        author: author.trim() || undefined,
        isPublic,
      });

      // Step 2: upload the file — backend will kick off async processing
      setUploadPct(30);
      await uploadBookFile(token, book.id, file);
      setUploadPct(100);

      // Redirect to processing status page
      router.push(`/book/${book.id}/processing`);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as { detail?: string; error?: string } | undefined;
        setError(body?.detail ?? body?.error ?? `Upload failed (${err.status})`);
      } else {
        setError("Upload failed — is the backend running?");
      }
      setUploading(false);
      setUploadPct(0);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-2xl">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>

        <h1 className="text-2xl font-bold text-slate-900 mb-1">Add a book</h1>
        <p className="text-slate-500 mb-8">
          Upload a file and Lexis will extract a knowledge graph from it.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => document.getElementById("file-input")?.click()}
            className={`relative flex flex-col items-center justify-center gap-3 p-12 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${
              dragOver
                ? "border-indigo-400 bg-indigo-50"
                : file
                ? "border-emerald-300 bg-emerald-50"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <input
              id="file-input"
              type="file"
              accept=".pdf,.epub,.txt"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />

            {file ? (
              <>
                <FileText className="h-10 w-10 text-emerald-500" />
                <div className="text-center">
                  <p className="font-medium text-slate-900">{file.name}</p>
                  <p className="text-sm text-slate-500">
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="absolute top-3 right-3 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </>
            ) : (
              <>
                <Upload className="h-10 w-10 text-slate-400" />
                <div className="text-center">
                  <p className="font-medium text-slate-700">Drop your book here</p>
                  <p className="text-sm text-slate-400">
                    or click to browse — PDF, EPUB, TXT · max {MAX_SIZE_MB} MB
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Upload progress */}
          {uploading && uploadPct > 0 && (
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div
                className="bg-indigo-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${uploadPct}%` }}
              />
            </div>
          )}

          {/* Metadata */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Title *
              </label>
              <input
                id="input-title"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Book title"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Author <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <input
                id="input-author"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="Author name"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Visibility */}
          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-medium text-slate-700 mb-3">Graph visibility</p>
              <div className="space-y-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    checked={!isPublic}
                    onChange={() => setIsPublic(false)}
                    className="text-indigo-600"
                  />
                  <Lock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-sm font-medium text-slate-900">Private to me</p>
                    <p className="text-xs text-slate-500">Only you can use this knowledge graph.</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    checked={isPublic}
                    onChange={() => setIsPublic(true)}
                    className="text-indigo-600"
                  />
                  <Globe className="h-4 w-4 text-indigo-400" />
                  <div>
                    <p className="text-sm font-medium text-slate-900">Contribute to shared library</p>
                    <p className="text-xs text-slate-500">
                      For public-domain books. Others can use your verified graph.
                    </p>
                  </div>
                </label>
              </div>
            </CardContent>
          </Card>

          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">
              <AlertCircle className="h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          <Button
            id="btn-upload-submit"
            type="submit"
            className="w-full"
            size="lg"
            disabled={uploading || !file}
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Uploading...
              </>
            ) : (
              "Upload & build knowledge graph"
            )}
          </Button>
        </form>
      </main>
    </div>
  );
}
