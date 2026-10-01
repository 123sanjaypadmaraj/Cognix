# Autopilot status

Project: Club Hub (Next.js 16 + Supabase), source in `club-hub/`. All paths below are relative to `club-hub/`.
Note: `club-hub/AGENTS.md` warns that this Next.js version has breaking changes; read the relevant guide in `node_modules/next/dist/docs/` before writing code.

## Task list

- [done] **Add unit tests for the pure lib helpers (stats, csv, format)**
  Add Vitest as a devDependency with an `npm test` script (`vitest run`), and write tests in `src/lib/__tests__/` covering `stats.ts` (`parseRange`, `inRange` excluding draft/cancelled and out-of-range events, `totals` attendance rate using past events only and rating weighted by feedback_count, `monthly` gap-filling, `trend` incl. prev=0 cases), `csv.ts` (quoting, formula-injection prefix, BOM in `csvResponse`) and `format.ts` (`fromLocalInput`/`toLocalInput` IST round-trip, `safeUrl` rejecting non-http schemes, `int`/`str`). Done when `npm test` passes; use `vi.useFakeTimers()`/`vi.setSystemTime` for date-dependent cases.

- [pending] **Add a CI workflow running lint, typecheck and tests**
  Create `club-hub/.github/workflows/ci.yml` (the README tells users to push this folder as its own GitHub repo, so treat `club-hub/` as the repo root) that on push/PR to `main` runs `npm ci`, `npm run lint`, `npx tsc --noEmit`, and `npm test` (if the test task above is done; otherwise omit that step) on Node 20. Supply dummy `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` env values; do not run `next build` or any deploy step.

- [pending] **Add error, not-found and loading boundaries**
  Add `src/app/error.tsx` (client component with a friendly message and a "Try again" button calling `reset()`), `src/app/not-found.tsx` (links back to `/` and `/events`), and `src/app/dashboard/loading.tsx` (simple skeleton using existing `card` styles). Done when an unknown `/clubs/does-not-exist` shows the custom 404 and a thrown error in a dashboard page renders the error boundary instead of the default Next screen.

- [pending] **Let signed-in users change their own password**
  Admin hands leads a temporary password (README "Day to day") but there is no way to change it. Add `/dashboard/account` page with current password + new password (min 8 chars) + confirm; the server action re-verifies the current password via `signInWithPassword` for the profile's email, then calls `supabase.auth.updateUser({ password })`, redirecting with the existing `?ok=`/`?error=` flash pattern. Link it from `DashNav`.

- [pending] **Surface errors from silent dashboard mutations**
  In `src/app/dashboard/actions.ts`, `toggleAttendanceAction`, `removeParticipantAction`, `setMemberStatusAction`, `removeMemberAction`, `deleteAnnouncementAction`, `assignLeadAction` and `unassignLeadAction` ignore the Supabase `error`, and `createLeadAction` ignores errors from the profile update and `club_leads` insert. Check each error and redirect back with the existing `go(path, "error", msg)` helper (keep success behavior unchanged); for `createLeadAction`, report "Account created but club assignment failed" if the `club_leads` insert fails.

- [done] **Parse member CSV imports with a real CSV parser**
  `importMembersAction` splits each line on `,`, so quoted fields like `"Shah, Riya"` or a department containing a comma shift every column. Add a small RFC 4180-style `parseCsv(text): string[][]` to `src/lib/csv.ts` (handles quoted fields, escaped `""`, CRLF) with no new dependency, use it in `importMembersAction`, and skip rows whose email (when present) fails the existing `EMAIL` regex, reporting the skipped count in the success message. Add unit tests for `parseCsv` if the test setup exists.

- [pending] **Add "Add to calendar" (.ics) download for public events**
  Add a route handler `src/app/events/[id]/calendar/route.ts` returning a single-VEVENT `text/calendar` file (UID = event id, DTSTART/DTEND in UTC, default end = start + 1h when `ends_at` is null, SUMMARY, LOCATION = venue, DESCRIPTION incl. the public event URL, proper text escaping and 75-octet line folding) for events visible to anon (RLS already hides drafts; return 404 when not found or id is not a UUID). Link it from `src/app/events/[id]/page.tsx` as "Add to calendar".

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
