import { useEffect, useState } from "react";
import { Save, RefreshCw, CheckCircle, XCircle } from "lucide-react";
import {
  fetchSettings,
  updateSettings,
  fetchHealth,
  type AppSettings,
  type HealthStatus,
} from "../api/client";

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchSettings(), fetchHealth()]).then(([s, h]) => {
      setSettings(s);
      setHealth(h);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      // Refresh health after settings change
      const h = await fetchHealth();
      setHealth(h);
    } finally {
      setSaving(false);
    }
  };

  const refreshHealth = async () => {
    const h = await fetchHealth();
    setHealth(h);
  };

  if (loading || !settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Settings</h1>
        <p className="text-slate-400 mt-1">Configure your AI Code Reviewer</p>
      </div>

      {/* Health Status */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100">LLM Provider Status</h2>
          <button
            onClick={refreshHealth}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-700"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        {health && (
          <div className="flex items-center gap-3">
            {health.status === "healthy" ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <XCircle className="w-5 h-5 text-red-400" />
            )}
            <div>
              <span
                className={`text-sm font-medium ${
                  health.status === "healthy" ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {health.status === "healthy" ? "Connected" : "Disconnected"}
              </span>
              {health.provider && (
                <p className="text-xs text-slate-500 mt-0.5">
                  {health.provider} / {health.model}
                </p>
              )}
              {health.error && (
                <p className="text-xs text-red-400 mt-0.5">{health.error}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* LLM Settings */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-100">LLM Configuration</h2>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Provider</label>
          <select
            value={settings.llm_provider}
            onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="groq">Groq (Free — Cloud)</option>
            <option value="ollama">Ollama (Self-Hosted — Local)</option>
          </select>
        </div>

        {settings.llm_provider === "groq" && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Groq Model
            </label>
            <select
              value={settings.groq_model}
              onChange={(e) => setSettings({ ...settings, groq_model: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="llama-3.1-70b-versatile">Llama 3.1 70B</option>
              <option value="llama-3.1-8b-instant">Llama 3.1 8B (Faster)</option>
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
              <option value="deepseek-r1-distill-llama-70b">DeepSeek R1 70B</option>
              <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
              <option value="gemma2-9b-it">Gemma 2 9B</option>
            </select>
          </div>
        )}

        {settings.llm_provider === "ollama" && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Ollama Model
            </label>
            <input
              type="text"
              value={settings.ollama_model}
              onChange={(e) =>
                setSettings({ ...settings, ollama_model: e.target.value })
              }
              placeholder="deepseek-coder-v2"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-500 mt-1">
              Run: <code className="text-blue-400">ollama pull {settings.ollama_model}</code>
            </p>
          </div>
        )}
      </div>

      {/* Review Settings */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-100">Review Settings</h2>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Minimum Inline Comment Severity
          </label>
          <select
            value={settings.min_inline_severity}
            onChange={(e) =>
              setSettings({ ...settings, min_inline_severity: e.target.value })
            }
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="critical">Critical only</option>
            <option value="warning">Warning and above</option>
            <option value="suggestion">All (including suggestions)</option>
          </select>
          <p className="text-xs text-slate-500 mt-1">
            Lower-severity issues will only appear in the summary comment
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Max Files Per Review
          </label>
          <input
            type="number"
            value={settings.max_files_per_review}
            onChange={(e) =>
              setSettings({
                ...settings,
                max_files_per_review: parseInt(e.target.value) || 50,
              })
            }
            min={1}
            max={200}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Max Diff Lines Per File
          </label>
          <input
            type="number"
            value={settings.max_diff_lines_per_file}
            onChange={(e) =>
              setSettings({
                ...settings,
                max_diff_lines_per_file: parseInt(e.target.value) || 500,
              })
            }
            min={100}
            max={2000}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium text-white transition-colors"
      >
        {saved ? (
          <>
            <CheckCircle className="w-4 h-4" /> Saved!
          </>
        ) : saving ? (
          <>
            <RefreshCw className="w-4 h-4 animate-spin" /> Saving...
          </>
        ) : (
          <>
            <Save className="w-4 h-4" /> Save Settings
          </>
        )}
      </button>
    </div>
  );
}
