# Narrative Therapy Chatbot — v0

A streaming CLI prototype of the reflection companion described in
[`docs/narrative-therapy-chatbot-design.md`](../docs/narrative-therapy-chatbot-design.md).

> This is a reflection tool, **not therapy or medical care**. If you or someone you
> know is in crisis, contact local emergency services or a crisis line
> (international directory: <https://findahelpline.com>).

## Run it

```bash
pip install -r chatbot/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # https://platform.claude.com
python -m chatbot.chat
```

In-chat commands:

| Command | Effect |
|---|---|
| `/letter` | Generate and save the end-of-session letter (a Narrative Therapy "therapeutic document") |
| `/quit` | End the session — also writes a letter if the conversation had substance |

Letters are saved to `chatbot/letters/`.

## What's in v0

- **`prompts.py`** — the system prompt encoding the Narrative Therapy stance and the six
  practices (externalizing, mapping effects, deconstruction, unique outcomes,
  re-authoring, re-membering), the scripted crisis message, and the letter prompt.
  This file is where most iteration should happen.
- **`chat.py`** — streaming chat loop on `claude-opus-5` with prompt caching, a keyword
  crisis backstop that suspends narrative work with a *scripted* (never generated)
  response, and letter generation from the transcript.

## What's deliberately not here yet (see the design doc)

- v1: model-based risk classifier in front of the keyword backstop
- v2: phase tracking + per-user memory across sessions
- v4: web UI, auth, letter history
