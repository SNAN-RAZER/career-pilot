# Career Pilot workspace

A new responsive React/TypeScript interface integrated with the Python agent from [SNAN-RAZER/career-pilot](https://github.com/SNAN-RAZER/career-pilot). The frontend is authored here; the upstream repository is not vendored or modified.

## Implemented

- Overview, searchable job matches, device-local saved jobs, application pipeline, resume review, and agent preferences.
- In-tab TXT resume extraction before a backend is available; connected PDF/DOCX/TXT parsing through the existing agent.
- Server-side API proxy with a fixed configured destination, action allowlist, same-origin mutation checks, upload limits, and server-only bearer token.
- Bounded sequential agent runs using upstream discovery, matching, tailoring, and guarded auto-apply. Review-only is the default. Automatic submission is an explicit saved preference.
- Accurate distinction between filled/prepared forms and confirmed submissions.
- Optional Python gateway with authentication, serialized mutations, and SQLite-backed protection against repeated or uncertain submissions.
- Owner-private hosting and a WebMCP navigation tool.

## Run

Use Node 22.13+ (tested with Node 24). `npm ci`, then `npm run dev`. The portable preview uses port 5173. `npm run build` produces the Cloudflare Worker and static assets.

Copy `.env.example` to `.env` and configure the agent URL/token for live mode. See [the connection guide](public/setup.md) for backend setup. The upstream backend and Naukri/model credentials are not included or provisioned.

## Architecture

- `app/page.tsx`: workspace shell, overview, job discovery and navigation.
- `app/workflows.tsx`: resume review, preferences, agent settings, application table, job details.
- `lib/use-career.ts`: sequential execution and outcome updates.
- `lib/career.ts`: API adapter, job normalization, local text extraction and outcome semantics.
- `app/api/career/[...path]/route.ts`: server-only allowlisted proxy.
- `integrations/pilot_gateway.py`: gateway placed in the original Python repository.

## Limits

The deployment starts in clearly labeled demo mode. Live operation requires the Python agent, an AI model, and the user's job-board account. No live applications were sent during development. Runs require the tab to remain open; there is no closed-tab scheduler. This is a private single-owner app, not a multi-tenant service. Company-site browser fallback may require manual completion. Real provider and job-board behavior has not been end-to-end tested without credentials.

Gateway reconciliation is intentionally conservative: it does not automatically retry interrupted submission attempts. Confirm the real job-board outcome before manually removing a corresponding `submissions` row or stale `mutation_lock` row from its SQLite database. Preserve this database across restarts. Use one gateway process per data directory.

## Attribution

The app follows the API contracts and workflows of SNAN-RAZER/career-pilot, inspected from its public repository. No license file was present in the inspected repository. Obtain the appropriate rights before redistributing upstream code; this source package does not include it. Company names in the demo are illustrative and do not assert current job openings or affiliation.
