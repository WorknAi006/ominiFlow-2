"use client";

import { useState, useRef } from "react";

export function KnowledgeBaseTab() {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      // API call logic would go here
      console.log("Uploading", file.name);
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
        <h2 className="text-xl font-bold text-slate-900 mb-2">Knowledge Bases</h2>
        <p className="text-sm text-slate-500 mb-6">
          Manage your knowledge bases. Document ingestion and AI answer generation are not yet active in this phase.
        </p>
        
        <div className="bg-slate-50 border border-slate-200 text-slate-800 rounded-lg p-4 text-sm flex gap-3 mb-8">
          <div>
            <p className="font-bold mb-1">Notice</p>
            <p>This is a structural preview. File upload and processing infrastructure will be added in Phase 2.</p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-slate-800">Your Knowledge Bases</h3>
            <div className="flex gap-4">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".txt,.pdf,.doc,.docx,.csv,.md"
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg font-bold text-sm hover:bg-slate-50 transition-colors disabled:opacity-50"
              >
                {uploading ? "Uploading..." : "Upload Document"}
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg font-bold text-sm hover:bg-blue-700 transition-colors disabled:opacity-50">
                Create Knowledge Base
              </button>
            </div>
          </div>

          <div className="border border-slate-200 rounded-lg divide-y divide-slate-100 bg-white">
            <div className="p-8 text-center text-slate-500">
              No knowledge bases configured yet.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
