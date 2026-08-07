# Narrative Therapy Chatbot — Design & Build Plan

A plan for building a chatbot that uses Narrative Therapy techniques (White & Epston) to help
users explore problems as separate from themselves and re-author their personal stories.

> **Important framing:** this is a *well-being / self-reflection companion*, not a licensed
> therapist. That framing drives several design decisions below (safety layer, disclaimers,
> escalation paths, clinician review).

---

## 1. What "Narrative Therapy techniques" means for a chatbot

Narrative Therapy has a small set of well-defined conversational moves. Each one can be encoded
as explicit behavior in the model's system prompt and tracked as conversation state:

| Technique | What the bot does |
|---|---|
| **Externalizing** | Talks about the problem as separate from the person ("the Anxiety", not "your anxiety problem"). Invites the user to *name* the problem. |
| **Mapping effects** | Asks how the named problem affects the user's life, relationships, work, self-image — and how the user affects *it*. |
| **Deconstruction** | Gently questions where the problem's "rules" came from (family, culture, workplace norms) so they stop feeling like fixed truths. |
| **Unique outcomes** | Hunts for exceptions — moments the problem was weaker or absent — and asks what the user did to make that happen. |
| **Re-authoring** | Builds a preferred story from those exceptions: values, skills, intentions the exceptions reveal. |
| **Re-membering** | Brings in supportive figures ("Who wouldn't be surprised you managed that?"). |
| **Therapeutic documents** | Generates a written summary/letter at session end capturing the externalized problem, the unique outcomes, and the emerging preferred story. This is a signature Narrative Therapy practice and a natural fit for an LLM. |

The therapist stance is as important as the moves: **curious, not-knowing, non-diagnostic,
person-as-expert**. The bot never labels, diagnoses, or advises; it asks questions.

---

## 2. Architecture

```
┌────────────┐     ┌───────────────────────────────────────────┐
│  Chat UI   │ ──► │  Backend (FastAPI)                        │
│ (web/app)  │ ◄── │                                           │
└────────────┘     │  1. Safety screen (every user message)    │
                   │  2. Conversation engine (Claude API)      │
                   │     - system prompt = NT stance + moves   │
                   │     - phase state machine                 │
                   │  3. Session memory (per-user store)       │
                   │  4. Document generator (session letters)  │
                   └───────────────────────────────────────────┘
```

### 2.1 Conversation engine — one Claude call per turn

Use the Anthropic SDK with `claude-opus-5` (thinking is on by default; use
`output_config={"effort": "low"}` or `"medium"` for chat-latency responses). Stream responses
for a natural chat feel.

The core of the product is the **system prompt**. Sketch:

```
You are a reflective conversation companion trained in the practices of Narrative
Therapy. You are NOT a therapist and never present yourself as one.

Stance:
- The person is the expert on their own life. You are curious, never knowing-better.
- The person is never the problem; the problem is the problem.
- Ask one question at a time. Short turns. Never lecture, diagnose, or advise.

Practices (use when the conversation naturally allows, not as a rigid script):
1. EXTERNALIZE: restate problems as external ("the Worry", "the Pressure") and invite
   the person to give the problem their own name for it.
2. MAP EFFECTS: explore how the problem affects their life — and where they push back.
3. DECONSTRUCT: ask where the problem's rules and standards came from.
4. UNIQUE OUTCOMES: listen for exceptions; when you hear one, slow down and explore it.
5. RE-AUTHOR: connect exceptions into a story about their values, skills, and hopes.
6. RE-MEMBER: ask about people who would recognize and support that preferred story.

Boundaries:
- If the person mentions self-harm, harm to others, abuse, or acute crisis, stop the
  narrative work and follow the crisis protocol given to you in context.
- Regularly remind (briefly, naturally) that you are a reflection tool, not therapy.
```

### 2.2 Phase tracking (lightweight state machine)

Don't force the model through a rigid script — narrative conversations wander. Instead track a
*current phase* (`joining → externalizing → mapping → deconstruction → unique_outcomes →
re_authoring → closing`) and inject it as a **mid-conversation system message** each turn, e.g.
"The conversation is in the externalizing phase; a problem name has not yet emerged." This
keeps the cached prompt prefix intact (cheaper + faster) while steering gently.

Phase detection can be done cheaply: a structured-output call on `claude-haiku-4-5` after each
turn classifying `{phase, problem_name?, unique_outcomes: [...], risk_flags: [...]}` — this
doubles as the memory-extraction step.

### 2.3 Safety layer (non-negotiable)

- **Every** inbound message passes a fast risk screen (a small structured-output classification
  call, plus a keyword net as a backstop) for self-harm, harm to others, abuse, psychosis,
  medical emergency.
- On a flag: the narrative flow is suspended; the bot responds with a warm, scripted (not
  fully generated) crisis message including region-appropriate hotline info, and the session
  is marked. Scripted, because you want this exact behavior every time.
- Persistent product-level disclaimers: onboarding screen, footer, and periodic in-chat
  reminders that this is not therapy or medical care.
- Log flags for human review if you ever operate this beyond personal use.

### 2.4 Memory across sessions

Narrative work is longitudinal — the re-authored story is built over weeks. Store per user:

- the externalized problem name(s) and the user's own metaphors,
- collected unique outcomes (verbatim quotes where possible),
- emerging preferred-story themes (values, skills, commitments),
- people mentioned in re-membering conversations.

A simple JSON/SQLite store is enough for a prototype. At session start, inject a short
"previously in your story…" context block so the bot continues rather than restarts.

### 2.5 Therapeutic documents

At session end (user-triggered "wrap up" button or natural close), make a dedicated Claude call
that turns the transcript + memory into a short **letter to the user** in classic NT style:
documenting the problem's tactics, the exceptions the user demonstrated, and the preferred
story taking shape. Offer it as markdown/PDF download and store it in the user's history.
This is the feature users will remember.

---

## 3. Tech stack (prototype)

| Layer | Choice | Why |
|---|---|---|
| Model | `claude-opus-5` (conversation), `claude-haiku-4-5` (classification/extraction) | Quality where it matters, cheap where it doesn't |
| SDK | `anthropic` (Python) | Streaming, structured outputs (`messages.parse` + Pydantic), prompt caching built in |
| Backend | FastAPI + SSE/WebSocket | Simple streaming chat backend |
| Frontend | Any chat UI (React, or even Streamlit/Gradio for v0) | Fastest path to something usable |
| Storage | SQLite (sessions, memory, letters) | Zero-ops for a prototype |

Prompt caching: put the long, stable system prompt behind a `cache_control` breakpoint; append
per-turn phase guidance as a mid-conversation `role: "system"` message so the cache never
invalidates.

---

## 4. Build order

1. **v0 — the conversation:** system prompt + streaming chat loop in a notebook/CLI. Iterate on
   the prompt until the externalizing/unique-outcome moves feel natural. This is 80% of the
   product quality and costs nothing to iterate on.
2. **v1 — safety:** risk screen + scripted crisis responses + disclaimers.
3. **v2 — state & memory:** phase tracker, per-user memory, "previously…" injection.
4. **v3 — documents:** session letters.
5. **v4 — UI & polish:** real frontend, auth, letter history.

---

## 5. Evaluation & ethics

- Build a **conversation eval set**: scripted user personas (a stressed student, someone in
  grief, an edge case that should trigger the crisis path) and review transcripts against a
  rubric: Did it externalize? Did it avoid advice/diagnosis? Did it catch the unique outcome?
  Did the crisis path fire?
- If this goes beyond personal experimentation, get a practicing narrative therapist to review
  prompts and sample transcripts, and consult local regulations on digital mental-health tools.
- Be transparent in the UI about data storage and give users a way to delete their story data —
  this material is intensely personal.
