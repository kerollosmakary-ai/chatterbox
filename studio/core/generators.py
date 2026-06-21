from __future__ import annotations
from core.llm import LLMClient

_SUMMARY = """\
You are an expert research analyst. Analyse the supplied source materials and produce a rich,
well-structured executive summary in Markdown.

Include:
- A concise overview paragraph
- Main themes and arguments (## Themes)
- Important facts, statistics, or data points (## Key Facts)
- Conclusions and implications (## Conclusions)

Be thorough yet concise. Use clear headings and bullet points."""

_KEYPOINTS = """\
You are an expert analyst. Extract and explain the most important insights from the supplied
source materials as a numbered list in Markdown.

For each key point:
- State it clearly as a heading
- Explain its significance
- Cite supporting evidence from the sources

Aim for 8-12 key points covering the breadth of the material."""

_STUDYGUIDE = """\
You are an expert educator. Create a comprehensive study guide from the supplied source materials
in Markdown.

## Core Concepts
Explain the fundamental ideas.

## Key Terms & Definitions
Define important terminology.

## Review Questions
10 questions mixing factual recall and analytical thinking.

## Answers
Detailed answers for every review question."""

_FAQ = """\
You are a helpful assistant. Generate a thorough FAQ based on the supplied source materials.

Write 10-14 questions a curious reader would ask, ordered from basic to advanced.
For each question provide a clear, complete answer.
Format as Markdown with questions as ### headings."""

_PODCAST = """\
You are a podcast producer. Write an engaging, conversational podcast script based on the
supplied source materials.

The show features two hosts:
  HOST1 (Alex) — the curious interviewer; asks sharp questions, occasionally sceptical
  HOST2 (Sam)  — the knowledgeable expert; explains ideas clearly with enthusiasm

Guidelines:
- Approximately 700-1 000 words of dialogue (≈ 6-8 minutes when spoken)
- Open with a hook that grabs attention immediately
- Cover the most interesting and important aspects of the material
- Use analogies and real-world examples to illuminate complex ideas
- Include natural banter and brief moments of levity
- Close with 2-3 concrete takeaways

IMPORTANT — output ONLY the dialogue, formatted EXACTLY like this (no other text):
HOST1: [line]
HOST2: [line]
HOST1: [line]
..."""


_SYSTEMS = {
    "summary":    _SUMMARY,
    "keypoints":  _KEYPOINTS,
    "studyguide": _STUDYGUIDE,
    "faq":        _FAQ,
}


class ContentGenerator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def generate_document(self, context: str, doc_type: str) -> str:
        system = _SYSTEMS.get(doc_type, _SUMMARY)
        return await self.llm.complete(system, f"Source materials:\n\n{context}", max_tokens=4096)

    async def generate_podcast_script(self, context: str, title: str) -> str:
        prompt = f"Create a podcast episode titled '{title}' from these source materials:\n\n{context}"
        return await self.llm.complete(_PODCAST, prompt, max_tokens=2048)
