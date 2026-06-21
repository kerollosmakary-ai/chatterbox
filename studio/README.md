# Notebook Studio

A **NotebookLM-style** local studio that turns your documents, PDFs, and web pages into:
- AI-generated **summaries, key points, study guides, and FAQs**
- **Audio podcasts** — two-host conversations synthesised with edge-tts (optionally upgraded to Chatterbox TTS for GPU voice cloning)

Built with FastAPI + vanilla JS.  Supports **Anthropic, OpenAI, Groq, and OpenRouter** — bring your own API key.

---

## Quick start

```bash
cd studio
pip install -r requirements.txt
python main.py
```

Then open **http://localhost:7860** in your browser.

> **ffmpeg** is required for audio concatenation.  
> Install it via `brew install ffmpeg` (macOS), `sudo apt install ffmpeg` (Linux), or from https://ffmpeg.org/download.html.

---

## Usage

1. Click **⚙️** → enter your API key and choose a provider + model → **Save**
2. Upload PDFs / text files with **+ Upload**, or paste a URL with **+ URL**
3. Click sources to select them (checkmark appears)
4. Choose a tab (Summary / Key Points / Study Guide / FAQ) and click **✨ Generate**
5. Click **Generate Podcast** to create an audio overview — the player appears when the MP3 is ready

---

## Supported sources

| Type | Extension |
|------|-----------|
| PDF  | `.pdf` |
| Text | `.txt`, `.md` |
| Word | `.docx` (requires `pip install python-docx`) |
| Web  | Any public URL |

---

## LLM providers

| Provider | Models | Notes |
|----------|--------|-------|
| **Anthropic** | claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5 | Best quality |
| **OpenAI** | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | |
| **Groq** | llama-3.3-70b, mixtral-8x7b | Free tier available |
| **OpenRouter** | 100+ models | One key, many providers |

---

## Podcast TTS

By default the studio uses **edge-tts** (Microsoft Neural TTS, CPU, free).  
To upgrade to **Chatterbox** (GPU voice cloning, same repo):

```bash
# From the repo root
pip install -e .
# Then restart the studio — it auto-detects Chatterbox when CUDA is available
```

Set your preferred voices in **⚙️ Settings**.

---

## Stack

- **Backend** — FastAPI + uvicorn
- **Document parsing** — pdfplumber, httpx, BeautifulSoup4
- **LLM** — anthropic / openai SDK (Groq and OpenRouter via OpenAI-compat)
- **TTS** — edge-tts (primary) → Chatterbox TTS (GPU optional)
- **Audio** — pydub / ffmpeg
- **Frontend** — Vanilla JS, marked.js for Markdown rendering
