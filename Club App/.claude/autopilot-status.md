# Autopilot status

Project: Club Hub (Next.js 16 + Supabase), source in `club-hub/`. All paths below are relative to `club-hub/`.
Note: `club-hub/AGENTS.md` warns that this Next.js version has breaking changes; read the relevant guide in `node_modules/next/dist/docs/` before writing code.

## Task list

- [done] **Add unit tests for the pure lib helpers (stats, csv, format)**
  Add Vitest as a devDependency with an `npm test` script (`vitest run`), and write tests in `src/lib/__tests__/` covering `stats.ts` (`parseRange`, `inRange` excluding draft/cancelled and out-of-range events, `totals` attendance rate using past events only and rating weighted by feedback_count, `monthly` gap-filling, `trend` incl. prev=0 cases), `csv.ts` (quoting, formula-injection prefix, BOM in `csvResponse`) and `format.ts` (`fromLocalInput`/`toLocalInput` IST round-trip, `safeUrl` rejecting non-http schemes, `int`/`str`). Done when `npm test` passes; use `vi.useFakeTimers()`/`vi.setSystemTime` for date-dependent cases.

- [done] **Add a CI workflow running lint, typecheck and tests**
  Create `club-hub/.github/workflows/ci.yml` (the README tells users to push this folder as its own GitHub repo, so treat `club-hub/` as the repo root) that on push/PR to `main` runs `npm ci`, `npm run lint`, `npx tsc --noEmit`, and `npm test` (if the test task above is done; otherwise omit that step) on Node 20. Supply dummy `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` env values; do not run `next build` or any deploy step.

- [blocked] **Add error, not-found and loading boundaries**
  Add `src/app/error.tsx` (client component with a friendly message and a "Try again" button calling `reset()`), `src/app/not-found.tsx` (links back to `/` and `/events`), and `src/app/dashboard/loading.tsx` (simple skeleton using existing `card` styles). Done when an unknown `/clubs/does-not-exist` shows the custom 404 and a thrown error in a dashboard page renders the error boundary instead of the default Next screen.

- [pending] **Let signed-in users change their own password**
  Admin hands leads a temporary password (README "Day to day") but there is no way to change it. Add `/dashboard/account` page with current password + new password (min 8 chars) + confirm; the server action re-verifies the current password via `signInWithPassword` for the profile's email, then calls `supabase.auth.updateUser({ password })`, redirecting with the existing `?ok=`/`?error=` flash pattern. Link it from `DashNav`.

- [blocked] **Surface errors from silent dashboard mutations**
  In `src/app/dashboard/actions.ts`, `toggleAttendanceAction`, `removeParticipantAction`, `setMemberStatusAction`, `removeMemberAction`, `deleteAnnouncementAction`, `assignLeadAction` and `unassignLeadAction` ignore the Supabase `error`, and `createLeadAction` ignores errors from the profile update and `club_leads` insert. Check each error and redirect back with the existing `go(path, "error", msg)` helper (keep success behavior unchanged); for `createLeadAction`, report "Account created but club assignment failed" if the `club_leads` insert fails.

- [done] **Parse member CSV imports with a real CSV parser**
  `importMembersAction` splits each line on `,`, so quoted fields like `"Shah, Riya"` or a department containing a comma shift every column. Add a small RFC 4180-style `parseCsv(text): string[][]` to `src/lib/csv.ts` (handles quoted fields, escaped `""`, CRLF) with no new dependency, use it in `importMembersAction`, and skip rows whose email (when present) fails the existing `EMAIL` regex, reporting the skipped count in the success message. Add unit tests for `parseCsv` if the test setup exists.

- [pending] **Add "Add to calendar" (.ics) download for public events**
  Add a route handler `src/app/events/[id]/calendar/route.ts` returning a single-VEVENT `text/calendar` file (UID = event id, DTSTART/DTEND in UTC, default end = start + 1h when `ends_at` is null, SUMMARY, LOCATION = venue, DESCRIPTION incl. the public event URL, proper text escaping and 75-octet line folding) for events visible to anon (RLS already hides drafts; return 404 when not found or id is not a UUID). Link it from `src/app/events/[id]/page.tsx` as "Add to calendar".

- [pending] **Add participant search to the event check-in list**
  On `src/app/dashboard/clubs/[slug]/events/[id]/page.tsx`, add a GET form (`?q=`) above the participants table that filters registrations by case-insensitive substring match on name, email or roll_no (do the filtering in JS on the already-fetched list so the Stat counts stay totals; show "Showing N of M" and a "Clear" link when `q` is set). Preserve `q` across check-in toggles: pass it through to `toggleAttendanceAction`/`removeParticipantAction` redirects, or append it to the redirect path, so a lead checking people in at the door does not lose the filter after every click.

- [pending] **Add a "Duplicate event" action for leads**
  Add `duplicateEventAction(slug, eventId)` in `src/app/dashboard/actions.ts` that copies an event the lead can access (title suffixed " (copy)", same category/venue/description/capacity/external URLs, `starts_at`/`ends_at` shifted +7 days, `status` = draft, `registration_open` = true, no registrations/feedback copied), then redirects to the new event's manage page with `?ok=Event duplicated as draft`. Add a "Duplicate" button next to the existing public-page links on the manage-event page. Recurring weekly club meetups are the main use case.

- [pending] **Add category and club filters to the public events page**
  `src/app/events/page.tsx` shows every club's events with no filtering. Accept `?category=` and `?club=<slug>` searchParams, apply them as `.eq("category", …)` and an `.eq("club_id", …)` filter (resolve the slug to an id first; ignore unknown values), and render a row of filter links/chips (categories taken from the `EventForm` category options, clubs from active clubs) with an "All" reset. Also show events that have started but not yet ended (`ends_at > now`) under "Upcoming" with a "Happening now" badge instead of under "Recent".

- [pending] **Add share-friendly metadata to public event and club pages**
  Extend `generateMetadata` in `src/app/events/[id]/page.tsx` and `src/app/clubs/[slug]/page.tsx` to return `description` (event: date in IST via `fmtDateTime` + venue + first ~150 chars of description; club: its description/tagline) and matching `openGraph` `{ title, description, type }` fields, so links shared in WhatsApp/Instagram show a useful preview. Set `metadataBase` in the root layout from `process.env.NEXT_PUBLIC_SITE_URL` when it is set (add it to `.env.example` as optional). Do not generate OG images.

## Run log

### 2026-10-01 — planner run (initial)
- Surveyed: `club-hub/README.md`, `AGENTS.md`/`CLAUDE.md`, `package.json`, `.env.example`, `.gitignore`, `next.config.ts`, `supabase/schema.sql`, `src/proxy.ts`, all of `src/lib/`, the three server-action files, public event page, root layout, login page, and the route tree. `club-hub/` has no commits of its own (untracked inside a parent repo at `C:\Users\padma\Downloads` whose history belongs to an unrelated project), so there was no commit history to read. No TODO/FIXME/XXX markers found. No status file existed, so I created this one.
- Added "unit tests for lib helpers": no test runner or tests exist at all, and `stats.ts` holds the metric math the admin dashboard depends on.
- Added "CI workflow": there is no CI. Put it under `club-hub/.github/` because the README treats that folder as the repo to push.
- Added "error/not-found/loading boundaries": the app has none, so failed Supabase calls (e.g. `getEventStats` throws) currently show the default Next error screen.
- Added "change own password": leads get admin-issued temporary passwords and can't rotate them. This is a security gap.
- Added "surface silent mutation errors": several actions throw away Supabase errors, so a failed check-in or delete looks like it worked.
- Added "real CSV parser for member import": the naive `split(",")` corrupts rows that contain quoted commas.
- Added ".ics calendar download": a cheap feature that students would use and that fits the public-event flow.
- Not added: a honeypot or rate-limit on the public register/feedback forms. Abuse isn't a demonstrated problem yet at roughly 20 clubs, and a real rate-limit needs infrastructure the project doesn't have. Revisit if spam shows up.
- Not added: the capacity race in `event_accepts_registration` (two concurrent inserts can both pass the count check). The fix is a locking trigger, and that is low impact at this scale.
- Not added: an anti-impersonation check for feedback, i.e. requiring the email to be registered. The current open-feedback behavior is documented in the README, so it looks deliberate.

### 2026-10-01 — autopilot run
- Branch `autopilot/tests-and-fixes` (created in the parent repo at `C:\Users\padma\Downloads`; only `Club App/` files committed).
- Done: unit tests (vitest@^3 — vitest 5 fails ERESOLVE against `@types/node@^20`; 21 tests across csv/format/stats) and the real CSV parser (`parseCsv`, used in `importMembersAction`, skips rows with invalid email and reports the count; has unit tests).
- Checks: `npm test` 21/21 pass, `npx tsc --noEmit` clean, `npm run lint` clean. `next build` not run.
- Not pushed: awaiting user confirmation (parent repo's remote belongs to an unrelated project).
- Next: CI workflow (tests now exist; use Node 20), error/not-found/loading boundaries, silent mutation errors, password change, .ics.

### 2026-10-01 — planner run (second)
- Surveyed: the full status file, `club-hub/README.md`, `package.json` (vitest now present), the route tree, `src/app/actions.ts`, `src/app/events/page.tsx`, `src/app/events/[id]/page.tsx`, the dashboard manage-event page, the list of exports in `src/app/dashboard/actions.ts`, and the root layout. Git history for `club-hub/` is a single autopilot commit (bf4e9de). No TODO/FIXME/XXX markers.
- Added "participant search in check-in list": leads check people in at the door from an unfiltered list. That is slow for large events and is a core workflow from the README.
- Added "Duplicate event": clubs run recurring events, and every one is currently re-entered by hand in `EventForm`.
- Added "category/club filters on /events": the public page merges every club's events with no way to narrow them down. It also lists in-progress events under "Recent", which is wrong.
- Added "share-friendly metadata": event links are shared on social apps, but `generateMetadata` only sets a title. There is no description and no OG data.
- Not added: tests for server actions. They need Supabase mocking, and that work belongs after the pending "surface silent mutation errors" task changes those actions.
- Not added: pagination for members (limit 1000) and recent events (limit 24). Those limits are adequate at roughly 20 clubs.
- Five original tasks are still pending, so I kept this batch to four small, concrete items.

### 2026-10-01 — autopilot run 2 (loop wakeup)
- Picked up: CI workflow, error/not-found/loading boundaries, silent mutation errors.
- Done: CI workflow  (lint, tsc, test on Node 20; ran each step locally, cannot run Actions here).
- Blocked (code written; tsc, lint and 21 unit tests pass, but no automated test covers the area): boundaries — needs manual check that  shows the 404 and a thrown dashboard error shows the boundary; per Next 16 docs  uses the  prop (not ). Silent mutation errors — needs manual check of the ?error= flash on each action; all listed actions now check errors.
- Not pushed (see earlier note on remote). Next: password change, .ics, then the 4 new planner tasks.
