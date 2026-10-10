"""git CLI wrapper — the only module that knows git (M24 adds GitLab push
options here too).

Auth: the token never appears in a URL, argv, on disk, or in logs. It is
handed to git as an HTTP header via GIT_CONFIG_* env (git >= 2.31), scoped
to the repo's scheme://host[:port]. That also makes git's stderr safe to
surface in errors — the URL carries no credentials (load_config rejects
URLs that do).
"""

import base64
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

TIMEOUT = 300  # seconds per git call; a hung remote must not wedge the poller

# stderr fragments git/hosts emit on a rejected or missing credential
# (GitHub: "could not read Username"; GitLab: "HTTP Basic: Access denied").
_AUTH_FAILURE_MARKERS = ("could not read Username", "Authentication failed", "Access denied", "error: 401", "error: 403")


class GitError(RuntimeError):
    pass


def _env(url: str, token: str | None) -> dict[str, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    parts = urlsplit(url)
    if token and parts.scheme == "https":
        basic = base64.b64encode(f"oauth2:{token}".encode()).decode()
        env |= {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"http.{parts.scheme}://{parts.netloc}/.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}",
        }
    return env


def _run(args: list[str], url: str, token: str | None, cwd: Path | None = None) -> str:
    try:
        r = subprocess.run(
            ["git", *args], cwd=cwd, env=_env(url, token),
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise GitError(f"git {args[0]} timed out after {TIMEOUT}s") from None
    if r.returncode != 0:
        stderr = r.stderr.strip()
        # git's wording for a rejected/missing token is cryptic ("could not
        # read Username ... terminal prompts disabled") — say what to check.
        hint = ""
        if any(m in stderr for m in _AUTH_FAILURE_MARKERS):
            state = "set" if token else "not set"
            hint = (f" — authentication failed: check OHMYDB_ANNOTATIONS_TOKEN ({state}) "
                    "is valid and has read access to the repo")
        raise GitError(f"git {args[0]} failed: {stderr}{hint}")
    return r.stdout


def clone(url: str, ref: str, dest: Path, token: str | None = None) -> str:
    """Shallow single-branch clone of `ref` into `dest`; returns HEAD sha."""
    _run(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", ref, "--", url, str(dest)], url, token)
    return _run(["rev-parse", "HEAD"], url, token, cwd=dest).strip()


def ls_remote(url: str, ref: str, token: str | None = None) -> str:
    """Remote sha of branch `ref`, without fetching anything."""
    out = _run(["ls-remote", url, f"refs/heads/{ref}"], url, token)
    if not out.strip():
        raise GitError(f"branch {ref!r} not found at {url}")
    return out.split()[0]
