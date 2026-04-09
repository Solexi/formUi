import { useEffect, useState } from "react";
import DocumentsPanel from "./DocumentsPanel";
import { formatDateTime, truncate } from "../lib/formatting";
import { supabase } from "../lib/supabase";

function ProjectCard({ project }) {
  const [open, setOpen] = useState(false);

  return (
    <article className="panel p-4">
      <button
        type="button"
        className="flex w-full items-center justify-between text-left"
        onClick={() => setOpen((prev) => !prev)}
      >
        <div>
          <h3 className="font-display text-lg font-semibold text-brand-900">
            {project.company_name} - {project.project_name}
          </h3>
          <p className="text-sm text-[var(--muted)]">Project ID: {project.project_id}</p>
        </div>
        <span className="text-sm font-semibold text-brand-800">{open ? "Hide" : "View"}</span>
      </button>

      {open ? (
        <div className="mt-4 grid gap-4">
          <div className="grid gap-3 rounded-lg border border-[#e5d5bf] bg-white p-4 text-sm text-[var(--ink)] md:grid-cols-2">
            <p>Contact: {project.key_contact || "N/A"}</p>
            <p>Created: {project.created_at ? formatDateTime(project.created_at) : "N/A"}</p>
            <p>Meeting Type: {project.meeting_type || "N/A"}</p>
            <p>Meeting ID: {project.meeting_id || "N/A"}</p>
            <p>HubSpot: {truncate(project.hubspot_url, 36)}</p>
            <p>
              Google Drive Folder:{" "}
              {project.folder_url ? (
                <a className="font-semibold underline" href={project.folder_url} target="_blank" rel="noreferrer">
                  Open Folder
                </a>
              ) : (
                "N/A"
              )}
            </p>
          </div>

          {project.project_token ? (
            <div className="rounded-lg border border-brand-200 bg-brand-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">Secure Link</p>
              <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                <input
                  className="input flex-1"
                  readOnly
                  value={`${import.meta.env.VITE_APP_BASE_URL || window.location.origin}?token=${project.project_token}`}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() =>
                    navigator.clipboard.writeText(
                      `${import.meta.env.VITE_APP_BASE_URL || window.location.origin}?token=${project.project_token}`,
                    )
                  }
                >
                  Copy
                </button>
              </div>
            </div>
          ) : null}

          <DocumentsPanel projectId={project.project_id} compact />
        </div>
      ) : null}
    </article>
  );
}

export default function AdminProjectsView() {
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const { data, error: loadError } = await supabase
        .from("projects")
        .select("*")
        .order("created_at", { ascending: false });

      if (loadError) {
        setError(loadError.message || "Failed to load projects.");
        setLoading(false);
        return;
      }

      setProjects(data || []);
      setLoading(false);
    };

    load();
  }, []);

  if (loading) {
    return <section className="panel p-6 text-sm text-[var(--muted)]">Loading project overview...</section>;
  }

  return (
    <section className="space-y-3">
      <div className="panel p-6">
        <h2 className="font-display text-2xl font-semibold text-brand-900">All Projects Overview</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Explore every project and manage attached context documents.</p>
        {error ? <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      </div>

      {!projects.length ? (
        <div className="panel p-5 text-sm text-[var(--muted)]">No projects found.</div>
      ) : (
        projects.map((project) => <ProjectCard key={project.project_id} project={project} />)
      )}
    </section>
  );
}
