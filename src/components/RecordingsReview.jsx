import { useEffect, useMemo, useState } from "react";
import DocumentsPanel from "./DocumentsPanel";
import { formatDateTime, truncate } from "../lib/formatting";
import { fetchMeetingDetails } from "../lib/testMeetings";
import { supabase } from "../lib/supabase";

function RecordingCard({ record, selectedProjectId, refresh }) {
  const [overrideMeetingId, setOverrideMeetingId] = useState("");
  const [loadedMeeting, setLoadedMeeting] = useState(null);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const onApprove = async () => {
    setBusyAction("approve");
    setError("");

    try {
      const { error: updateError } = await supabase
        .from("zoom_meetings")
        .update({
          processed: true,
          processed_at: new Date().toISOString(),
          status: "approved",
        })
        .eq("zoom_record_id", record.zoom_record_id);

      if (updateError) {
        throw updateError;
      }

      const wf3Webhook = import.meta.env.VITE_N8N_WF3_WEBHOOK_URL;
      if (wf3Webhook) {
        await fetch(wf3Webhook, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: selectedProjectId,
            meeting_id: record.meeting_id,
            zoom_record_id: record.zoom_record_id,
            status: "approved",
            trigger_source: "react_approval",
          }),
        });
      }

      refresh();
    } catch (approveError) {
      setError(approveError.message || "Could not approve this recording.");
    } finally {
      setBusyAction("");
    }
  };

  const onLoadMeeting = () => {
    if (!overrideMeetingId.trim()) {
      setError("Enter a Meeting ID before loading details.");
      return;
    }

    const details = fetchMeetingDetails(overrideMeetingId.trim());
    if (!details) {
      setLoadedMeeting(null);
      setError("Meeting not found in test source.");
      return;
    }

    setError("");
    setLoadedMeeting(details);
  };

  const onConfirmOverride = async () => {
    if (!overrideMeetingId || !loadedMeeting) {
      return;
    }

    setBusyAction("override");
    setError("");

    try {
      const { error: updateError } = await supabase
        .from("zoom_meetings")
        .update({
          override_meeting_id: overrideMeetingId,
          status: "override_requested",
          processed: true,
          processed_at: new Date().toISOString(),
        })
        .eq("zoom_record_id", record.zoom_record_id);

      if (updateError) {
        throw updateError;
      }

      const wf3Webhook = import.meta.env.VITE_N8N_WF3_WEBHOOK_URL;
      if (wf3Webhook) {
        await fetch(wf3Webhook, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: selectedProjectId,
            meeting_id: overrideMeetingId,
            zoom_record_id: record.zoom_record_id,
            original_meeting_id: record.meeting_id,
            status: "override_approved",
            trigger_source: "react_override",
          }),
        });
      }

      refresh();
    } catch (overrideError) {
      setError(overrideError.message || "Could not submit override.");
    } finally {
      setBusyAction("");
    }
  };

  return (
    <article className="rounded-xl border border-[#e9d9c7] bg-white p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h4 className="font-display text-lg font-semibold text-brand-900">{record.meeting_topic || "Untitled Meeting"}</h4>
          <div className="mt-2 grid gap-1 text-sm text-[var(--muted)]">
            <p>Meeting ID: {record.meeting_id}</p>
            <p>Date: {record.meeting_date ? formatDateTime(record.meeting_date) : "N/A"}</p>
            <p>Duration: {record.duration && record.duration !== "N/A" ? `${record.duration} min` : "N/A"}</p>
            <p>Host: {truncate(record.host_id, 20)}</p>
          </div>
        </div>

        <span className="w-fit rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
          Pending Review
        </span>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[auto_1fr_auto]">
        <button type="button" className="btn-primary" onClick={onApprove} disabled={busyAction.length > 0}>
          {busyAction === "approve" ? "Approving..." : "Accept Recording"}
        </button>

        <input
          className="input"
          placeholder="Enter different Meeting ID"
          value={overrideMeetingId}
          onChange={(event) => setOverrideMeetingId(event.target.value)}
        />

        <button type="button" className="btn-secondary" onClick={onLoadMeeting} disabled={busyAction.length > 0}>
          Load Meeting
        </button>
      </div>

      {loadedMeeting ? (
        <div className="mt-4 rounded-lg border border-brand-200 bg-brand-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">Meeting Preview</p>
          <div className="mt-2 grid gap-2 text-sm text-brand-900 md:grid-cols-2">
            <p>Topic: {loadedMeeting.topic}</p>
            <p>Meeting ID: {loadedMeeting.id}</p>
            <p>Host: {loadedMeeting.host_email}</p>
            <p>Scheduled: {formatDateTime(loadedMeeting.start_time)}</p>
            <p>Duration: {loadedMeeting.duration} minutes</p>
            <p>Recordings: {loadedMeeting.recording_files?.length || 0}</p>
          </div>

          {loadedMeeting.recording_files?.length ? (
            <ul className="mt-3 space-y-1 text-sm text-brand-800">
              {loadedMeeting.recording_files.map((file) => (
                <li key={file.id}>
                  {file.file_type} ({String(file.file_extension || "").toUpperCase()}) - {file.status}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-amber-800">No recording files available for this meeting.</p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={onConfirmOverride}
              disabled={busyAction.length > 0}
            >
              {busyAction === "override" ? "Submitting..." : "Use This Meeting ID"}
            </button>
            <button type="button" className="btn-secondary" onClick={() => setLoadedMeeting(null)}>
              Try Different Meeting ID
            </button>
          </div>
        </div>
      ) : null}

      {error ? <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
    </article>
  );
}

export default function RecordingsReview({ projectToken = null }) {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [recordings, setRecordings] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) || null,
    [projects, selectedProjectId],
  );

  const loadProjects = async () => {
    if (projectToken) {
      const { data, error: projectError } = await supabase
        .from("projects")
        .select("project_id, project_name, company_name, folder_url, project_token")
        .eq("project_token", projectToken)
        .single();

      if (projectError) {
        throw new Error("Invalid or expired access token.");
      }

      setProjects([data]);
      setSelectedProjectId(data.project_id);
      return;
    }

    const { data, error: listError } = await supabase
      .from("projects")
      .select("project_id, project_name, company_name, folder_url, project_token")
      .order("created_at", { ascending: false });

    if (listError) {
      throw listError;
    }

    setProjects(data || []);
    if (data?.length) {
      setSelectedProjectId(data[0].project_id);
    }
  };

  const loadRecordings = async (projectId) => {
    if (!projectId) {
      setRecordings([]);
      return;
    }

    const { data, error: recordingsError } = await supabase
      .from("zoom_meetings")
      .select("*")
      .eq("project_id", projectId)
      .eq("processed", false)
      .order("meeting_date", { ascending: false });

    if (recordingsError) {
      throw recordingsError;
    }

    setRecordings(data || []);
  };

  useEffect(() => {
    const bootstrap = async () => {
      setLoading(true);
      setError("");

      try {
        await loadProjects();
      } catch (bootstrapError) {
        setError(bootstrapError.message || "Failed to load project list.");
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectToken]);

  useEffect(() => {
    if (!selectedProjectId) {
      return;
    }

    loadRecordings(selectedProjectId).catch((recordingsError) => {
      setError(recordingsError.message || "Failed to load recordings.");
    });
  }, [selectedProjectId]);

  const secureLink = selectedProject?.project_token
    ? `${import.meta.env.VITE_APP_BASE_URL || window.location.origin}?token=${selectedProject.project_token}`
    : null;

  if (loading) {
    return <section className="panel p-6 text-sm text-[var(--muted)]">Loading recordings...</section>;
  }

  return (
    <section className="space-y-4">
      <div className="panel p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="font-display text-2xl font-semibold text-brand-900">Review Zoom Recordings</h2>
            <p className="text-sm text-[var(--muted)]">Approve recordings or override meeting IDs before processing.</p>
          </div>

          {!projectToken ? (
            <label className="w-full max-w-md">
              <span className="label">Select Project</span>
              <select
                className="input"
                value={selectedProjectId || ""}
                onChange={(event) => setSelectedProjectId(Number(event.target.value))}
              >
                {projects.map((project) => (
                  <option key={project.project_id} value={project.project_id}>
                    {project.company_name} - {project.project_name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>

        {selectedProject?.folder_url ? (
          <p className="mt-3 text-sm text-brand-800">
            Google Drive Folder: {" "}
            <a className="font-semibold underline" href={selectedProject.folder_url} target="_blank" rel="noreferrer">
              Open Folder
            </a>
          </p>
        ) : null}

        {secureLink && !projectToken ? (
          <div className="mt-3 rounded-lg border border-brand-200 bg-brand-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">Share Secure Link with Client</p>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input className="input flex-1" readOnly value={secureLink} />
              <button type="button" className="btn-secondary" onClick={() => navigator.clipboard.writeText(secureLink)}>
                Copy
              </button>
            </div>
          </div>
        ) : null}

        {error ? <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      </div>

      <div className="space-y-3">
        {!recordings.length ? (
          <div className="panel p-5 text-sm text-[var(--muted)]">No pending recordings for this project.</div>
        ) : (
          recordings.map((record) => (
            <RecordingCard
              key={record.zoom_record_id}
              record={record}
              selectedProjectId={selectedProjectId}
              refresh={() => loadRecordings(selectedProjectId)}
            />
          ))
        )}
      </div>

      {selectedProjectId ? <DocumentsPanel projectId={selectedProjectId} /> : null}
    </section>
  );
}
