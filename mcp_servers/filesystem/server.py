from __future__ import annotations

from pathlib import Path

from platform_core.errors import AppError


class FilesystemMCPServer:
    def __init__(self, allowed_root: Path) -> None:
        self._allowed_root = allowed_root.resolve()

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self._allowed_root / relative_path).resolve()
        if self._allowed_root not in [candidate, *candidate.parents]:
            raise AppError("Path is outside the allowed root", status_code=403)
        return candidate

    def list_files(self, relative_path: str = ".") -> list[str]:
        target = self._resolve(relative_path)
        return sorted(str(path.relative_to(self._allowed_root)) for path in target.iterdir())

    def read_file(self, relative_path: str) -> str:
        target = self._resolve(relative_path)
        if not target.is_file():
            raise AppError("Path is not a file", status_code=400)
        return target.read_text(encoding="utf-8")

    def search_files(self, pattern: str, relative_path: str = ".") -> list[str]:
        target = self._resolve(relative_path)
        return sorted(str(path.relative_to(self._allowed_root)) for path in target.rglob(pattern))
