# Frontend Standards

## Stack

- **Framework:** Next.js 15 (App Router, TypeScript strict)
- **Styling:** Tailwind CSS (utility classes only, no custom CSS files)
- **Components:** shadcn/ui as base component library
- **State:** React `useState` / `useReducer` for local state; no global state manager in MVP
- **Data fetching:** Native `fetch` with React Server Components where possible; `useSWR` for polling
- **Real-time:** Supabase Realtime (WebSocket) for RPA job completion notifications
- **Auth:** `@supabase/auth-helpers-nextjs` — server-side session handling

## MVP component structure

The MVP frontend is minimal by design. It is a conversational interface, not a dashboard.

```
app/
  (auth)/
    login/page.tsx
    register/page.tsx
  dashboard/
    page.tsx               # Entry point after login
  proceso/
    p04/
      page.tsx             # Main P04 flow container
components/
  chat/
    ChatInterface.tsx      # Main conversation UI with the agent
    MessageBubble.tsx      # Renders text + structured agent messages
  facturas/
    FacturaUploader.tsx    # Drag-and-drop PDF upload
    FacturaReviewer.tsx    # Editable table of OCR-extracted invoice data
  resultado/
    ResumenIVA.tsx         # Structured M303 calculation summary
  confirmacion/
    ConfirmacionModal.tsx  # THE critical click — user confirms presentation
  ui/                      # shadcn/ui components (do not modify)
lib/
  supabase/
    client.ts              # Browser Supabase client
    server.ts              # Server Supabase client (RSC/Server Actions)
  api/
    p04.ts                 # Typed fetch wrappers for P04 endpoints
```

## Critical UI/UX rules

- **ConfirmacionModal is the most important component.** It must show: period, ejercicio, total IVA a ingresar/compensar, IBAN (last 4 digits), due date. The confirm button must require a deliberate click — never auto-submit. Log timestamp and user_id on confirmation.
- **ResumenIVA shows numbers in human language**, not raw casilla codes. Use "IVA que has cobrado a tus clientes" not "Casilla 27". The raw casilla values appear as secondary info only.
- **FacturaReviewer must show OCR confidence.** Fields with confidence < 0.8 highlight in amber. User must explicitly confirm or correct them before proceeding.
- **RPA progress is async.** After user confirms, show a progress indicator with status from Supabase Realtime. Never block the UI waiting for the RPA to finish — it can take 2-5 minutes.
- **Never show fiscal amounts without context.** Always pair amounts with the period they belong to (e.g., "2.340 € — 2T 2026").

## TypeScript conventions

- **Strict mode always on.** No `any`, no `// @ts-ignore`.
- **All API responses typed.** Types in `lib/types/p04.ts` matching the FastAPI Pydantic models exactly.
- **No implicit returns in async functions.** Every async function has explicit return type annotation.
- **Zod for form validation.** Any user input validated client-side with Zod before sending to API.

## Component conventions

- **Functional components only.** No class components.
- **Props interfaces** named `<ComponentName>Props`, defined in the same file.
- **Server Components by default.** Add `"use client"` only when needed (event handlers, hooks, Realtime).
- **Loading states always handled.** Every data-fetching component has a loading skeleton.
- **Error states always handled.** Every component that can fail has an error boundary or fallback UI.

## Styling conventions

- Tailwind utility classes only — no `style={{}}` props, no CSS modules, no global CSS (except `globals.css` for Tailwind base).
- Color palette follows the fiscal domain: use green for positive results (a ingresar but manageable), amber for warnings (results requiring attention), red for errors or blocking issues.
- Mobile-first: all components work at 375px width minimum. The autónomo may use this on their phone.

## Testing

- **Playwright** for E2E tests. Test files in `e2e/`.
- Cover the full happy path: login → upload invoices → review OCR → see summary → confirm → receive justificante notification.
- Cover the critical negative: user clicks cancel in ConfirmacionModal → process reverts to pending, no RPA job enqueued.
- No unit tests for presentational components — E2E covers the critical paths.

## Environment variables

```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_URL           # FastAPI backend URL
```
