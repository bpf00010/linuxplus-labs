"""AI lab scenario generator and static safety linter."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple
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


def extract_json_from_response(text: str) -> dict:
    """Extract valid JSON from LLM markdown code blocks or raw text."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try extracting markdown ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # Search between outermost curly brackets
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(f"Could not parse valid JSON from AI response: {text[:200]}...")


class AILabGenerator:
    """Generates CompTIA Linux+ labs using an OpenAI-compatible API."""

    def __init__(self, ai_config: AIConfig):
        self.config = ai_config

    def generate_lab(
        self,
        domain: str,
        topic: str,
        base_image: str = "rockylinux-9",
        max_retries: int = 2,
    ) -> GeneratedLabPayload:
        """Generate a complete lab scenario with automatic linting and repair retries."""
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

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        while attempt <= max_retries:
            attempt += 1
            if last_errors:
                # Add correction feedback
                feedback = (
                    "Your previous generation had the following linting/compliance errors:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                    + "\nPlease fix all of these issues and return the corrected JSON object."
                )
                messages.append({"role": "user", "content": feedback})

            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.4,
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    messages.append({"role": "assistant", "content": content})
            except Exception as e:
                raise RuntimeError(f"AI API request failed: {e}")

            # Parse and validate schema
            try:
                parsed_json = extract_json_from_response(content)
                payload_obj = GeneratedLabPayload.model_validate(parsed_json)
            except Exception as e:
                last_errors = [f"JSON schema validation failed: {e}"]
                continue

            # Run safety linter
            lint_errors = SafetyLinter.lint_payload(payload_obj)
            if not lint_errors:
                return payload_obj

            last_errors = lint_errors

        raise ValueError(
            f"Failed to generate a compliant lab after {max_retries} repair retries. "
            f"Last errors: {last_errors}"
        )

    def save_generated_lab(self, payload: GeneratedLabPayload, labs_dir: Path) -> Path:
        """Persist generated lab files to labs/<slug>/."""
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

        return lab_dir
