"""Narrative Therapy chatbot — v0 streaming CLI chat loop.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m chatbot.chat

Commands inside the chat:
    /letter   generate the end-of-session letter and save it next to this script
    /quit     exit (also generates a letter if the session had substance)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from chatbot.prompts import (
    CRISIS_KEYWORDS,
    CRISIS_MESSAGE,
    LETTER_PROMPT,
    SYSTEM_PROMPT,
)

MODEL = "claude-opus-5"
LETTER_DIR = Path(__file__).resolve().parent / "letters"

# Stable system block with a cache breakpoint — every turn after the first reads
# the cached prefix instead of re-processing the full prompt.
SYSTEM = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


def crisis_flagged(user_text: str) -> bool:
    lowered = user_text.lower()
    return any(keyword in lowered for keyword in CRISIS_KEYWORDS)


def stream_reply(client: anthropic.Anthropic, messages: list[dict]) -> str:
    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM,
        output_config={"effort": "medium"},
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()
    print()
    if final.stop_reason == "refusal":
        return ""
    return next((b.text for b in final.content if b.type == "text"), "")


def render_transcript(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        speaker = "Person" if m["role"] == "user" else "Companion"
        lines.append(f"{speaker}: {m['content']}")
    return "\n\n".join(lines)


def write_letter(client: anthropic.Anthropic, messages: list[dict]) -> Path | None:
    # Fewer than two user turns isn't a session worth documenting.
    if sum(1 for m in messages if m["role"] == "user") < 2:
        return None
    print("\nWriting your session letter...\n")
    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": LETTER_PROMPT.format(
                    transcript=render_transcript(messages)
                ),
            }
        ],
    ) as stream:
        letter = stream.get_final_message()
    if letter.stop_reason == "refusal":
        print("(The letter could not be generated for this session.)")
        return None
    text = next((b.text for b in letter.content if b.type == "text"), "")
    LETTER_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    path = LETTER_DIR / f"letter-{stamp}.md"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n(Saved to {path})")
    return path


def main() -> None:
    client = anthropic.Anthropic()
    messages: list[dict] = []

    print(
        "This is a reflection companion, not therapy or medical care.\n"
        "If you are in crisis, contact your local emergency services or a\n"
        "crisis line (https://findahelpline.com). Type /quit to end, /letter\n"
        "for a written summary of the conversation.\n"
    )
    print("Companion: Hello. I'm glad you're here. What's been on your mind lately?\n")
    messages.append(
        {
            "role": "assistant",
            "content": "Hello. I'm glad you're here. What's been on your mind lately?",
        }
    )

    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            write_letter(client, messages)
            return

        if not user_text:
            continue
        if user_text.lower() == "/quit":
            write_letter(client, messages)
            return
        if user_text.lower() == "/letter":
            write_letter(client, messages)
            continue

        messages.append({"role": "user", "content": user_text})

        if crisis_flagged(user_text):
            # Scripted, not generated: we want this exact behavior every time.
            print(f"\nCompanion: {CRISIS_MESSAGE}\n")
            messages.append({"role": "assistant", "content": CRISIS_MESSAGE})
            continue

        print("\nCompanion: ", end="", flush=True)
        try:
            reply = stream_reply(client, messages)
        except anthropic.RateLimitError:
            print("(Rate limited — wait a moment and send that again.)")
            messages.pop()
            continue
        except anthropic.APIConnectionError:
            print("(Connection lost — check your network and send that again.)")
            messages.pop()
            continue
        except anthropic.APIStatusError as e:
            print(f"(API error {e.status_code} — send that again in a moment.)")
            messages.pop()
            continue
        print()

        if not reply:
            reply = CRISIS_MESSAGE
            print(f"Companion: {reply}\n")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    sys.exit(main())
