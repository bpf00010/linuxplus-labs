"""AI lab scenario generator and static safety linter."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import httpx
import yaml

from lplab.models import AIConfig, GeneratedLabPayload, LabManifest


class SafetyLinter:
    """Static safety linter enforcing strict containment and syntax checks."""

    HOST_MOUNT_PATTERNS = [
        re.compile(r"/mnt/[a-zA-Z]\b", re.IGNORECASE),
        re.compile(r"\b[a-zA-Z]:[\\/]", re.IGNORECASE),
    ]

    UNSCOPED_FIREWALL_PATTERNS = [
        re.compile(r"nft\s+flush\s+ruleset", re.IGNORECASE),
        re.compile(r"iptables\s+-F\s*($|;|\n)", re.IGNORECASE),
        re.compile(r"iptables\s+--flush\s*($|;|\n)", re.IGNORECASE),
        re.compile(r"ip6tables\s+-F\s*($|;|\n)", re.IGNORECASE),
    ]

    @classmethod
    def is_dangerous_rm(cls, line: str) -> bool:
        """Check if line contains dangerous recursive root removal."""
        tokens = line.split()
        if not any(t == "rm" or t.endswith("/rm") for t in tokens):
            return False
        has_root_target = (
            any(t in ("/", "/*") for t in tokens)
            or bool(re.search(r"\s+/\s+\*", line))
            or bool(re.search(r"\s+/\*(\s|$)", line))
            or bool(re.search(r"\s+/\s*$", line))
        )
        if not has_root_target:
            return False
        has_recursive = any(
            t in ("-r", "-R", "--recursive")
            or (t.startswith("-") and not t.startswith("--") and any(c in t for c in "rR"))
            for t in tokens
        )
        has_force = any(
            t in ("-f", "-F", "--force")
            or (t.startswith("-") and not t.startswith("--") and any(c in t for c in "fF"))
            for t in tokens
        )
        return has_recursive and has_force

    @classmethod
    def check_bash_syntax(cls, script_content: str) -> Optional[str]:
        """Validate bash script syntax using bash -n natively or via WSL bridge."""
        # 1. Direct Git for Windows bash or PATH bash (ultra-fast, ~5ms)
        candidates = []
        if sys.platform == "win32":
            candidates.extend([
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files\Git\usr\bin\bash.exe",
            ])
        shutil_bash = shutil.which("bash")
        if shutil_bash and not shutil_bash.lower().endswith(r"system32\bash.exe"):
            candidates.append(shutil_bash)

        for bash_cmd in candidates:
            if Path(bash_cmd).is_file():
                try:
                    res = subprocess.run(
                        [bash_cmd, "-n"],
                        input=script_content.encode("utf-8"),
                        capture_output=True,
                        timeout=5,
                    )
                    if res.returncode != 0:
                        return res.stderr.decode("utf-8", errors="replace")
                    return None
                except Exception:
                    pass

        # 2. WSL bridge check if on Windows
        if sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["wsl.exe", "--", "bash", "-n"],
                    input=script_content.encode("utf-8"),
                    capture_output=True,
                    timeout=5,
                )
                if res.returncode != 0:
                    return res.stderr.decode("utf-8", errors="replace")
                return None
            except Exception:
                pass

        # Basic fallback syntactic balance checks
        if script_content.count("if ") > script_content.count("fi"):
            return "Syntax error: unmatched 'if' and 'fi'"
        if script_content.count("do\n") > script_content.count("done"):
            return "Syntax error: unmatched 'do' and 'done'"
        return None

    @classmethod
    def lint_script(cls, script_content: str, script_name: str) -> List[str]:
        """Lint a bash script for security risks and structural compliance."""
        errors: List[str] = []

        # Check rm -rf /
        for line in script_content.splitlines():
            if cls.is_dangerous_rm(line):
                errors.append(f"{script_name}: Contains dangerous destructive root command: 'rm -rf /'")
                break

        # Check host mounts /mnt/c etc.
        for pat in cls.HOST_MOUNT_PATTERNS:
            if pat.search(script_content):
                errors.append(
                    f"{script_name}: References host filesystem mount (/mnt/c or drive letter). "
                    "Labs run with [automount] enabled=false and must be fully self-contained."
                )

        # Check unscoped firewall flush
        for pat in cls.UNSCOPED_FIREWALL_PATTERNS:
            if pat.search(script_content):
                errors.append(
                    f"{script_name}: Global firewall flush detected (e.g. 'nft flush ruleset' or 'iptables -F'). "
                    "WSL2 shares one kernel netns; firewall labs MUST scope rules to a dedicated named table "
                    "(e.g. 'table inet lplab_<id>') or isolated 'ip netns'."
                )

        # Check bash syntax
        syntax_err = cls.check_bash_syntax(script_content)
        if syntax_err:
            errors.append(f"{script_name} has bash syntax errors: {syntax_err.strip()}")

        return errors

    @classmethod
    def lint_manifest(cls, manifest: LabManifest) -> List[str]:
        """Validate manifest requirements."""
        errors: List[str] = []
        if not manifest.distro_name.startswith("lplab-"):
            errors.append(
                f"Distro name '{manifest.distro_name}' violates namespace guard. Must start with 'lplab-'."
            )
        return errors

    @classmethod
    def lint_verify_script(cls, verify_sh: str) -> List[str]:
        """Ensure verify.sh satisfies the JSON stdout contract."""
        errors: List[str] = []
        # Must contain keys from JSON contract
        required_keys = ["lab_id", "passed", "score_passed", "score_total", "checks"]
        for k in required_keys:
            if f'"{k}"' not in verify_sh and f"'{k}'" not in verify_sh and k not in verify_sh:
                errors.append(f"verify.sh does not appear to emit required JSON key '{k}'.")
        return errors

    @classmethod
    def lint_payload(cls, payload: GeneratedLabPayload) -> List[str]:
        """Run all linting checks across manifest, setup.sh, and verify.sh."""
        errors: List[str] = []
        errors.extend(cls.lint_manifest(payload.manifest))
        errors.extend(cls.lint_script(payload.setup_sh, "setup.sh"))
        errors.extend(cls.lint_script(payload.verify_sh, "verify.sh"))
        errors.extend(cls.lint_verify_script(payload.verify_sh))
        return errors


SYSTEM_PROMPT = """You are an expert CompTIA Linux+ (XK0-006) lab architect.
Your task is to design a realistic, production-ready, hands-on Linux+ troubleshooting or configuration lab scenario for WSL2.

MANDATORY RULES:
1. Strict Distro Namespace: distro_name MUST start with "lplab-" (e.g. "lplab-lab-storage-recovery").
2. No Host Mounts: Under no circumstances reference /mnt/c or /mnt/d. The lab runs with automount and interop disabled.
3. Shared Kernel Firewall Safety: NEVER use global "nft flush ruleset" or "iptables -F". If configuring firewall rules, strictly scope to a named table "table inet lplab_<slug>" on high local ports (18000-18999) or use an isolated "ip netns".
4. Zero-Spoilers BRIEF.md: Formatted as a professional sysadmin IT work order / ticket. Clearly define symptoms and operational criteria without revealing exact commands or solutions.
5. Strict JSON stdout in verify.sh:
   - Must be non-destructive and idempotent.
   - Redirect all tool output to /dev/null (e.g. &>/dev/null).
   - Emit ONLY one valid JSON object to stdout with exact structure:
     {"lab_id": "<id>", "passed": false, "score_passed": 0, "score_total": <total>, "checks": [{"id": "chk-1", "description": "...", "passed": false, "details": "..."}]}
   - Exit code 0 if passed is true, exit code 1 if passed is false.

You must respond with ONLY valid JSON matching this schema:
{
  "manifest": {
    "id": "lab-...",
    "slug": "lab-...",
    "title": "...",
    "distro_name": "lplab-...",
    "base_image": "rockylinux-9" or "ubuntu-24.04",
    "student_user": "sysadmin",
    "difficulty": "beginner" or "intermediate" or "advanced",
    "estimated_minutes": 20,
    "xk0_006_domains": ["system_management", "services_and_users", "security", "automation_scripting", "troubleshooting"],
    "objectives": ["..."]
  },
  "brief_md": "...",
  "setup_sh": "#!/usr/bin/env bash\\nset -euo pipefail\\n...",
  "verify_sh": "#!/usr/bin/env bash\\n..."
}
"""


def strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> reasoning blocks emitted by thinking/reasoning models."""
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"<think>[\s\S]*?(?=(?:```|\{|$))", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_json_from_response(text: str) -> dict:
    """Extract valid JSON from LLM markdown code blocks or raw text, stripping think blocks."""
    clean_text = strip_think_blocks(text)
    # Try direct parse
    try:
        return json.loads(clean_text)
    except Exception:
        pass

    # Try extracting markdown ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass

    # Search between outermost curly brackets
    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(clean_text[start : end + 1])
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from AI response: {clean_text[:200]}...")


def normalize_chat_completion_url(base_url: str, provider: str = "custom") -> str:
    """Normalize base URL to /chat/completions endpoint based on provider preset."""
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1/chat/completions"

    url = (base_url or "").strip().rstrip("/")
    if not url:
        url = "http://localhost:11434/v1"

    if provider == "ollama" and ":11434" in url and not url.endswith("/v1"):
        url = f"{url}/v1"
    elif provider == "open_webui":
        if not url.endswith("/api") and not url.endswith("/v1"):
            url = f"{url}/api"

    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    if url.endswith("/api"):
        return f"{url}/v1/chat/completions"
    return f"{url}/chat/completions"


def detect_local_providers() -> List[Dict[str, Any]]:
    """Fast local provider auto-discovery with 1.5s timeout per probe."""
    detected: List[Dict[str, Any]] = []

    # 1. Ollama probe
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                data = r.json()
                models = [m["name"] for m in data.get("models", []) if isinstance(m, dict) and "name" in m]
                detected.append({
                    "provider": "ollama",
                    "name": "Ollama (Local)",
                    "base_url": "http://localhost:11434/v1",
                    "models": models,
                    "status": "ready",
                    "recommended_model": models[0] if models else "llama3",
                })
    except Exception:
        pass

    # 2. Open WebUI probe (ports 8080 and 3000)
    for port in (8080, 3000):
        try:
            with httpx.Client(timeout=1.5) as client:
                r = client.get(f"http://localhost:{port}/api/config")
                if r.status_code == 200:
                    owui_models: List[str] = []
                    try:
                        rm = client.get(f"http://localhost:{port}/api/models", timeout=1.5)
                        if rm.status_code == 200:
                            mdata = rm.json()
                            if isinstance(mdata, list):
                                owui_models = [m.get("id") or m.get("name") for m in mdata if isinstance(m, dict)]
                            elif isinstance(mdata, dict) and "data" in mdata:
                                owui_models = [m.get("id") for m in mdata.get("data", []) if isinstance(m, dict)]
                    except Exception:
                        pass
                    detected.append({
                        "provider": "open_webui",
                        "name": f"Open WebUI (port {port})",
                        "base_url": f"http://localhost:{port}/api",
                        "models": [m for m in owui_models if m],
                        "status": "ready",
                        "recommended_model": owui_models[0] if owui_models else "",
                    })
                    break
        except Exception:
            pass

    # 3. LM Studio on port 1234
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get("http://localhost:1234/v1/models")
            if r.status_code == 200:
                data = r.json()
                models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]
                detected.append({
                    "provider": "custom",
                    "name": "LM Studio (port 1234)",
                    "base_url": "http://localhost:1234/v1",
                    "models": models,
                    "status": "ready",
                    "recommended_model": models[0] if models else "",
                })
    except Exception:
        pass

    return detected


def fetch_provider_models(
    provider: str,
    base_url: str,
    api_key: Optional[str] = None,
) -> Tuple[bool, List[str], str]:
    """Test connectivity and query live available models from provider."""
    headers: Dict[str, str] = {}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    url = (base_url or "").strip().rstrip("/")

    try:
        with httpx.Client(timeout=10.0) as client:
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/bpf00010/linuxplus-labs"
                headers["X-Title"] = "lplab"
                r = client.get("https://openrouter.ai/api/v1/models", headers=headers)
                r.raise_for_status()
                data = r.json()
                models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]
                return True, sorted(models), f"Discovered {len(models)} models from OpenRouter"

            elif provider == "ollama":
                host = url.replace("/v1", "")
                try:
                    r = client.get(f"{host}/api/tags", headers=headers, timeout=5.0)
                    if r.status_code == 200:
                        data = r.json()
                        models = [m["name"] for m in data.get("models", []) if isinstance(m, dict) and "name" in m]
                        return True, models, f"Discovered {len(models)} models from Ollama"
                except Exception:
                    pass
                models_url = f"{url}/models" if not url.endswith("/models") else url
                r = client.get(models_url, headers=headers, timeout=5.0)
                r.raise_for_status()
                data = r.json()
                models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]
                return True, models, f"Discovered {len(models)} models from Ollama"

            elif provider == "open_webui":
                candidates = [
                    f"{url}/models",
                    f"{url}/v1/models",
                    f"{url}/api/models",
                ]
                for cand in candidates:
                    try:
                        r = client.get(cand, headers=headers, timeout=5.0)
                        if r.status_code == 200:
                            data = r.json()
                            models = []
                            if isinstance(data, list):
                                models = [m.get("id") or m.get("name") for m in data if isinstance(m, dict)]
                            elif isinstance(data, dict):
                                items = data.get("data", []) or data.get("models", [])
                                models = [m.get("id") or m.get("name") for m in items if isinstance(m, dict)]
                            models = [m for m in models if m]
                            return True, models, f"Discovered {len(models)} models from Open WebUI"
                    except Exception:
                        pass
                return False, [], "Could not fetch models from Open WebUI (check Base URL and API key)"

            else:  # custom
                models_url = f"{url}/models" if not url.endswith("/models") else url
                r = client.get(models_url, headers=headers, timeout=5.0)
                r.raise_for_status()
                data = r.json()
                models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]
                return True, models, f"Discovered {len(models)} models"

    except Exception as e:
        return False, [], f"Connection error: {e}"


def assign_next_lab_id_and_distro(payload: GeneratedLabPayload, labs_dir: Path) -> GeneratedLabPayload:
    """Ensure generated lab has a guaranteed unique, non-colliding numeric ID and distro_name."""
    existing_nums: set[int] = set()
    if labs_dir.is_dir():
        for item in labs_dir.iterdir():
            m_sub = re.match(r"^lab-(\d+)", item.name)
            if m_sub:
                existing_nums.add(int(m_sub.group(1)))
            yaml_file = item / "lab.yaml"
            if yaml_file.is_file():
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        yd = yaml.safe_load(f)
                    if isinstance(yd, dict) and "id" in yd:
                        m_id = re.match(r"^lab-(\d+)", str(yd["id"]))
                        if m_id:
                            existing_nums.add(int(m_id.group(1)))
                except Exception:
                    pass

    next_num = max(existing_nums, default=0) + 1
    new_id = f"lab-{next_num:02d}"
    old_id = payload.manifest.id

    title_slug = re.sub(r"[^a-z0-9]+", "-", payload.manifest.title.lower()).strip("-")
    if not title_slug:
        title_slug = "scenario"
    title_slug = title_slug[:30].strip("-")

    new_slug = f"{new_id}-{title_slug}"
    new_distro = f"lplab-{next_num:02d}"

    payload.manifest.id = new_id
    payload.manifest.slug = new_slug
    payload.manifest.distro_name = new_distro

    if old_id and old_id != new_id:
        payload.verify_sh = payload.verify_sh.replace(f'"{old_id}"', f'"{new_id}"')
        payload.verify_sh = payload.verify_sh.replace(f"'{old_id}'", f"'{new_id}'")

    return payload


class AILabGenerator:
    """Generates CompTIA Linux+ labs using an OpenAI-compatible API."""

    def __init__(self, ai_config: AIConfig):
        self.config = ai_config

    def _resolve_api_key(self) -> str:
        """Resolve API key using api_key_env if set, falling back to api_key."""
        if self.config.api_key_env:
            env_val = os.environ.get(self.config.api_key_env)
            if env_val and env_val.strip():
                return env_val.strip()
        return self.config.api_key or "ollama"

    def generate_lab(
        self,
        domain: str,
        topic: str,
        base_image: str = "rockylinux-9",
        max_retries: int = 2,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> GeneratedLabPayload:
        """Generate a complete lab scenario with automatic linting and repair retries."""
        def log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        user_prompt = (
            f"Generate a CompTIA Linux+ XK0-006 lab scenario.\n"
            f"Domain: {domain}\n"
            f"Topic: {topic}\n"
            f"Base Image: {base_image}\n"
            f"Remember: distro_name must start with 'lplab-', verify.sh must output strict JSON only, "
            f"and firewall rules must be scoped to table inet lplab_<slug>."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        attempt = 0
        last_errors: List[str] = []

        api_key = self._resolve_api_key()
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if self.config.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/bpf00010/linuxplus-labs"
            headers["X-Title"] = "lplab"

        url = normalize_chat_completion_url(self.config.base_url, self.config.provider)
        timeout = float(self.config.timeout_seconds)

        while attempt <= max_retries:
            attempt += 1
            if last_errors:
                log(f"Auto-repair attempt {attempt - 1}/{max_retries}...")
                feedback = (
                    "Your previous generation had the following linting/compliance errors:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                    + "\nPlease fix all of these issues and return the corrected JSON object."
                )
                messages.append({"role": "user", "content": feedback})
            else:
                log(f"Connecting to {self.config.provider} ({self.config.model})...")

            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": float(self.config.temperature),
            }

            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    messages.append({"role": "assistant", "content": content})
            except Exception as e:
                raise RuntimeError(f"AI API request failed: {e}")

            log("Parsing lab payload...")
            try:
                parsed_json = extract_json_from_response(content)
                payload_obj = GeneratedLabPayload.model_validate(parsed_json)
            except Exception as e:
                last_errors = [f"JSON schema validation failed: {e}"]
                continue

            log("Running static safety linter & bash -n...")
            lint_errors = SafetyLinter.lint_payload(payload_obj)
            if not lint_errors:
                return payload_obj

            last_errors = lint_errors

        raise ValueError(
            f"Failed to generate a compliant lab after {max_retries} repair retries. "
            f"Last errors: {last_errors}"
        )

    def save_generated_lab(
        self,
        payload: GeneratedLabPayload,
        labs_dir: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Path:
        """Persist generated lab files to labs/<slug>/ with non-colliding numbering."""
        def log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        log("Assigning non-colliding ID and distro name...")
        payload = assign_next_lab_id_and_distro(payload, labs_dir)

        lab_dir = labs_dir / payload.manifest.slug
        lab_dir.mkdir(parents=True, exist_ok=True)

        # Write lab.yaml
        manifest_data = payload.manifest.model_dump()
        with open(lab_dir / "lab.yaml", "w", encoding="utf-8") as f:
            yaml.dump(manifest_data, f, sort_keys=False)

        # Write BRIEF.md
        (lab_dir / "BRIEF.md").write_text(payload.brief_md, encoding="utf-8")

        # Write setup.sh
        setup_file = lab_dir / "setup.sh"
        setup_file.write_text(payload.setup_sh, encoding="utf-8")
        try:
            setup_file.chmod(0o755)
        except Exception:
            pass

        # Write verify.sh
        verify_file = lab_dir / "verify.sh"
        verify_file.write_text(payload.verify_sh, encoding="utf-8")
        try:
            verify_file.chmod(0o755)
        except Exception:
            pass

        log(f"Saved to {lab_dir.name} (distro: {payload.manifest.distro_name})")
        return lab_dir
