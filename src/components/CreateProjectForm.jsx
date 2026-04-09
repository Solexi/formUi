import { useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

function generateToken() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

const initialForm = {
  company_name: "",
  project_name: "",
  hubspot_url: "",
  notes: "",
  key_contact: "",
  meeting_type: "",
  meeting_id: "",
  meeting_number: "",
};

export default function CreateProjectForm() {
  const [form, setForm] = useState(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null);

  const baseUrl = useMemo(
    () => import.meta.env.VITE_APP_BASE_URL || window.location.origin,
    [],
  );

  const onChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!form.project_name || !form.company_name) {
      setError("Project Name and Company Name are required.");
      return;
    }

    setIsSubmitting(true);

    try {
      const projectToken = generateToken();
      const payload = {
        ...form,
        project_token: projectToken,
      };

      const { data, error: insertError } = await supabase
        .from("projects")
        .insert(payload)
        .select("project_id, project_name")
        .single();

      if (insertError) {
        throw insertError;
      }

      const secureLink = `${baseUrl}?token=${projectToken}`;

      if (import.meta.env.VITE_N8N_WEBHOOK_URL) {
        try {
          await fetch(import.meta.env.VITE_N8N_WEBHOOK_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...payload,
              project_id: data.project_id,
              trigger_source: "react_form",
            }),
          });
        } catch {
        }
      }

      setCreated({
        projectName: data.project_name,
        secureLink,
      });
      setForm(initialForm);
    } catch (submitError) {
      setError(submitError.message || "Failed to create project.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="panel p-6">
      <div className="mb-4">
        <h2 className="font-display text-2xl font-semibold text-brand-900">Create New Project</h2>
        <p className="text-sm text-[var(--muted)]">Create a project and generate a client review link.</p>
      </div>

      <form className="grid gap-4 lg:grid-cols-2" onSubmit={onSubmit}>
        <label>
          <span className="label">Client Company Name</span>
          <input className="input" name="company_name" value={form.company_name} onChange={onChange} />
        </label>
        <label>
          <span className="label">Project Name</span>
          <input className="input" name="project_name" value={form.project_name} onChange={onChange} />
        </label>
        <label>
          <span className="label">HubSpot URL</span>
          <input className="input" name="hubspot_url" value={form.hubspot_url} onChange={onChange} />
        </label>
        <label>
          <span className="label">Key Contact Full Name</span>
          <input className="input" name="key_contact" value={form.key_contact} onChange={onChange} />
        </label>
        <label>
          <span className="label">Meeting Type</span>
          <input className="input" name="meeting_type" value={form.meeting_type} onChange={onChange} />
        </label>
        <label>
          <span className="label">Meeting ID</span>
          <input className="input" name="meeting_id" value={form.meeting_id} onChange={onChange} />
        </label>
        <label>
          <span className="label">Meeting Number</span>
          <input className="input" name="meeting_number" value={form.meeting_number} onChange={onChange} />
        </label>
        <label className="lg:col-span-2">
          <span className="label">Notes</span>
          <textarea className="input min-h-24" name="notes" value={form.notes} onChange={onChange} />
        </label>

        {error ? <p className="lg:col-span-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

        <div className="lg:col-span-2 flex justify-end">
          <button className="btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create Project"}
          </button>
        </div>
      </form>

      {created ? (
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="font-semibold text-emerald-800">Project {created.projectName} created successfully.</p>
          <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-emerald-700">Secure Client Link</p>
          <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center">
            <input className="input flex-1" readOnly value={created.secureLink} />
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigator.clipboard.writeText(created.secureLink)}
            >
              Copy Link
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
