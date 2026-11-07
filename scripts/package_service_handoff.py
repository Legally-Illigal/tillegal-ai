"""Create a no-secret source snapshot and an incremental patch against the local pre-M4 snapshot."""

import argparse
import difflib
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOTS = ("src", "tests", "scripts", "configs", "deployments", ".docs", ".github")
ROOT_FILES = (
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".gitignore",
    ".env.example",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
)
EXTENSIONS = {".py", ".md", ".toml", ".lock", ".yaml", ".yml", ".json", ".sql", ".txt"}
SENSITIVE = re.compile(rb"AIza[0-9A-Za-z_-]{35}|sk-[0-9A-Za-z_-]{24,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package(service, before, output):
    if output.exists():
        raise ValueError("Output must be new")
    files = {}
    for name in ROOT_FILES:
        path = service / name
        if path.is_file():
            files[name] = path.read_bytes()
    for directory in ROOTS:
        for path in (service / directory).rglob("*"):
            if (
                path.is_file()
                and path.suffix in EXTENSIONS
                and not any(p in {".git", ".venv", "__pycache__", ".pytest_cache"} for p in path.parts)
                and not path.name.startswith(".env")
            ):
                files[path.relative_to(service).as_posix()] = path.read_bytes()
    for name, data in files.items():
        if SENSITIVE.search(data):
            raise ValueError("Possible credential in " + name)
    diff = []
    changed = {}
    for name, data in sorted(files.items()):
        if not (name.startswith(("src/", "tests/", "scripts/")) or name == "pyproject.toml"):
            continue
        old_path = before / name
        old = old_path.read_bytes() if old_path.is_file() else b""
        if old == data:
            continue
        changed[name] = {"before_sha256": sha(old) if old_path.is_file() else None, "after_sha256": sha(data)}
        diff.extend(
            difflib.unified_diff(
                old.decode("utf8").splitlines(keepends=True),
                data.decode("utf8").splitlines(keepends=True),
                fromfile="a/" + name if old_path.is_file() else "/dev/null",
                tofile="b/" + name,
            )
        )
    manifest = {
        "format": "local-source-handoff-v1",
        "team_git_base": "UNKNOWN",
        "parent_repo_is_not_team_repo": True,
        "files": {name: sha(data) for name, data in sorted(files.items())},
        "incremental_changes": changed,
        "excluded": "secrets, caches, model weights, corpus artifacts, git metadata",
    }
    output.mkdir(parents=True)
    with zipfile.ZipFile(output / "service-source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
        archive.writestr("HANDOFF_MANIFEST.json", json.dumps(manifest, indent=2))
    (output / "m4.patch").write_bytes("".join(diff).encode("utf8"))
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
    # Read every ZIP member back and compare byte hashes before declaring it usable.
    with zipfile.ZipFile(output / "service-source.zip") as archive:
        for name, digest in manifest["files"].items():
            if sha(archive.read(name)) != digest:
                raise ValueError("Archive checksum mismatch")
    (output / "SHA256SUMS.txt").write_text(
        "\n".join(
            sha((output / n).read_bytes()) + "  " + n for n in ("service-source.zip", "m4.patch", "manifest.json")
        )
        + "\n",
        encoding="utf8",
    )
    print(len(files), "files verified;", len(changed), "incremental changes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("service", "before", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    package(args.service, args.before, args.output)
