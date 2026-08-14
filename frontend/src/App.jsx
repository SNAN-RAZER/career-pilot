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

  const [showAllApplications, setShowAllApplications] =
    useState(false);

  const [selectedStoredJobId, setSelectedStoredJobId] =
    useState("");

  const [sourceResume, setSourceResume] = useState("");
  const [profileStatus, setProfileStatus] = useState(null);
  const [parsedFacts, setParsedFacts] = useState(null);
  const [profileBusy, setProfileBusy] = useState(false);
  const [allowSearchAnyway, setAllowSearchAnyway] =
    useState(false);

  const [searchForm, setSearchForm] = useState({
    role: "",
    location: "",
    pages: 1,
    experience: 2,
    jobAge: 3,
  });

  useEffect(() => {
    loadApplications();
    loadSourceResume();
    loadProfileStatus();
  }, []);

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

    try {
      const response = await axios.post(
        `${API_BASE_URL}/profile/parse`,
        body
      );
      setParsedFacts(response.data.facts);
      setSourceResume(response.data.filename);
      await loadProfileStatus();
    } catch (err) {
      alert(
        err.response?.data?.detail
        || "Could not parse that resume file."
      );
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
        }
      );

      setSearchResults(response.data);
      setSelectedStoredJobId("");
      setShowAllApplications(false);
      await loadApplications();
    } catch (err) {
      console.error(err);
      setSearchError(
        err.response?.data?.detail
          || "Job search failed. Check API and Naukri credentials."
      );
    } finally {
      setSearching(false);
    }
  }

  async function performAction(jobId, action) {
    try {
      setActionLoading(`${jobId}-${action}`);

      if (action === "company-apply") {
        const response = await axios.post(
          `${API_BASE_URL}/applications/${jobId}/company-apply`
        );
        const pack = response.data;

        if (pack.apply_url) {
          window.open(pack.apply_url, "_blank");
        }

        window.open(
          `${API_BASE_URL}/applications/${jobId}/resume-file`,
          "_blank"
        );

        alert(
          pack.message
          + "\n\nUpload this resume on the company page:\n"
          + pack.resume_path
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
            AI-powered job search and application
            management
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
                ? "Parsing..."
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
              <p>
                {parsedFacts.name || "No name"}
                {parsedFacts.email
                  ? ` · ${parsedFacts.email}`
                  : ""}
              </p>
              <p>
                {(parsedFacts.experience || []).length}
                {" jobs · "}
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
                    ? `Collected ${searchResults.collected_jobs} · ${searchResults.relevant_jobs} relevant · ${searchResults.applications_queued} queued`
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
                  Saved applications. Pick one from
                  the dropdown or browse the list.
                </p>
              </div>
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
    return "Click Tailor Resume first. For Accenture-style jobs use Company site + resume.";
  }

  if (
    application.ats_score != null
    && application.ats_score < 40
  ) {
    return "Resume match is weak. Apply only if you really want this job.";
  }

  return "Easy Apply works only when Naukri has no extra questions. If a screening form appears, use Open Naukri.";
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

  if (application?.tailored_summary) {
    window.open(
      `${API_BASE_URL}/applications/${jobId}/resume-file`,
      "_blank"
    );
  }
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
              === loadingKey("tailor")
            }
            onClick={() =>
              onAction(jobId, "tailor")
            }
          >
            Tailor Resume
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

        {application.status === "PENDING"
          && application.source === "naukri" && (
          <button
            type="button"
            className="action-button tailor"
            disabled={
              actionLoading
              === loadingKey("company-apply")
            }
            onClick={() =>
              onAction(jobId, "company-apply")
            }
          >
            Company site + resume
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
