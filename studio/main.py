import uuid
import shutil
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiofiles
import uvicorn

from core.document_processor import DocumentProcessor
from core.generators import ContentGenerator
from core.llm import LLMClient
from core.tts_engine import TTSEngine

# ── Paths & data directories ────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
UPLOADS    = DATA_DIR / "uploads"
AUDIO_DIR  = DATA_DIR / "audio"

for _d in [DATA_DIR, UPLOADS, AUDIO_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── In-memory state ─────────────────────────────────────────────────────────
sources:   dict = {}
documents: dict = {}
podcasts:  dict = {}

settings: dict = {
    "provider": "anthropic",
    "api_key": "",
    "model": "claude-sonnet-4-6",
    "tts_voice_host1": "en-US-GuyNeural",
    "tts_voice_host2": "en-US-JennyNeural",
}

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Notebook Studio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _llm() -> LLMClient:
    if not settings["api_key"]:
        raise HTTPException(400, "API key not set. Open Settings (⚙️) to add your key.")
    return LLMClient(settings["provider"], settings["api_key"], settings["model"])


# ── Settings ────────────────────────────────────────────────────────────────
class SettingsIn(BaseModel):
    provider: Optional[str] = None
    api_key:  Optional[str] = None
    model:    Optional[str] = None
    tts_voice_host1: Optional[str] = None
    tts_voice_host2: Optional[str] = None


@app.get("/api/settings")
def get_settings():
    safe = {**settings}
    if safe["api_key"]:
        safe["api_key"] = "***" + safe["api_key"][-4:]
    return safe


@app.post("/api/settings")
def save_settings(body: SettingsIn):
    for k, v in body.model_dump(exclude_none=True).items():
        settings[k] = v
    return {"ok": True}


# ── Sources ─────────────────────────────────────────────────────────────────
@app.get("/api/sources")
def list_sources():
    return [{k: v for k, v in s.items() if k != "content"} for s in sources.values()]


@app.post("/api/sources/upload")
async def upload_source(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".txt", ".md", ".docx"):
        raise HTTPException(400, f"Unsupported type '{ext}'. Use PDF, TXT, MD, or DOCX.")

    sid  = str(uuid.uuid4())
    dest = UPLOADS / f"{sid}{ext}"

    async with aiofiles.open(dest, "wb") as f:
        data = await file.read()
        await f.write(data)

    try:
        text = DocumentProcessor().process_file(str(dest), ext)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, str(exc))

    rec = {
        "id": sid, "name": file.filename, "type": "file",
        "ext": ext, "char_count": len(text), "preview": text[:300],
        "content": text,
    }
    sources[sid] = rec
    return {k: v for k, v in rec.items() if k != "content"}


class URLIn(BaseModel):
    url: str


@app.post("/api/sources/url")
async def import_url(body: URLIn):
    try:
        title, text = await DocumentProcessor().process_url(body.url)
    except Exception as exc:
        raise HTTPException(500, str(exc))

    sid = str(uuid.uuid4())
    rec = {
        "id": sid, "name": title or body.url, "type": "url",
        "url": body.url, "char_count": len(text), "preview": text[:300],
        "content": text,
    }
    sources[sid] = rec
    return {k: v for k, v in rec.items() if k != "content"}


@app.delete("/api/sources/{sid}")
def delete_source(sid: str):
    if sid not in sources:
        raise HTTPException(404, "Source not found")
    sources.pop(sid)
    return {"ok": True}


# ── Document generation ─────────────────────────────────────────────────────
class DocGenIn(BaseModel):
    source_ids: List[str]
    doc_type: str   # summary | keypoints | studyguide | faq


@app.post("/api/generate/document")
async def generate_document(body: DocGenIn):
    if not body.source_ids:
        raise HTTPException(400, "Select at least one source.")

    combined = _build_context(body.source_ids, max_chars_each=8000)
    llm      = _llm()
    gen      = ContentGenerator(llm)

    try:
        content = await gen.generate_document(combined, body.doc_type)
    except Exception as exc:
        raise HTTPException(500, str(exc))

    did = str(uuid.uuid4())
    doc = {
        "id": did, "type": body.doc_type,
        "title": _doc_label(body.doc_type),
        "content": content, "source_ids": body.source_ids,
    }
    documents[did] = doc
    return doc


@app.get("/api/documents")
def list_documents():
    return list(documents.values())


# ── Podcast generation ───────────────────────────────────────────────────────
class PodcastIn(BaseModel):
    source_ids: List[str]
    title: Optional[str] = "AI Overview"


@app.post("/api/generate/podcast")
async def generate_podcast(body: PodcastIn, bg: BackgroundTasks):
    if not body.source_ids:
        raise HTTPException(400, "Select at least one source.")

    combined = _build_context(body.source_ids, max_chars_each=6000)
    llm      = _llm()
    gen      = ContentGenerator(llm)

    try:
        script = await gen.generate_podcast_script(combined, body.title)
    except Exception as exc:
        raise HTTPException(500, f"Script generation failed: {exc}")

    pid = str(uuid.uuid4())
    podcast = {
        "id": pid, "title": body.title,
        "script": script, "source_ids": body.source_ids,
        "audio_ready": False, "audio_path": None, "error": None,
    }
    podcasts[pid] = podcast
    bg.add_task(_render_audio, pid, script)
    return podcast


async def _render_audio(pid: str, script: str):
    tts = TTSEngine(
        voice_host1=settings.get("tts_voice_host1", "en-US-GuyNeural"),
        voice_host2=settings.get("tts_voice_host2", "en-US-JennyNeural"),
    )
    out = AUDIO_DIR / f"{pid}.mp3"
    try:
        await tts.generate_podcast_audio(script, str(out))
        podcasts[pid]["audio_ready"] = True
        podcasts[pid]["audio_path"]  = f"/api/audio/{pid}.mp3"
    except Exception as exc:
        podcasts[pid]["error"] = str(exc)


@app.get("/api/podcasts/{pid}")
def get_podcast(pid: str):
    if pid not in podcasts:
        raise HTTPException(404, "Podcast not found")
    return podcasts[pid]


@app.get("/api/audio/{filename}")
def serve_audio(filename: str):
    path = AUDIO_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Audio not found")
    return FileResponse(str(path), media_type="audio/mpeg")


# ── Helpers ─────────────────────────────────────────────────────────────────
def _build_context(source_ids: List[str], max_chars_each: int = 8000) -> str:
    parts = []
    for sid in source_ids:
        if sid not in sources:
            raise HTTPException(404, f"Source {sid} not found")
        s = sources[sid]
        parts.append(f"--- {s['name']} ---\n{s['content'][:max_chars_each]}")
    return "\n\n".join(parts)


def _doc_label(t: str) -> str:
    return {"summary": "Summary", "keypoints": "Key Points",
            "studyguide": "Study Guide", "faq": "FAQ"}.get(t, t)


# ── Static files (must come last) ────────────────────────────────────────────
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=True, app_dir=str(BASE_DIR))
