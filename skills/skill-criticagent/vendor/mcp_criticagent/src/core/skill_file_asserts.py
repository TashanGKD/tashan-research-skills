"""Safe output-file collection for deterministic skill evaluations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


MAX_OUTPUT_FILES = 512
MAX_OUTPUT_FILE_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_TOTAL_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class OutputFile:
    path: str
    content: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "content": self.content,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root)
        return True
    except (OSError, ValueError):
        return False


def read_outputs_dir(outputs_dir: str | Path) -> list[OutputFile]:
    """Read a bounded, symlink-safe text snapshot of an outputs directory."""

    root = Path(outputs_dir).expanduser().resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise ValueError(f"outputs path is not a directory: {root}")

    files: list[OutputFile] = []
    total_bytes = 0
    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        if not _within(root, candidate):
            continue
        if len(files) >= MAX_OUTPUT_FILES:
            raise ValueError(f"outputs directory exceeds {MAX_OUTPUT_FILES} files")
        payload = candidate.read_bytes()
        if len(payload) > MAX_OUTPUT_FILE_BYTES:
            raise ValueError(f"output file is too large: {candidate.relative_to(root)}")
        total_bytes += len(payload)
        if total_bytes > MAX_OUTPUT_TOTAL_BYTES:
            raise ValueError("outputs directory exceeds the total size limit")
        files.append(
            OutputFile(
                path=candidate.relative_to(root).as_posix(),
                content=payload.decode("utf-8", errors="replace"),
                size_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    return files
