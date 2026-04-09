import { useMemo, useState } from "react";
import CreateProjectForm from "./components/CreateProjectForm";
import RecordingsReview from "./components/RecordingsReview";
import AdminProjectsView from "./components/AdminProjectsView";
import { isSupabaseConfigured } from "./lib/supabase";

const navItems = [
  { key: "create", label: "Create Project" },
  { key: "review", label: "Review Recordings" },
  { key: "admin", label: "All Projects" },
];

export default function App() {
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token"), []);
  const [activeView, setActiveView] = useState(token ? "review" : "create");

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-6 md:px-8 md:py-8">
      <header className="mb-6 panel overflow-hidden">
        <div className="grid gap-4 border-b border-[var(--line)] bg-[var(--bg-accent)]/35 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-800">HA Automation Form</p>
            <h1 className="mt-1 font-display text-3xl font-semibold text-brand-900">HA Data Integration</h1>
          </div>

          {!token ? (
            <nav className="grid gap-2 sm:grid-cols-3">
              {navItems.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setActiveView(item.key)}
                  className={
                    activeView === item.key
                      ? "btn-primary"
                      : "btn-secondary"
                  }
                >
                  {item.label}
                </button>
              ))}
            </nav>
          ) : (
            <span className="rounded-lg border border-brand-300 bg-white px-3 py-2 text-sm font-semibold text-brand-900">
              Secure Client Access Mode
            </span>
          )}
        </div>

        {!isSupabaseConfigured ? (
          <div className="m-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Missing Supabase configuration. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your environment.
          </div>
        ) : null}
      </header>

      <main>
        {isSupabaseConfigured ? (
          token || activeView === "review" ? (
            <RecordingsReview projectToken={token} />
          ) : activeView === "create" ? (
            <CreateProjectForm />
          ) : (
            <AdminProjectsView />
          )
        ) : null}
      </main>
    </div>
  );
}
