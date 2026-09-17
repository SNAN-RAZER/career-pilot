# Connect your Career Pilot agent

This workspace is a new frontend for the job-search and application engine in https://github.com/SNAN-RAZER/career-pilot . The connected agent runs Python and a browser, so it needs a machine or server that can run those processes. The website alone does not run a job-board browser.

## What works before connecting

- Explore clearly labeled sample opportunities, search, and save jobs on this device.
- Save job preferences on this device.
- Upload a TXT resume for an in-tab text preview. This is keyword extraction, not AI analysis. The preview is discarded on reload.

PDF/DOCX analysis, real job discovery, tailored resumes, and application submissions require the agent connection. No real applications have been sent during setup.

## Start the agent

1. Clone the referenced Career Pilot repository and follow its Python installation instructions. It requires Python 3.13 or newer.
2. Install the referenced NopeRi client into `third_party/NopeRi`, as described in its README.
3. Configure your Naukri credentials in the backend's local `.env`. Never add credentials to source control or frontend code.
4. Use the original backend's model settings UI to configure a reachable chat model and embedding model. Its existing provider management API is retained.
5. Copy `integrations/pilot_gateway.py` from this app's source into the Career Pilot repository root. This adds a bearer-token boundary and conservative duplicate-submission protection.
6. Set `CAREER_PILOT_GATEWAY_TOKEN` to a long random secret on the backend, then start `uvicorn pilot_gateway:app --host 127.0.0.1 --port 8000` from that repository. Keep its data directory persistent.

For local development, configure `CAREER_PILOT_API_URL=http://127.0.0.1:8000` and `CAREER_PILOT_API_TOKEN` in the frontend's `.env` file. Set the token to the same value as `CAREER_PILOT_GATEWAY_TOKEN`.

For the hosted site, the backend needs a reachable HTTPS endpoint with the same token protection. Set the two server-side environment values in the site's deployment settings. Do not expose the original unauthenticated API to the Internet. `localhost` on the hosted site is not your computer.

## Use live mode

1. Open Agent settings and check the connection.
2. Upload a PDF, DOCX, or TXT resume. Review the extracted facts, then save the profile. Fix incorrect facts in the source resume and upload again.
3. Set target roles, location, experience, minimum match/eligibility, and a limit of 1–20 applications per run.
4. Start with review mode to generate tailored resumes. Enable automatic submission when you want the agent to send eligible applications.
5. Run the agent and keep the tab open. It searches Naukri and processes qualified roles sequentially. Pause takes effect after the in-flight action finishes.
6. Check Applications for confirmed submissions or steps needing attention. A prepared or filled browser form is not counted as a confirmed submission. Browser fallback may still require manual submission, sign-in, or MFA.

## Scope and operating notes

This release is for one private owner's account. It is not a multi-tenant SaaS service. Keep the site owner-private and the backend token protected. Background scheduling across closed tabs, multiple job-board integrations, and multi-user billing are not implemented.

Resume facts and application records are stored by the Python backend. The website stores only saved-job IDs and preferences in local browser storage. The backend's original provider configuration may store API keys locally; protect its data directory.

After an interrupted or uncertain automatic application, the gateway blocks repeat submissions for that job until you manually reconcile the outcome. A skipped/failed result can be retried, but a prepared form or ambiguous network outcome needs review. Run activity is session-only; refresh reads the backend's persistent application records.

The original upstream browser fallback has limitations: it may only fill a company form and may not persist that activity in its application store. This frontend distinguishes the immediate result, while the included gateway remembers guarded application outcomes across refreshes.
