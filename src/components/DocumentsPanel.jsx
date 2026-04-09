import { useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

const uploadFields = [
  { key: "questions", label: "Questions Document", accept: ".txt,.md,.pdf", multiple: false },
  { key: "dictionary", label: "Dictionary", accept: ".json,.txt", multiple: false },
  {
    key: "company_research",
    label: "Company Research",
    accept: ".pdf,.txt,.md",
    multiple: false,
  },
  {
    key: "other_documents",
    label: "Other Documents",
    accept: ".pdf,.txt,.md,.json",
    multiple: true,
  },
];

async function saveMetadata(projectId, docType, fileName, fileUrl) {
  const base = {
    project_id: String(projectId),
    doc_type: docType,
    file_name: fileName,
    file_url: fileUrl,
  };

  const candidates = [base];
  const userId = null;

  if (userId) {
    candidates.push(
      { ...base, uploaded_by: userId },
      { ...base, created_by: userId },
      { ...base, user_id: userId },
      { ...base, reviewer_user_id: userId },
    );
  }

  let finalError = null;
  for (const candidate of candidates) {
    const { error } = await supabase.from("analysis_documents").insert(candidate);
    if (!error) {
      return;
    }

    finalError = error;
    const lower = (error.message || "").toLowerCase();
    if (lower.includes("column") && lower.includes("does not exist")) {
      continue;
    }
    if (lower.includes("row-level security") || lower.includes("violates row-level security policy")) {
      continue;
    }
    break;
  }

  if (finalError) {
    throw finalError;
  }
}

export default function DocumentsPanel({ projectId, compact = false }) {
  const [documents, setDocuments] = useState([]);
  const [filesByType, setFilesByType] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const groupKey = useMemo(() => `docs-${projectId}`, [projectId]);

  const loadDocuments = async () => {
    const { data, error } = await supabase
      .from("analysis_documents")
      .select("id, doc_type, file_name, file_url")
      .eq("project_id", String(projectId));

    if (error) {
      setMessage({ type: "error", text: error.message });
      return;
    }

    setDocuments(data || []);
  };

  useEffect(() => {
    loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const onFileChange = (event, key, multiple) => {
    const selectedFiles = event.target.files ? Array.from(event.target.files) : [];
    setFilesByType((prev) => ({
      ...prev,
      [key]: multiple ? selectedFiles : selectedFiles[0] || null,
    }));
  };

  const uploadOne = async (docType, file) => {
    const safeName = file.name.replace(/\s+/g, "_");
    const path = `projects/${projectId}/${docType}/${safeName}`;

    const { error: uploadError } = await supabase.storage.from("documents").upload(path, file, {
      upsert: true,
    });

    if (uploadError) {
      throw uploadError;
    }

    const { data } = supabase.storage.from("documents").getPublicUrl(path);
    await saveMetadata(projectId, docType, safeName, data.publicUrl);
  };

  const onSave = async () => {
    setMessage(null);
    const tasks = [];

    for (const field of uploadFields) {
      const value = filesByType[field.key];
      if (!value) {
        continue;
      }
      if (field.multiple) {
        for (const file of value) {
          tasks.push({ type: field.key, file });
        }
      } else {
        tasks.push({ type: field.key, file: value });
      }
    }

    if (!tasks.length) {
      setMessage({ type: "info", text: "No files selected." });
      return;
    }

    setIsSaving(true);

    try {
      for (const task of tasks) {
        await uploadOne(task.type, task.file);
      }
      setMessage({ type: "success", text: "Documents uploaded successfully." });
      setFilesByType({});
      await loadDocuments();
    } catch (error) {
      setMessage({ type: "error", text: error.message || "Failed to upload documents." });
    } finally {
      setIsSaving(false);
    }
  };

  const onDelete = async (id) => {
    const { error } = await supabase.from("analysis_documents").delete().eq("id", id);
    if (error) {
      setMessage({ type: "error", text: error.message });
      return;
    }
    await loadDocuments();
  };

  return (
    <section className={`panel ${compact ? "p-4" : "p-5"}`}>
      <h3 className="font-display text-lg font-semibold text-brand-900">Upload Additional Context</h3>
      <p className="mt-1 text-sm text-[var(--muted)]">Attach optional files to improve analysis quality.</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {uploadFields.map((field) => (
          <label key={`${groupKey}-${field.key}`}>
            <span className="label">{field.label}</span>
            <input
              className="input"
              type="file"
              accept={field.accept}
              multiple={field.multiple}
              onChange={(event) => onFileChange(event, field.key, field.multiple)}
            />
          </label>
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <button type="button" className="btn-primary" onClick={onSave} disabled={isSaving}>
          {isSaving ? "Uploading..." : "Save Documents"}
        </button>
      </div>

      {message ? (
        <p
          className={`mt-3 rounded-lg p-3 text-sm ${
            message.type === "success"
              ? "bg-emerald-50 text-emerald-800"
              : message.type === "error"
                ? "bg-red-50 text-red-700"
                : "bg-amber-50 text-amber-800"
          }`}
        >
          {message.text}
        </p>
      ) : null}

      <div className="mt-5 border-t border-[var(--line)] pt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Uploaded Documents</p>
        {!documents.length ? <p className="mt-2 text-sm text-[var(--muted)]">No documents uploaded yet.</p> : null}

        <div className="mt-2 space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex flex-col gap-2 rounded-lg border border-[#e6d4be] bg-white p-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <a className="text-sm font-medium text-brand-700 hover:underline" href={doc.file_url} target="_blank" rel="noreferrer">
                {(doc.doc_type || "document").replaceAll("_", " ")}: {doc.file_name}
              </a>
              <button type="button" className="btn-secondary" onClick={() => onDelete(doc.id)}>
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
