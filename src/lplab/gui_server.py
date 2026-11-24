"""FastAPI server for lplab native desktop GUI."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import json
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from lplab.ai_generator import AILabGenerator
from lplab.config import AppConfig, load_config
from lplab.lab_engine import LabEngine
from lplab.models import CheckResult, LabRuntimeStatus, VerifyReport
from lplab.paths import get_static_index_path
from lplab.rootfs_builder import build_rootfs_tar


class EventBroker:
    """Thread-safe event pub/sub broker with history buffering for SSE streams."""

    def __init__(self, max_history: int = 200):
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.job_status: str = "idle"
        self.current_lab_id: Optional[str] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def set_job_status(self, status: str, lab_id: Optional[str] = None) -> None:
        self.job_status = status
        self.current_lab_id = lab_id
        self.publish({"type": "job_status", "status": status, "lab_id": lab_id})

    def log(self, text: str, level: str = "info") -> None:
        time_str = datetime.now().strftime("%H:%M:%S")
        self.publish({
            "type": "log",
            "text": text,
            "level": level,
            "time": time_str,
        })

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            queues = list(self._subscribers)

        for q in queues:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(q.put_nowait, event)

    def subscribe(self, q: asyncio.Queue) -> List[Dict[str, Any]]:
        with self._lock:
            self._subscribers.add(q)
            return list(self._history)

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers.discard(q)


class GenerateRequest(BaseModel):
    """Payload for generating a new AI lab."""
    domain: str = Field(default="system_management", description="CompTIA Linux+ XK0-006 domain")
    topic: str = Field(default="storage-repair", description="Scenario topic")
    base_image: str = Field(default="rockylinux-9", description="Base image name")


class BuildImageRequest(BaseModel):
    """Payload for triggering rootfs archive build."""
    image: str = Field(default="all", description="'rockylinux-9', 'ubuntu-24.04', or 'all'")
    force: bool = Field(default=False, description="Force rebuild")


def get_images_status(config: AppConfig) -> Dict[str, bool]:
    """Check existence of cached base image archives."""
    rocky_tar = config.base_images_dir / "rockylinux-9.tar"
    ubuntu_tar = config.base_images_dir / "ubuntu-24.04.tar"
    return {
        "rockylinux-9": rocky_tar.is_file(),
        "ubuntu-24.04": ubuntu_tar.is_file(),
    }


def create_app(config: Optional[AppConfig] = None, engine: Optional[LabEngine] = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app_config = config or load_config()
    app_engine = engine or LabEngine(app_config)
    broker = EventBroker()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        broker.set_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(
        title="lplab-gui-server",
        description="Local desktop API backend for lplab CompTIA Linux+ Lab Engine",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.state.config = app_config
    app.state.engine = app_engine
    app.state.broker = broker

    @app.get("/", response_class=HTMLResponse)
    async def get_index():
        """Serve the zero-build-step single page desktop frontend."""
        static_index = get_static_index_path()
        if not static_index.is_file():
            raise HTTPException(status_code=404, detail="Dashboard UI static file not found")
        content = static_index.read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    @app.get("/api/labs")
    async def get_labs():
        """List all labs with manifest fields, runtime status, score, and check items."""
        engine_inst: LabEngine = app.state.engine
        labs = engine_inst.discover_labs()
        results = []
        for manifest, _ in labs:
            status, record = engine_inst.get_lab_status(manifest)
            results.append({
                "id": manifest.id,
                "slug": manifest.slug,
                "title": manifest.title,
                "distro_name": manifest.distro_name,
                "base_image": manifest.base_image,
                "student_user": manifest.student_user,
                "difficulty": manifest.difficulty,
                "estimated_minutes": manifest.estimated_minutes,
                "xk0_006_domains": manifest.xk0_006_domains,
                "objectives": manifest.objectives,
                "status": status.value,
                "last_verified": record.last_verified if record else None,
                "score_passed": record.score_passed if record else 0,
                "score_total": record.score_total if record else 0,
                "provisioned_at": record.provisioned_at if record else None,
                "checks": [c.model_dump() for c in record.checks] if (record and record.checks) else [],
            })
        return results

    @app.get("/api/labs/{lab_id}/brief")
    async def get_lab_brief(lab_id: str):
        """Return raw BRIEF.md content and manifest metadata for a lab."""
        engine_inst: LabEngine = app.state.engine
        lab = engine_inst.get_lab(lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
        manifest, lab_dir = lab
        brief_file = lab_dir / "BRIEF.md"
        brief_content = brief_file.read_text(encoding="utf-8") if brief_file.is_file() else ""
        return {
            "manifest": manifest.model_dump(),
            "brief_md": brief_content,
        }

    @app.post("/api/labs/{lab_id}/start")
    async def start_lab(lab_id: str):
        """Run engine.start_lab in a background worker thread, streaming progress."""
        engine_inst: LabEngine = app.state.engine
        lab = engine_inst.get_lab(lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
        manifest, lab_dir = lab

        def do_start():
            broker.set_job_status("provisioning", lab_id)
            try:
                broker.log(f"[{lab_id}] Starting lab provisioning / launch...")
                engine_inst.start_lab(
                    manifest=manifest,
                    lab_dir=lab_dir,
                    progress_callback=lambda msg: broker.log(f"[{lab_id}] {msg}"),
                )
                status, _ = engine_inst.get_lab_status(manifest)
                broker.publish({"type": "lab_status", "lab_id": lab_id, "status": status.value})
                broker.log(f"[{lab_id}] Terminal launched successfully.", level="success")
            except Exception as e:
                broker.log(f"[{lab_id}] Failed to start lab: {e}", level="error")
                raise
            finally:
                broker.set_job_status("idle")

        try:
            await asyncio.to_thread(do_start)
            return {"status": "success", "message": f"Lab '{lab_id}' started", "lab_id": lab_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/labs/{lab_id}/verify")
    async def verify_lab(lab_id: str):
        """Run engine.verify_lab in a background thread and return full VerifyReport."""
        engine_inst: LabEngine = app.state.engine
        lab = engine_inst.get_lab(lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
        manifest, lab_dir = lab

        def do_verify() -> VerifyReport:
            broker.set_job_status("verifying", lab_id)
            try:
                broker.log(f"[{lab_id}] Running verification checks on {manifest.distro_name}...")
                report = engine_inst.verify_lab(
                    manifest=manifest,
                    lab_dir=lab_dir,
                    progress_callback=lambda msg: broker.log(f"[{lab_id}] {msg}"),
                )
                status, record = engine_inst.get_lab_status(manifest)
                broker.publish({
                    "type": "lab_status",
                    "lab_id": lab_id,
                    "status": status.value,
                    "score_passed": report.score_passed,
                    "score_total": report.score_total,
                })
                lvl = "success" if report.passed else "warn"
                broker.log(
                    f"[{lab_id}] Verification finished: {report.score_passed}/{report.score_total} passed.",
                    level=lvl,
                )
                return report
            except Exception as e:
                broker.log(f"[{lab_id}] Verification error: {e}", level="error")
                raise
            finally:
                broker.set_job_status("idle")

        try:
            report = await asyncio.to_thread(do_verify)
            return report.model_dump()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/labs/{lab_id}/stop")
    async def stop_lab(lab_id: str):
        """Terminate the lab distro."""
        engine_inst: LabEngine = app.state.engine
        lab = engine_inst.get_lab(lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
        manifest, _ = lab

        def do_stop():
            broker.log(f"[{lab_id}] Stopping distro {manifest.distro_name}...")
            engine_inst.stop_lab(
                manifest=manifest,
                progress_callback=lambda msg: broker.log(f"[{lab_id}] {msg}"),
            )
            status, _ = engine_inst.get_lab_status(manifest)
            broker.publish({"type": "lab_status", "lab_id": lab_id, "status": status.value})
            broker.log(f"[{lab_id}] Distro stopped.", level="info")

        try:
            await asyncio.to_thread(do_stop)
            return {"status": "success", "message": f"Lab '{lab_id}' stopped", "lab_id": lab_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/labs/{lab_id}/reset")
    async def reset_lab(lab_id: str):
        """Unregister and rebuild the lab distro in a background thread."""
        engine_inst: LabEngine = app.state.engine
        lab = engine_inst.get_lab(lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
        manifest, lab_dir = lab

        def do_reset():
            broker.set_job_status("resetting", lab_id)
            try:
                broker.log(f"[{lab_id}] Resetting lab distro {manifest.distro_name} from scratch...")
                engine_inst.reset_lab(
                    manifest=manifest,
                    lab_dir=lab_dir,
                    progress_callback=lambda msg: broker.log(f"[{lab_id}] {msg}"),
                )
                status, _ = engine_inst.get_lab_status(manifest)
                broker.publish({"type": "lab_status", "lab_id": lab_id, "status": status.value})
                broker.log(f"[{lab_id}] Reset completed successfully.", level="success")
            except Exception as e:
                broker.log(f"[{lab_id}] Reset error: {e}", level="error")
                raise
            finally:
                broker.set_job_status("idle")

        try:
            await asyncio.to_thread(do_reset)
            return {"status": "success", "message": f"Lab '{lab_id}' reset complete", "lab_id": lab_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/generate")
    async def generate_lab(req: GenerateRequest):
        """Generate a new AI lab scenario with safety linting and save it."""
        cfg: AppConfig = app.state.config

        def do_generate():
            broker.set_job_status("generating")
            try:
                broker.log(f"Synthesizing scenario for {req.domain}: '{req.topic}' ({req.base_image})...")
                generator = AILabGenerator(cfg.ai)
                payload = generator.generate_lab(
                    domain=req.domain,
                    topic=req.topic,
                    base_image=req.base_image,
                )
                saved_dir = generator.save_generated_lab(payload, cfg.labs_dir)
                broker.log(f"Generated lab saved to {saved_dir.name}", level="success")
                broker.publish({"type": "refresh_labs"})
                return payload, saved_dir
            except Exception as e:
                broker.log(f"AI generation failed: {e}", level="error")
                raise
            finally:
                broker.set_job_status("idle")

        try:
            payload, saved_dir = await asyncio.to_thread(do_generate)
            return {
                "status": "success",
                "manifest": payload.manifest.model_dump(),
                "saved_dir": str(saved_dir),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/images/status")
    async def check_images():
        """Return base image archive readiness."""
        cfg: AppConfig = app.state.config
        return get_images_status(cfg)

    @app.post("/api/images/build")
    async def build_images(req: BuildImageRequest):
        """Trigger base image tarball build."""
        cfg: AppConfig = app.state.config

        def do_build():
            broker.set_job_status("building_image")
            try:
                targets = ["rockylinux-9", "ubuntu-24.04"] if req.image.lower() == "all" else [req.image]
                built = []
                for target in targets:
                    broker.log(f"Building base image archive for {target}...")
                    tar_path = build_rootfs_tar(
                        base_image=target,
                        output_dir=cfg.base_images_dir,
                        force=req.force,
                        progress_callback=lambda msg: broker.log(f"[{target}] {msg}"),
                    )
                    built.append(str(tar_path))
                    broker.log(f"Successfully built {target}: {tar_path.name}", level="success")
                status = get_images_status(cfg)
                broker.publish({"type": "images_status", "images": status})
                return built
            except Exception as e:
                broker.log(f"Image build failed: {e}", level="error")
                raise
            finally:
                broker.set_job_status("idle")

        try:
            built_paths = await asyncio.to_thread(do_build)
            return {"status": "success", "built": built_paths}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/events")
    async def events_stream(request: Request):
        """Server-Sent Events (SSE) stream for live log lines and state notifications."""
        async def event_generator():
            q: asyncio.Queue = asyncio.Queue()
            history = broker.subscribe(q)
            try:
                # Stream recent history
                for evt in history:
                    yield f"data: {json.dumps(evt)}\n\n"

                # Send initial job status and images status
                yield f"data: {json.dumps({'type': 'job_status', 'status': broker.job_status, 'lab_id': broker.current_lab_id})}\n\n"
                images_curr = get_images_status(app.state.config)
                yield f"data: {json.dumps({'type': 'images_status', 'images': images_curr})}\n\n"

                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        evt = await asyncio.wait_for(q.get(), timeout=15.0)
                        yield f"data: {json.dumps(evt)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                broker.unsubscribe(q)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app


# Default app instance bound to 127.0.0.1
app = create_app()
