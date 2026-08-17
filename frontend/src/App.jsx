import { useEffect, useState } from "react";
import axios from "axios";
import {
  Briefcase,
  CheckCircle2,
  Clock3,
  Search,
  TrendingUp,
} from "lucide-react";

import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";
const MIN_MATCH_SCORE = 80;

function searchFailureMessage(err) {
  const detail = err.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => item.msg || JSON.stringify(item))
      .join("; ");
  }

  if (err.code === "ECONNABORTED") {
    return (
      "Search timed out while ranking jobs. "
      + "Keep the API running and try 1 page."
    );
  }

  if (!err.response) {
    return (
      "Cannot reach the API at 127.0.0.1:8000. "
      + "Start uvicorn, then search again."
    );
  }

  return (
    "Job search failed ("
    + err.response.status
    + "). Check the API terminal for the traceback."
  );
}

const DUMMY_COMPANIES = new Set([
  "API Test Company",
  "AI Company",
  "Search Test Co",
  "Naukri Co",
]);

function isRealJob(application) {
  if (application.source === "test") {
    return false;
  }

  if (DUMMY_COMPANIES.has(application.company)) {
    return false;
  }

  const jobId = application.job_id || "";

  if (jobId.startsWith("api-test")) {
    return false;
  }

  return true;
}

function App() {
  const [applications, setApplications] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [bulkApplying, setBulkApplying] = useState(false);
  const [bulkProgress, setBulkProgress] = useState("");

  const [showAllApplications, setShowAllApplications] =
    useState(false);

  const [selectedStoredJobId, setSelectedStoredJobId] =
    useState("");

  const [sourceResume, setSourceResume] = useState("");
  const [profileStatus, setProfileStatus] = useState(null);
  const [parsedFacts, setParsedFacts] = useState(null);
  const [parseMeta, setParseMeta] = useState(null);
  const [profileBusy, setProfileBusy] = useState(false);
  const [llmSettings, setLlmSettings] = useState(null);
  const [llmModels, setLlmModels] = useState([]);
  const [llmEmbedModels, setLlmEmbedModels] = useState([]);
  const [llmModelsError, setLlmModelsError] = useState("");
  const [llmBusy, setLlmBusy] = useState(false);
  const [llmForm, setLlmForm] = useState({
    kind: "custom",
    label: "",
    base_url: "",
    api_key: "",
    chat_model: "",
  });

  const [searchForm, setSearchForm] = useState({
    role: "",
    location: "",
    pages: 3,
    experience: 6,
    jobAge: 30,
  });

  useEffect(() => {
    loadApplications();
    loadSourceResume();
    loadProfileStatus();
    loadLlmSettings();
  }, []);

  async function loadLlmSettings() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/llm/settings`
      );
      setLlmSettings(response.data);
      const activeId = response.data.active_id;

      if (activeId) {
        await loadLlmModels(activeId);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function loadLlmModels(providerId) {
    if (!providerId) {
      setLlmModels([]);
      setLlmEmbedModels([]);
      return { models: [], embedding_models: [] };
    }

    setLlmModelsError("");

    try {
      const response = await axios.get(
        `${API_BASE_URL}/llm/providers/${providerId}/models`
      );
      const models = response.data.models || [];
      const embeddingModels =
        response.data.embedding_models || [];
      setLlmModels(models);
      setLlmEmbedModels(embeddingModels);

      if (!models.length) {
        setLlmModelsError(
          "No chat models found. Start Ollama or LM Studio, then refresh."
        );
      }

      return {
        models,
        embedding_models: embeddingModels,
      };
    } catch (err) {
      setLlmModels([]);
      setLlmEmbedModels([]);
      setLlmModelsError(
        err.response?.data?.detail
        || "Could not list models from that host."
      );
      return { models: [], embedding_models: [] };
    }
  }

  async function activateLlm(
    providerId,
    chatModel,
    embeddingModel
  ) {
    const model = (
      chatModel
      || llmSettings?.active?.chat_model
      || ""
    ).trim();
    const embedding = (
      embeddingModel
      || llmSettings?.active?.embedding_model
      || ""
    ).trim();

    if (!providerId || !model) {
      return;
    }

    setLlmSettings((current) => {
      if (!current) {
        return current;
      }

      const providers = (current.providers || []).map(
        (item) =>
          item.id === providerId
            ? {
                ...item,
                chat_model: model,
                embedding_model: embedding || item.embedding_model,
              }
            : item
      );
      const active = providers.find(
        (item) => item.id === providerId
      ) || {
        ...(current.active || {}),
        id: providerId,
        chat_model: model,
        embedding_model: embedding,
      };

      return {
        ...current,
        active_id: providerId,
        active,
        providers,
      };
    });
    setLlmBusy(true);

    try {
      await axios.post(
        `${API_BASE_URL}/llm/activate`,
        {
          provider_id: providerId,
          chat_model: model,
          embedding_model: embedding || undefined,
        }
      );
      await loadLlmSettings();
    } catch (err) {
      alert(
        err.response?.data?.detail
        || "Could not activate that LLM."
      );
      await loadLlmSettings();
    } finally {
      setLlmBusy(false);
    }
  }

  async function saveLlmProvider(event) {
    event.preventDefault();
    setLlmBusy(true);

    try {
      const saved = await axios.post(
        `${API_BASE_URL}/llm/providers`,
        llmForm
      );
      const model = (
        llmForm.chat_model
        || saved.data.chat_model
        || ""
      ).trim();

      if (model) {
        await axios.post(
          `${API_BASE_URL}/llm/activate`,
          {
            provider_id: saved.data.id,
            chat_model: model,
          }
        );
      }
      setLlmForm({
        kind: "custom",
        label: "",
        base_url: "",
        api_key: "",
        chat_model: "",
      });
      await loadLlmSettings();
    } catch (err) {
      alert(
        err.response?.data?.detail
        || "Could not save that LLM provider."
      );
    } finally {
      setLlmBusy(false);
    }
  }

  function llmKindDefaults(kind) {
    if (kind === "lmstudio") {
      return {
        label: "LM Studio",
        base_url: "http://localhost:1234/v1",
      };
    }

    if (kind === "ollama") {
      return {
        label: "Ollama",
        base_url: "http://localhost:11434/v1",
      };
    }

    if (kind === "openai") {
      return {
        label: "OpenAI",
        base_url: "https://api.openai.com/v1",
      };
    }

    if (kind === "anthropic") {
      return {
        label: "Anthropic",
        base_url: "https://api.anthropic.com/v1",
      };
    }

    return {
      label: "Custom API",
      base_url: "",
    };
  }

  async function loadProfileStatus() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/profile`
      );
      setProfileStatus(response.data);

      if (response.data.source_resume) {
        setSourceResume(response.data.source_resume);
      }

      if (response.data.preview) {
        setParsedFacts((current) =>
          current || response.data.preview
        );
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function loadSourceResume() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/profile/source-resume`
      );

      if (response.data.uploaded) {
        setSourceResume(response.data.filename);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function parseResumeFile(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    const body = new FormData();
    body.append("resume_file", file);
    setProfileBusy(true);
    setParsedFacts(null);
    setParseMeta(null);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/profile/parse`,
        body
      );
      setParsedFacts(response.data.facts);
      setParseMeta({
        source: response.data.source,
        model: response.data.model,
        kind: response.data.kind,
      });
      setSourceResume(response.data.filename);
      await loadProfileStatus();
    } catch (err) {
      alert(
        err.response?.data?.detail
        || "Could not parse that resume file."
      );
      await loadProfileStatus();
    } finally {
      setProfileBusy(false);
      event.target.value = "";
    }
  }

  async function storeParsedProfile() {
    setProfileBusy(true);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/profile/store`
      );
      setParsedFacts(null);
      await loadProfileStatus();
      alert(
        `Stored ${response.data.name} in profile JSON `
        + `(${response.data.jobs_count} jobs, `
        + `${response.data.skills_count} skills).`
      );
    } catch (err) {
      alert(
        err.response?.data?.detail
        || "Could not store parsed resume."
      );
    } finally {
      setProfileBusy(false);
    }
  }

  async function loadApplications() {
    try {
      setLoading(true);

      const response = await axios.get(
        `${API_BASE_URL}/applications`
      );

      setApplications(
        response.data.filter(isRealJob)
      );
      setError(null);
    } catch (err) {
      console.error(err);
      setError(
        "Unable to connect to Career-Pilot API."
      );
    } finally {
      setLoading(false);
    }
  }

  async function searchJobs(event) {
    event.preventDefault();

    if (
      profileStatus
      && !profileStatus.complete
      && !allowSearchAnyway
    ) {
      setSearchError(
        "Profile JSON is missing "
        + (profileStatus.missing || []).join(", ")
        + ". Parse and store your resume first, or choose Search anyway."
      );
      return;
    }

    try {
      setSearching(true);
      setSearchError(null);

      const response = await axios.post(
        `${API_BASE_URL}/jobs/search`,
        {
          queries: [
            searchForm.role.trim(),
          ],
          location: searchForm.location,
          pages: searchForm.pages,
          experience: searchForm.experience,
          job_age: searchForm.jobAge,
        },
        { timeout: 600000 }
      );

      setSearchResults(response.data);
      setSelectedStoredJobId("");
      setShowAllApplications(false);
      await loadApplications();
    } catch (err) {
      console.error(err);
      setSearchError(searchFailureMessage(err));
    } finally {
      setSearching(false);
    }
  }

  async function performAction(jobId, action) {
    try {
      setActionLoading(`${jobId}-${action}`);

      if (action === "download-resume") {
        await downloadTailoredResume(jobId);
        await loadApplications();
        return;
      }

      if (action === "web-apply") {
        const response = await axios.post(
          `${API_BASE_URL}/applications/${jobId}/web-apply`,
          null,
          { timeout: 300000 }
        );
        const report = response.data;
        alert(
          (report.message || "Web agent finished.")
          + "\n\nStatus: "
          + report.status
          + "\nPage: "
          + (report.current_url || report.apply_url)
          + (
            report.filled?.length
              ? "\nFilled: " + report.filled.join("; ")
              : ""
          )
          + (
            report.thoughts?.length
              ? "\n\nAgent thinking:\n- "
                + report.thoughts.slice(-6).join("\n- ")
              : ""
          )
          + (
            report.steps?.length
              ? "\n\nActions:\n- "
                + report.steps.slice(-8).join("\n- ")
              : ""
          )
        );
        await loadApplications();
        return;
      }

      const response = await axios.post(
        `${API_BASE_URL}/applications/${jobId}/${action}`
      );

      setApplications((current) =>
        current.map((application) =>
          application.job_id === jobId
            ? response.data
            : application
        )
      );
    } catch (err) {
      console.error(err);

      const detail = err.response?.data?.detail;
      const message = applyErrorMessage(detail)
        || `Failed to ${action} application.`;
      const application = applications.find(
        (item) => item.job_id === jobId
      );

      if (
        action === "apply"
        && shouldOpenNaukri(message)
      ) {
        openNaukriApply(jobId, application);
      }

      alert(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function applyToQualifiedJobs() {
    if (!bulkTargets.length) {
      alert(
        `No pending APPLY jobs with match ≥ ${MIN_MATCH_SCORE}%.`
      );
      return;
    }

    const confirmed = window.confirm(
      `Apply to all ${bulkTargets.length} qualified job(s) `
      + `(match ≥ ${MIN_MATCH_SCORE}%, APPLY).\n`
      + "Easy Apply first; company sites fall back to the web agent.\n"
      + "If one job fails, the rest still run."
    );

    if (!confirmed) {
      return;
    }

    const applied = [];
    const skipped = [];
    const failed = [];

    try {
      setBulkApplying(true);

      for (let index = 0; index < bulkTargets.length; index += 1) {
        const job = bulkTargets[index];
        setBulkProgress(
          `${index + 1}/${bulkTargets.length}`
        );

        try {
          const response = await axios.post(
            `${API_BASE_URL}/applications/${job.job_id}/auto-apply`,
            null,
            { timeout: 300000 }
          );
          const item = response.data;

          if (item.status === "applied") {
            applied.push(item);
          } else if (item.status === "failed") {
            failed.push(item);
          } else {
            skipped.push(item);
          }
        } catch (err) {
          failed.push({
            title: job.title,
            detail:
              applyErrorMessage(err.response?.data?.detail)
              || err.message
              || "Request failed",
          });
        }
      }

      const skippedText = skipped
        .slice(0, 8)
        .map((item) => `${item.title}: ${item.detail}`)
        .join("\n")
        || "none";
      const failedText = failed
        .slice(0, 8)
        .map((item) => `${item.title}: ${item.detail}`)
        .join("\n")
        || "none";

      alert(
        `Finished ${bulkTargets.length} qualified jobs.\n`
        + `Applied: ${applied.length}\n`
        + `Skipped: ${skipped.length}\n`
        + `Failed: ${failed.length}\n\n`
        + `Applied titles: ${
          applied.map((item) => item.title).join(", ") || "none"
        }\n\nSkipped:\n${skippedText}\n\nFailed:\n${failedText}`
      );
      await loadApplications();
    } finally {
      setBulkApplying(false);
      setBulkProgress("");
    }
  }

  const searchJobIds = searchResults
    ? new Set(
        (searchResults.rankings || [])
          .map((ranking) => ranking.job_id)
          .filter(Boolean)
      )
    : null;

  const visibleApplications =
    searchJobIds && !showAllApplications
      ? applications.filter((application) =>
          searchJobIds.has(application.job_id)
        )
      : applications;

  const displayedApplications = selectedStoredJobId
    ? applications.filter(
        (application) =>
          application.job_id === selectedStoredJobId
      )
    : visibleApplications;

  const totalApplications = applications.length;

  const pendingApplications =
    applications.filter(
      (application) =>
        application.status === "PENDING"
    ).length;

  const bulkTargets = applications.filter(
    (application) =>
      application.status === "PENDING"
      && application.recommendation === "APPLY"
      && application.match_score >= MIN_MATCH_SCORE
      && (
        application.eligibility_score == null
        || application.eligibility_score >= MIN_MATCH_SCORE
      )
  );

  const appliedApplications =
    applications.filter(
      (application) =>
        application.status === "APPLIED"
    ).length;

  const offers =
    applications.filter(
      (application) =>
        application.status === "OFFER"
    ).length;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Career-Pilot</h1>
          <p>
            {llmSettings?.active
              ? `${llmSettings.active.label}${
                  llmSettings.active.chat_model
                    ? ` · ${llmSettings.active.chat_model}`
                    : ""
                }`
              : "AI-powered job search and application management"}
          </p>
        </div>

        <button
          type="button"
          className="refresh-button"
          onClick={loadApplications}
        >
          Refresh
        </button>
      </header>

      <main className="dashboard">
        <section className="search-section">
          <div className="section-header">
            <div>
              <h2>LLM provider</h2>
              <p>
                Use one chat model at a time from
                LM Studio, Ollama, OpenAI, Anthropic,
                or any URL + API key.
              </p>
            </div>
          </div>

          {llmSettings?.active && (
            <p className="search-summary">
              Active: {llmSettings.active.label}
              {llmSettings.active.chat_model
                ? ` · ${llmSettings.active.chat_model}`
                : " · no model selected"}
              {llmSettings.active.embedding_model
                ? ` · embed ${llmSettings.active.embedding_model}`
                : " · no embedding model"}
              {` · ${llmSettings.active.base_url}`}
              {llmModels.length
                ? ` · ${llmModels.length} models`
                : ""}
            </p>
          )}
          {llmModelsError && (
            <p className="search-summary">{llmModelsError}</p>
          )}

          <div className="search-form llm-provider-row">
            <label>
              Provider
              <select
                value={llmSettings?.active_id || ""}
                disabled={llmBusy}
                onChange={async (event) => {
                  const id = event.target.value;
                  const provider = (
                    llmSettings?.providers || []
                  ).find((item) => item.id === id);
                  const listed = await loadLlmModels(id);
                  const model = (
                    provider?.chat_model
                    || listed.models[0]
                    || ""
                  ).trim();
                  const embedding = (
                    provider?.embedding_model
                    || listed.embedding_models[0]
                    || ""
                  ).trim();

                  if (!model) {
                    alert(
                      "No chat model on that host. Start Ollama or LM Studio, then pick a model."
                    );
                    return;
                  }

                  await activateLlm(id, model, embedding);
                }}
              >
                {(llmSettings?.providers || []).map(
                  (provider) => (
                    <option
                      key={provider.id}
                      value={provider.id}
                    >
                      {provider.label} ({provider.kind})
                    </option>
                  )
                )}
              </select>
            </label>

            <label>
              Chat model
              <select
                value={
                  llmSettings?.active?.chat_model || ""
                }
                disabled={llmBusy || !llmSettings?.active_id}
                onChange={(event) => {
                  const model = event.target.value.trim();

                  if (!model) {
                    return;
                  }

                  activateLlm(
                    llmSettings.active_id,
                    model
                  );
                }}
              >
                <option value="">
                  {llmModels.length
                    ? `Select from ${llmModels.length} hosted models`
                    : "No hosted models yet"}
                </option>
                {llmModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
                {llmSettings?.active?.chat_model
                  && !llmModels.includes(
                    llmSettings.active.chat_model
                  ) && (
                  <option
                    value={llmSettings.active.chat_model}
                  >
                    {llmSettings.active.chat_model}
                  </option>
                )}
              </select>
            </label>

            <label>
              Embedding model
              <select
                value={
                  llmSettings?.active?.embedding_model || ""
                }
                disabled={llmBusy || !llmSettings?.active_id}
                onChange={(event) => {
                  const model = event.target.value.trim();

                  if (!model) {
                    return;
                  }

                  activateLlm(
                    llmSettings.active_id,
                    llmSettings.active?.chat_model,
                    model
                  );
                }}
              >
                <option value="">
                  {llmEmbedModels.length
                    ? `Select from ${llmEmbedModels.length} embedding models`
                    : "No embedding models yet"}
                </option>
                {llmEmbedModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
                {llmSettings?.active?.embedding_model
                  && !llmEmbedModels.includes(
                    llmSettings.active.embedding_model
                  ) && (
                  <option
                    value={llmSettings.active.embedding_model}
                  >
                    {llmSettings.active.embedding_model}
                  </option>
                )}
              </select>
            </label>

            <button
              type="button"
              className="ghost-button"
              disabled={llmBusy || !llmSettings?.active_id}
              onClick={() =>
                loadLlmModels(llmSettings.active_id)
              }
            >
              Refresh models
            </button>
          </div>

          <form
            className="search-form"
            onSubmit={saveLlmProvider}
          >
            <label>
              Kind
              <select
                value={llmForm.kind}
                onChange={(event) => {
                  const kind = event.target.value;
                  const defaults = llmKindDefaults(kind);
                  setLlmForm({
                    ...llmForm,
                    kind,
                    label: defaults.label,
                    base_url: defaults.base_url
                      || llmForm.base_url,
                  });
                }}
              >
                <option value="lmstudio">LM Studio</option>
                <option value="ollama">Ollama</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="custom">
                  Custom OpenAI-compatible
                </option>
              </select>
            </label>

            <label>
              Label
              <input
                value={llmForm.label}
                onChange={(event) =>
                  setLlmForm({
                    ...llmForm,
                    label: event.target.value,
                  })
                }
                placeholder="Work OpenAI"
              />
            </label>

            <label>
              Base URL
              <input
                value={llmForm.base_url}
                onChange={(event) =>
                  setLlmForm({
                    ...llmForm,
                    base_url: event.target.value,
                  })
                }
                placeholder="https://api.openai.com/v1"
                required
              />
            </label>

            <label>
              API key
              <input
                type="password"
                value={llmForm.api_key}
                onChange={(event) =>
                  setLlmForm({
                    ...llmForm,
                    api_key: event.target.value,
                  })
                }
                placeholder="optional for local hosts"
              />
            </label>

            <label>
              Model id
              <input
                value={llmForm.chat_model}
                onChange={(event) =>
                  setLlmForm({
                    ...llmForm,
                    chat_model: event.target.value,
                  })
                }
                placeholder="gpt-4o-mini"
              />
            </label>

            <button
              type="submit"
              className="search-button"
              disabled={llmBusy}
            >
              {llmBusy ? "Saving..." : "Save & use"}
            </button>
          </form>
        </section>

        <section className="search-section">
          <div className="section-header">
            <div>
              <h2>Profile JSON</h2>
              <p>
                Parse a resume into structured data,
                then store it as candidate.json
                before searching or tailoring.
              </p>
            </div>
          </div>

          {profileStatus && (
            <p className="search-summary">
              {profileStatus.complete
                ? `Ready: ${profileStatus.name} · ${profileStatus.jobs_count} jobs · ${profileStatus.skills_count} skills`
                : `Incomplete JSON. Missing: ${(profileStatus.missing || []).join(", ") || "profile"}`}
              {sourceResume
                ? ` · file ${sourceResume}`
                : " · no source file yet"}
            </p>
          )}

          {profileStatus && !profileStatus.complete && (
            <div className="banner error">
              Profile JSON is not ready. Parse a resume,
              then store it before searching. You can
              still choose Search anyway.
            </div>
          )}

          <div className="application-actions">
            <label className="action-button tailor">
              {profileBusy
                ? "Parsing with LLM..."
                : "1. Parse resume"}
              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                hidden
                disabled={profileBusy}
                onChange={parseResumeFile}
              />
            </label>

            <button
              type="button"
              className="action-button apply"
              disabled={profileBusy || !profileStatus?.parsed_preview}
              onClick={storeParsedProfile}
            >
              2. Store in profile JSON
            </button>

            {profileStatus
              && !profileStatus.complete
              && !allowSearchAnyway && (
              <button
                type="button"
                className="ghost-button"
                onClick={() =>
                  setAllowSearchAnyway(true)
                }
              >
                Search anyway
              </button>
            )}
          </div>

          {parsedFacts && (
            <div className="resume-preview">
              <h4>Parsed preview (not stored yet)</h4>
              {parseMeta?.model && (
                <p>
                  {`Via ${parseMeta.kind} · ${parseMeta.model}`}
                </p>
              )}
              <p>
                {parsedFacts.name || "No name"}
                {parsedFacts.email
                  ? ` · ${parsedFacts.email}`
                  : ""}
              </p>
              <p>
                {(parsedFacts.experience || []).length}
                {" jobs · "}
                {(parsedFacts.projects || []).length}
                {" projects · "}
                {(parsedFacts.skills || []).length}
                {" skills"}
              </p>
              {(parsedFacts.experience || []).length > 0 && (
                <ul>
                  {(parsedFacts.experience || [])
                    .slice(0, 6)
                    .map((job, index) => (
                      <li key={`${job.company}-${index}`}>
                        {job.title || job.role || "Role"}
                        {job.company
                          ? ` · ${job.company}`
                          : ""}
                        {(job.technologies || []).length
                          ? ` · ${(job.technologies || []).slice(0, 6).join(", ")}`
                          : ""}
                      </li>
                    ))}
                </ul>
              )}
              {(parsedFacts.projects || []).length > 0 && (
                <ul>
                  {(parsedFacts.projects || [])
                    .slice(0, 4)
                    .map((project, index) => (
                      <li key={`${project.name}-${index}`}>
                        {project.name || "Project"}
                        {(project.technologies || []).length
                          ? ` · ${(project.technologies || []).slice(0, 6).join(", ")}`
                          : ""}
                      </li>
                    ))}
                </ul>
              )}
              {(parsedFacts.skills || []).length > 0 && (
                <ul className="resume-skills">
                  {(parsedFacts.skills || [])
                    .slice(0, 16)
                    .map((skill) => (
                      <li key={skill}>{skill}</li>
                    ))}
                </ul>
              )}
            </div>
          )}
        </section>

        <section className="search-section">
          <div className="section-header">
            <div>
              <h2>Search Naukri</h2>
              <p>
                Type a role and city. Results stay
                on the left; saved jobs stay on the
                right.
              </p>
            </div>
          </div>

          <form
            className="search-form"
            onSubmit={searchJobs}
          >
            <label>
              Role
              <input
                type="text"
                value={searchForm.role}
                onChange={(event) =>
                  setSearchForm({
                    ...searchForm,
                    role: event.target.value,
                  })
                }
                placeholder="AI Engineer"
                required
              />
            </label>

            <label>
              Location
              <input
                type="text"
                value={searchForm.location}
                onChange={(event) =>
                  setSearchForm({
                    ...searchForm,
                    location: event.target.value,
                  })
                }
                placeholder="Bangalore"
              />
            </label>

            <button
              type="submit"
              className="search-button"
              disabled={
                searching
                || (
                  Boolean(profileStatus)
                  && !profileStatus.complete
                  && !allowSearchAnyway
                )
              }
            >
              <Search size={18} />
              {searching
                ? "Searching..."
                : "Search Jobs"}
            </button>
          </form>

          {searchError && (
            <div className="banner error">
              {searchError}
            </div>
          )}
        </section>

        <section className="stats-grid">
          <StatCard
            title="Stored jobs"
            value={totalApplications}
            icon={<Briefcase size={22} />}
          />

          <StatCard
            title="Pending"
            value={pendingApplications}
            icon={<Clock3 size={22} />}
          />

          <StatCard
            title="Applied"
            value={appliedApplications}
            icon={<CheckCircle2 size={22} />}
          />

          <StatCard
            title="Offers"
            value={offers}
            icon={<TrendingUp size={22} />}
          />
        </section>

        <div className="workspace">
          <section className="panel rankings-panel">
            <div className="section-header">
              <div>
                <h2>This search</h2>
                <p>
                  {searchResults
                    ? `Naukri returned ${searchResults.collected_jobs} · ${searchResults.relevant_jobs} passed filters · dropped ${
                        (searchResults.rejected_by_target || 0)
                        + (searchResults.rejected_by_candidate_fit || 0)
                      } (title ${searchResults.rejected_by_target || 0}, skills ${searchResults.rejected_by_candidate_fit || 0}) · ${searchResults.applications_queued} queued`
                    : "Run a search to rank live Naukri jobs."}
                </p>
              </div>
            </div>

            {!searchResults && (
              <div className="empty-state">
                Search for a role to see ranked
                jobs here.
              </div>
            )}

            {searchResults
              && searchResults.rankings.length === 0 && (
              <div className="empty-state">
                No ranked jobs for this query.
              </div>
            )}

            {searchResults
              && searchResults.rankings.length > 0 && (
              <div className="ranking-list">
                {searchResults.rankings.map(
                  (ranking) => (
                    <article
                      key={
                        ranking.job_id
                        || `${ranking.rank}-${ranking.title}`
                      }
                      className={`ranking-card rec-${(
                        ranking.recommendation || ""
                      ).toLowerCase()}`}
                    >
                      <div className="ranking-top">
                        <span className="rank-index">
                          #{ranking.rank}
                        </span>
                        <span
                          className={`rec-badge rec-${(
                            ranking.recommendation || ""
                          ).toLowerCase()}`}
                        >
                          {ranking.recommendation}
                        </span>
                      </div>
                      <h3>{ranking.title}</h3>
                      <p className="ranking-meta">
                        {ranking.company}
                        {ranking.location
                          ? ` · ${ranking.location}`
                          : ""}
                      </p>
                      <p className="ranking-score">
                        Match {ranking.score}%
                      </p>
                      {ranking.missing_requirements
                        ?.length > 0 && (
                        <p className="ranking-missing">
                          Missing:{" "}
                          {ranking.missing_requirements
                            .slice(0, 4)
                            .join(", ")}
                        </p>
                      )}
                    </article>
                  )
                )}
              </div>
            )}
          </section>

          <section className="panel applications-section">
            <div className="section-header">
              <div>
                <h2>Stored jobs</h2>
                <p>
                  Apply to all only runs APPLY jobs at
                  ≥ {MIN_MATCH_SCORE}% match. REJECT
                  jobs are stored so you can still
                  tailor or apply one by one.
                </p>
              </div>
              <div className="application-actions">
              {searchJobIds && (
                <button
                  type="button"
                  className="ghost-button"
                  onClick={() => {
                    setShowAllApplications(
                      (current) => !current
                    );
                    setSelectedStoredJobId("");
                  }}
                >
                  {showAllApplications
                    ? "This search"
                    : "All saved"}
                </button>
              )}
              <button
                type="button"
                className="action-button apply"
                disabled={
                  bulkApplying
                  || bulkTargets.length === 0
                }
                onClick={applyToQualifiedJobs}
              >
                {bulkApplying
                  ? `Applying ${bulkProgress || "..."}`
                  : `Apply to all (${bulkTargets.length} ≥ ${MIN_MATCH_SCORE}%)`}
              </button>
              </div>
            </div>

            <label className="stored-jobs-label">
              Stored jobs
              <select
                className="stored-jobs-dropdown"
                value={selectedStoredJobId}
                onChange={(event) =>
                  setSelectedStoredJobId(
                    event.target.value
                  )
                }
              >
                <option value="">
                  {applications.length === 0
                    ? "No stored jobs yet"
                    : `All stored jobs (${applications.length})`}
                </option>
                {applications.map((application) => (
                  <option
                    key={application.job_id}
                    value={application.job_id}
                  >
                    {application.title}
                    {" — "}
                    {application.company}
                    {" ("}
                    {application.status}
                    {")"}
                  </option>
                ))}
              </select>
            </label>

            {loading && (
              <div className="empty-state">
                Loading stored jobs...
              </div>
            )}

            {error && (
              <div className="banner error">
                {error}
              </div>
            )}

            {!loading &&
              !error &&
              displayedApplications.length === 0 && (
                <div className="empty-state">
                  {searchJobIds && !showAllApplications
                    ? "No stored cards for this search yet. Choose a job from the dropdown, or search again."
                    : "No stored jobs yet. Search to save ranked roles here."}
                </div>
              )}

            {!loading &&
              !error &&
              displayedApplications.length > 0 && (
                <div className="application-list">
                  {displayedApplications.map(
                    (application) => (
                      <ApplicationCard
                        key={application.job_id}
                        application={application}
                        actionLoading={actionLoading}
                        onAction={performAction}
                      />
                    )
                  )}
                </div>
              )}
          </section>
        </div>
      </main>
    </div>
  );
}

function StatCard({ title, value, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">
        {icon}
      </div>

      <div>
        <p>{title}</p>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function easyApplyHint(application) {
  if (application.recommendation === "REJECT") {
    return "Career-Pilot scored this as REJECT. You can still tailor and apply if you want this company.";
  }

  if (
    application.source === "naukri"
    && !application.tailored_summary
  ) {
    return "Click Tailor & download DOCX for this company, or Web agent apply.";
  }

  if (
    application.ats_score != null
    && application.ats_score < 40
  ) {
    return "Resume match is weak. Apply only if you really want this job.";
  }

  return "Use Tailor & download DOCX to save a resume for this company. Web agent apply uses a temporary DOCX on the company site and deletes it after. Open Naukri only opens the listing.";
}

function applyErrorMessage(detail) {
  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    return detail.message || "";
  }

  return "";
}

function shouldOpenNaukri(message) {
  return /questionnaire|manually on naukri|did not confirm|external company/i.test(
    message || ""
  );
}

function openNaukriApply(jobId, application) {
  if (application?.url) {
    window.open(application.url, "_blank");
  }
}

async function downloadTailoredResume(jobId) {
  const response = await axios.get(
    `${API_BASE_URL}/applications/${jobId}/resume-file`,
    {
      responseType: "blob",
      timeout: 180000,
    }
  );
  const disposition =
    response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || "tailored-resume.docx";
  const blob = new Blob([response.data], {
    type:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function ApplicationCard({
  application,
  actionLoading,
  onAction,
}) {
  const jobId = application.job_id;
  const loadingKey = (action) =>
    `${jobId}-${action}`;

  return (
    <article className="application-card">
      <div className="application-main">
        <div>
          <h3>{application.title}</h3>

          <p className="company">
            {application.company}
          </p>

          <p className="location">
            {application.location}
          </p>
        </div>

        <div className="application-status">
          <span
            className={`status status-${application.status.toLowerCase()}`}
          >
            {application.status}
          </span>
        </div>
      </div>

      <div className="application-details">
        <div>
          <span>Match</span>
          <strong>
            {application.match_score}%
          </strong>
        </div>

        <div>
          <span>Eligibility</span>
          <strong>
            {application.eligibility_score}%
          </strong>
        </div>

        <div>
          <span>Recommendation</span>
          <strong>
            {application.recommendation}
          </strong>
        </div>

        <div>
          <span>Next Action</span>
          <strong>
            {application.next_action}
          </strong>
        </div>

        <div>
          <span>ATS</span>
          <strong>
            {application.ats_score != null
              ? `${application.ats_score}%`
              : "—"}
          </strong>
        </div>
      </div>

      <div className="application-actions">
        {application.status === "PENDING" && (
          <button
            type="button"
            className="action-button tailor"
            disabled={
              actionLoading
              === loadingKey("download-resume")
            }
            onClick={() =>
              onAction(jobId, "download-resume")
            }
          >
            {actionLoading
              === loadingKey("download-resume")
              ? "Building DOCX..."
              : "Tailor & download DOCX"}
          </button>
        )}

        {application.status === "PENDING" && (
          <button
            type="button"
            className="action-button apply"
            disabled={
              actionLoading === loadingKey("apply")
              || (
                application.source === "naukri"
                && !application.tailored_summary
              )
            }
            title={easyApplyHint(application)}
            onClick={() =>
              onAction(jobId, "apply")
            }
          >
            {application.source === "naukri"
              ? "Easy Apply"
              : "Apply"}
          </button>
        )}

        {application.status === "PENDING"
          && application.source === "naukri"
          && application.url && (
          <button
            type="button"
            className="action-button tailor"
            onClick={() =>
              openNaukriApply(
                jobId,
                application
              )
            }
          >
            Open Naukri
          </button>
        )}

        {application.status === "PENDING" && (
          <button
            type="button"
            className="action-button apply"
            disabled={
              actionLoading
              === loadingKey("web-apply")
            }
            title={
              "Agent observes the live page stage (listing → Apply → form), thinks, then clicks/fills using only your profile JSON. Needs Ollama/LM Studio running."
            }
            onClick={() =>
              onAction(jobId, "web-apply")
            }
          >
            {actionLoading === loadingKey("web-apply")
              ? "Web agent running..."
              : "Web agent apply"}
          </button>
        )}

        {application.status === "PENDING" && (
          <p className="apply-hint">
            {easyApplyHint(application)}
          </p>
        )}

        {application.status === "APPLIED" && (
          <button
            type="button"
            className="action-button interview"
            disabled={
              actionLoading
              === loadingKey("interview")
            }
            onClick={() =>
              onAction(jobId, "interview")
            }
          >
            Interview
          </button>
        )}

        {application.status === "INTERVIEW" && (
          <>
            <button
              type="button"
              className="action-button offer"
              disabled={
                actionLoading
                === loadingKey("offer")
              }
              onClick={() =>
                onAction(jobId, "offer")
              }
            >
              Offer
            </button>

            <button
              type="button"
              className="action-button reject"
              disabled={
                actionLoading
                === loadingKey("reject")
              }
              onClick={() =>
                onAction(jobId, "reject")
              }
            >
              Reject
            </button>
          </>
        )}

        {![
          "OFFER",
          "REJECTED",
        ].includes(application.status) && (
          <button
            type="button"
            className="action-button reject"
            disabled={
              actionLoading
              === loadingKey("reject")
            }
            onClick={() =>
              onAction(jobId, "reject")
            }
          >
            Reject
          </button>
        )}
      </div>

      {application.tailored_summary && (
        <div className="resume-preview">
          <h4>Tailored resume</h4>
          <p>{application.tailored_summary}</p>
          {application.tailored_skills?.length > 0 && (
            <ul className="resume-skills">
              {application.tailored_skills.map(
                (skill) => (
                  <li key={skill}>{skill}</li>
                )
              )}
            </ul>
          )}
          {application.apply_message && (
            <p className="apply-message">
              {application.apply_message}
            </p>
          )}
        </div>
      )}
    </article>
  );
}

export default App;
