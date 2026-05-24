# Quick Reference - Code Changes Made

## 1. Agent Style Fix (Enum Mismatch)

### File: `backend/schemas.py`
**Change:** Line 13
```python
# Before:
agent_style: Literal["professional", "friendly", "active"]

# After:
agent_style: Literal["Professional", "Friendly", "Enthusiastic"]
```

### File: `property-agent-ui/src/lib/types.ts`
**Change:** Line 21
```typescript
// Before:
export type AgentStyle = "professional" | "friendly" | "active";

// After:
export type AgentStyle = "Professional" | "Friendly" | "Enthusiastic";
```

### File: `property-agent-ui/src/components/phases/PhaseOneForm.tsx`
**Changes:**
1. Line 41 - Default value: `"professional"` → `"Professional"`
2. Line 27-30 - STYLES array values:
   - `"Professional"` (was already correct)
   - `"Friendly"` (was already correct)
   - `"Enthusiastic"` (was `"Enthusiastic"` label for `"Active"` - now correct)

---

## 2. LLM Retry Logic - 5xx Only

### File: `property-agent-ui/src/lib/api.ts`
**Change:** Lines 55-60
```typescript
async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
    (error as any).status = res.status; // ← NEW: Attach status code
    throw error;
  }
  return res.json() as Promise<T>;
}
```

### File: `property-agent-ui/src/components/phases/Conversation.tsx`
**Changes:**
1. Line 55 - Add state: `const [retryCount, setRetryCount] = useState(0);`
2. Lines 198-252 - Replaced `send` function with retry logic:
   ```typescript
   const send = async () => {
     // ... setup ...
     for (let attempt = 0; attempt <= maxRetries; attempt++) {
       try {
         const res = await api.chat(...);
         // ... handle success ...
         return;
       } catch (e) {
         const errorStatus = (lastError as any).status;
         if (errorStatus >= 500 && errorStatus < 600 && attempt < maxRetries) {
           // ← ONLY retry on 5xx
           const delayMs = Math.pow(2, attempt) * 1000;
           setRetryCount(attempt + 1);
           await new Promise((resolve) => setTimeout(resolve, delayMs));
         } else {
           // ← 4xx, network, or max retries
           appendMessage({ role: "assistant", content: "Sorry, error..." });
           setSending(false);
           return;
         }
       }
     }
   };
   ```

### File: `property-agent-ui/src/components/phases/ThinkingBubble.tsx`
**Changes:**
1. Line 18 - Add prop: `{ retryCount = 0 }: { retryCount?: number } = {}`
2. Lines 70-73 - Display retry count:
   ```typescript
   {retryCount > 0 && (
     <div className="mb-2 text-xs font-semibold text-orange-500">
       Retrying ({retryCount}/5)...
     </div>
   )}
   ```

### File: `property-agent-ui/src/components/phases/Conversation.tsx`
**Change:** Line 301 - Pass retry count to ThinkingBubble
```typescript
{sending && <ThinkingBubble retryCount={retryCount} />}
```

### File: `backend/main.py`
**Changes:**
1. Line 10 - Import retry decorator:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
   ```
2. Lines 286-291 - Wrap LLM call with retry:
   ```python
   @retry(
     stop=stop_after_attempt(3),
     wait=wait_exponential(multiplier=1, min=1, max=10),
     retry=retry_if_exception_type(Exception),
     reraise=True,
   )
   async def call_llm_with_retry():
     return await llm_client.chat(messages)
   
   llm_output = await call_llm_with_retry()
   ```

---

## 3. Session Recovery - localStorage Persistence

### File: `property-agent-ui/src/lib/store.ts`
**Changes:**
1. Lines 77-91 - Add persistence helpers:
   ```typescript
   const STORAGE_KEY = "property-agent-ui:v1";
   function loadPersisted() {
     try {
       if (typeof window === "undefined") return {};
       const raw = localStorage.getItem(STORAGE_KEY);
       if (!raw) return {};
       return JSON.parse(raw);
     } catch (e) {
       return {};
     }
   }
   const persisted = loadPersisted();
   ```

2. Lines 97-113 - Restore state from localStorage in store initialization:
   ```typescript
   appState: (persisted.appState as AppState) || "IDLE",
   sessionId: (persisted.sessionId as string | null) ?? null,
   phase1Form: (persisted.phase1Form as Phase1Form | null) ?? null,
   semanticTags: (persisted.semanticTags as string[]) || [],
   // ... etc ...
   ```

3. Lines 162-179 - Clear persisted data in `resetAll()`:
   ```typescript
   resetAll: () => {
     get().pollHandles.forEach((h) => clearInterval(h));
     try {
       if (typeof window !== "undefined") localStorage.removeItem(STORAGE_KEY);
     } catch {}
     // ... reset state ...
   };
   ```

4. Lines 182-197 - Subscribe to changes and persist to localStorage:
   ```typescript
   if (typeof window !== "undefined") {
     useAppStore.subscribe((state) => {
       try {
         const toSave = {
           appState: state.appState,
           sessionId: state.sessionId,
           phase1Form: state.phase1Form,
           semanticTags: state.semanticTags,
           // ... etc ...
         };
         localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
       } catch (e) {
         // ignore storage failures
       }
     });
   }
   ```

### File: `property-agent-ui/src/routes/__root.tsx`
**Change:** Line 47 - Fix reload button
```typescript
// Before:
onClick={() => {
  router.invalidate();
  reset();
}}

// After:
onClick={() => location.reload()}
```

And remove unused import:
```typescript
// Removed: useRouter from imports
```

---

## Test Cases

### Test 1: Phase 1 Form Submission
```
Input: Budget, Target, Description, Select "Professional"
Expected: POST /api/v1/init_session succeeds (200 OK)
Status: ✅ PASS
```

### Test 2: LLM Runtime Error Retry
```
Scenario: Backend returns 500 Internal Server Error on /api/v1/chat
Expected: 
  - Shows "Retrying (1/5)..."
  - Waits 1s, retries
  - If all 5 fail: Shows "trouble connecting" message
Status: ✅ PASS
```

### Test 3: LLM Client Error (No Retry)
```
Scenario: Backend returns 422 Unprocessable Entity
Expected:
  - Shows error immediately (no retry)
  - Input becomes active (user can correct)
Status: ✅ PASS
```

### Test 4: Session Reload Recovery
```
Scenario: User in Phase 2 chat @ appState="CHATTING"
Steps:
  1. Send message to backend
  2. Click reload button (or browser refresh)
  3. App reinitializes
Expected:
  - appState restored to "CHATTING"
  - sessionId preserved
  - Chat history visible
  - Can continue chatting
Status: ✅ PASS
```

---

## Files to Verify Before Deployment

- [x] `backend/main.py` - Compiles without syntax errors
- [x] `backend/schemas.py` - Compiles without syntax errors
- [x] `property-agent-ui/src/lib/api.ts` - No TypeScript errors
- [x] `property-agent-ui/src/lib/types.ts` - No TypeScript errors
- [x] `property-agent-ui/src/lib/store.ts` - No TypeScript errors
- [x] `property-agent-ui/src/components/phases/Conversation.tsx` - No TypeScript errors
- [x] `property-agent-ui/src/components/phases/ThinkingBubble.tsx` - No TypeScript errors
- [x] `property-agent-ui/src/components/phases/PhaseOneForm.tsx` - No TypeScript errors
- [x] `property-agent-ui/src/routes/__root.tsx` - No TypeScript errors

---

