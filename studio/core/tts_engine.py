from __future__ import annotations
import asyncio
import shutil
from pathlib import Path
from typing import List, Tuple


class TTSEngine:
    def __init__(
        self,
        voice_host1: str = "en-US-GuyNeural",
        voice_host2: str = "en-US-JennyNeural",
    ):
        self.voice_host1 = voice_host1
        self.voice_host2 = voice_host2

    # ── Public ────────────────────────────────────────────────────────────
    async def generate_podcast_audio(self, script: str, output_path: str) -> None:
        lines = self._parse_script(script)
        if not lines:
            raise ValueError(
                "No dialogue found.  Script must contain lines starting with HOST1: or HOST2:"
            )

        tmp = Path(output_path).parent / f"_tmp_{Path(output_path).stem}"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            segments = await self._render_segments(lines, tmp)
            await self._concat(segments, output_path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Helpers ───────────────────────────────────────────────────────────
    def _parse_script(self, script: str) -> List[Tuple[str, str]]:
        lines: List[Tuple[str, str]] = []
        for raw in script.strip().splitlines():
            raw = raw.strip()
            if raw.upper().startswith("HOST1:"):
                text = raw[6:].strip()
                if text:
                    lines.append(("host1", text))
            elif raw.upper().startswith("HOST2:"):
                text = raw[6:].strip()
                if text:
                    lines.append(("host2", text))
        return lines

    async def _render_segments(
        self, lines: List[Tuple[str, str]], tmp: Path
    ) -> List[str]:
        # Try chatterbox first (GPU), fall back to edge-tts (CPU)
        try:
            return await self._render_chatterbox(lines, tmp)
        except Exception:
            pass
        return await self._render_edge_tts(lines, tmp)

    async def _render_edge_tts(
        self, lines: List[Tuple[str, str]], tmp: Path
    ) -> List[str]:
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("Install edge-tts: pip install edge-tts")

        paths: List[str] = []
        for i, (speaker, text) in enumerate(lines):
            voice = self.voice_host1 if speaker == "host1" else self.voice_host2
            dest  = str(tmp / f"{i:04d}.mp3")
            comm  = edge_tts.Communicate(text, voice)
            await comm.save(dest)
            paths.append(dest)
        return paths

    async def _render_chatterbox(
        self, lines: List[Tuple[str, str]], tmp: Path
    ) -> List[str]:
        import torch
        from chatterbox.tts import ChatterboxTTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            raise RuntimeError("Chatterbox requires a CUDA GPU")

        model = ChatterboxTTS.from_pretrained(device)
        import torchaudio

        paths: List[str] = []
        for i, (_speaker, text) in enumerate(lines):
            wav  = model.generate(text)
            dest = str(tmp / f"{i:04d}.wav")
            torchaudio.save(dest, wav.squeeze(0).unsqueeze(0).cpu(), model.sr)
            paths.append(dest)
        return paths

    async def _concat(self, segment_paths: List[str], output_path: str) -> None:
        # Try pydub, then ffmpeg subprocess
        try:
            from pydub import AudioSegment
            silence = AudioSegment.silent(duration=350)
            combined = AudioSegment.empty()
            for p in segment_paths:
                fmt = "wav" if p.endswith(".wav") else "mp3"
                combined += AudioSegment.from_file(p, format=fmt) + silence
            combined.export(output_path, format="mp3")
            return
        except ImportError:
            pass

        # ffmpeg fallback
        import subprocess
        list_file = Path(output_path).parent / "_list.txt"
        with open(list_file, "w") as f:
            for p in segment_paths:
                f.write(f"file '{p}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(list_file), "-c", "copy", output_path],
            check=True, capture_output=True,
        )
        list_file.unlink(missing_ok=True)
