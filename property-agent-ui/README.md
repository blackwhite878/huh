# Property Agent UI

A stylish, minimalistic, futuristic UI shell for a conversational property-search
agent. Built with **TanStack Start**, **React 19**, **Zustand**, **Tailwind CSS**,
and **shadcn/ui**. The UI is driven by a state machine that mirrors the backend
contract in `frontend.md` / `backend(1).md`.

> The current build is a **UI shell** — no real backend required. A local
> heuristic fallback derives semantic tags from the Phase 1 description so every
> screen is reachable. Plug in your FastAPI backend by setting `VITE_API_BASE_URL`.

---

## 1. Quick start (local)

```bash
# Install deps (bun recommended; npm/pnpm also work)
bun install

# Dev server (http://localhost:5173 by default)
bun run dev

# Production build + preview
bun run build
bun run start
```

Node 20+ is required. Replace `bun` with `npm` / `pnpm` if preferred.

---

## 2. Environment variables

Create a `.env` (or `.env.local`) in the project root. All client-side vars
**must** be prefixed `VITE_`.

| Variable                | Default     | Purpose                                                                  |
| ----------------------- | ----------- | ------------------------------------------------------------------------ |
| `VITE_API_BASE_URL`     | `/api/v1`   | Base URL of the FastAPI backend (e.g. `https://api.example.com/api/v1`). |
| `VITE_TRANSPORT`        | `polling`   | `sse` to prefer Server-Sent Events; auto-falls back to 3 s polling.      |

Example `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_TRANSPORT=sse
```

---

## 3. Backend wiring

All HTTP calls live in **`src/lib/api.ts`** — change endpoints in **one place**.
Endpoints match the backend spec exactly:

| Method | Path                                | Used by                                |
| ------ | ----------------------------------- | -------------------------------------- |
| POST   | `/init_session`                     | `PhaseOneForm`                         |
| GET    | `/session_ready/:id`                | `SemanticAligning` (poll)              |
| GET    | `/session_ready/:id/stream`         | `SemanticAligning` (SSE)               |
| POST   | `/chat`                             | `Conversation`                         |
| GET    | `/search_status/:id`                | `Searching` (poll)                     |
| GET    | `/search_status/:id/stream`         | `Searching` (SSE)                      |
| POST   | `/next_batch`                       | `ResultsBatch`                         |
| POST   | `/reject_single`                    | `ResultsBatch`                         |
| POST   | `/reject_all`                       | `ResultsBatch`                         |
| POST   | `/resolve_action`                   | `ActionRequired`                       |
| POST   | `/update_requirements`              | `Tier3NoResult`                        |

### To swap the local fallback for the real backend:

1. Set `VITE_API_BASE_URL` to your FastAPI base.
2. (Optional) Set `VITE_TRANSPORT=sse` and expose SSE routes at
   `/session_ready/:id/stream` and `/search_status/:id/stream`.
3. Remove the timeout fallback in `src/components/phases/SemanticAligning.tsx`
   (the `setTimeout(...) → deriveTagsFromDescription` block) once your
   `/session_ready` endpoint reliably returns `status: "ready"`.

CORS: the backend must allow the frontend origin and the `Content-Type` header.

---

## 4. Project structure

```
src/
├── routes/
│   ├── __root.tsx          # Shell, providers, fonts
│   └── index.tsx           # State-machine view switcher (the only page)
├── components/
│   ├── AppShell.tsx        # Header + aurora background
│   ├── DevPanel.tsx        # Floating dev-only state switcher (bottom-right)
│   ├── StateChip.tsx       # Current-state badge
│   ├── phases/             # ONE file per app state
│   │   ├── PhaseOneForm.tsx       # IDLE
│   │   ├── SemanticAligning.tsx   # SEMANTIC_ALIGNING
│   │   ├── ProfilingComplete.tsx  # PROFILING_COMPLETE
│   │   ├── Conversation.tsx       # CHATTING / PENDING_CONFIRMATION
│   │   ├── Searching.tsx          # SEARCHING
│   │   ├── ResultsBatch.tsx       # BATCH_1_DISPLAY / BATCH_2_DISPLAY / ALL_REJECTED
│   │   ├── ActionRequired.tsx     # ACTION_REQUIRED_UI
│   │   └── Tier3NoResult.tsx      # TIER3_NO_RESULT
│   └── ui/                 # shadcn/ui primitives
├── lib/
│   ├── store.ts            # Zustand store — single source of truth
│   ├── api.ts              # HTTP / SSE client (edit endpoints here)
│   ├── types.ts            # All API + state types
│   └── semantic.ts         # Local fallback: text → exclusion tags
└── styles.css              # OKLCH design tokens, glass effects, aurora
```

### State machine

Defined in `src/lib/types.ts → AppState`. The router (`src/routes/index.tsx`)
renders exactly one phase component per state. To add a new state:

1. Add it to the `AppState` union in `types.ts`.
2. Add a case in the switch in `routes/index.tsx`.
3. Build a new component in `components/phases/`.

### Dev panel

A floating panel (bottom-right, dev builds only) lets you jump to any state
without a backend and seed sample property data. Remove `<DevPanel />` from
`AppShell.tsx` before production.

---

## 5. Common changes

| You want to…                          | Edit…                                                  |
| ------------------------------------- | ------------------------------------------------------ |
| Change colors / theme                 | `src/styles.css` (OKLCH tokens — `--primary`, etc.)    |
| Change fonts                          | `src/routes/__root.tsx` (Google Fonts link)            |
| Add/rename Phase 1 fields             | `src/lib/types.ts` → `Phase1Form` + `PhaseOneForm.tsx` |
| Adjust local tag-derivation rules     | `src/lib/semantic.ts` (`RULES` array)                  |
| Change polling interval               | `src/lib/api.ts` (`pollLoop(..., 3000)`)               |
| Add a new API endpoint                | `src/lib/api.ts` (extend the `api` object)             |
| Tweak result-card layout              | `src/components/phases/ResultsBatch.tsx`               |
| Disable the dev panel                 | Remove `<DevPanel />` from `src/components/AppShell.tsx` |

---

## 6. Deployment

The template targets edge runtimes (Cloudflare Workers via `wrangler.jsonc`),
but a standard Node host works too:

```bash
bun run build      # outputs .output/
bun run start      # serves the build
```

For static hosting, use any TanStack Start adapter and point your reverse
proxy at the produced server entry. Set `VITE_API_BASE_URL` at **build time**
(it is inlined by Vite).

---

## 7. Tech stack

- **TanStack Start v1** (React 19 + Vite 7, file-based routing)
- **Zustand** — state machine store
- **Tailwind CSS v4** + **shadcn/ui** — styling primitives
- **lucide-react** — icons
- **TypeScript strict** mode

Design direction: *Cloud White* — clean SaaS with subtle aurora gradients,
glassmorphism, OKLCH color tokens, Inter + JetBrains Mono.

---

## 8. License

Private / internal. Add your license here before publishing.
