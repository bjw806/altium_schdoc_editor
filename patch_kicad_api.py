"""
Utility script to patch kicad_sch_api for non-snapping coordinates and Net hashing.

- components.py: respect `ksa.config.positioning.grid_size` (allow 0 to disable snapping)
- connectivity.py: add `Net.__hash__` so Net instances can be stored in sets/dicts

다른 환경에서도 `python patch_kicad_api.py`만 실행하면 동일한 패치를 적용할 수 있습니다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent


def _patch_text(text: str, original: str, replacement: str, label: str) -> str:
    """Replace a block of text, raising a helpful error if it does not match."""
    if replacement.strip() in text:
        print(f"[skip] {label} 이미 패치됨")
        return text

    if original.strip() not in text:
        raise RuntimeError(f"[fail] {label}: 원본 블록을 찾을 수 없습니다. API 버전이 다른지 확인하세요.")

    return text.replace(original, replacement, 1)


def patch_components(components_path: Path):
    original = dedent(
        """
                # Always snap component position to KiCAD grid (1.27mm = 50mil)
                from ..core.geometry import snap_to_grid

                snapped_pos = snap_to_grid((position.x, position.y), grid_size=1.27)
                position = Point(snapped_pos[0], snapped_pos[1])
        """
    ).strip()

    replacement = dedent(
        """
                # Always snap component position to KiCAD grid unless disabled
                from ..core.geometry import snap_to_grid

                snap_grid = getattr(config.positioning, "grid_size", 1.27)
                if snap_grid and snap_grid > 0:
                    snapped_pos = snap_to_grid((position.x, position.y), grid_size=snap_grid)
                    position = Point(snapped_pos[0], snapped_pos[1])
                else:
                    # Preserve exact coordinates when snap grid is zero/disabled
                    position = Point(position.x, position.y)
        """
    ).strip()

    text = components_path.read_text(encoding="utf-8")
    updated = _patch_text(text, original, replacement, "components.py grid snap")

    if updated != text:
        components_path.write_text(updated, encoding="utf-8")
        print(f"[ok] {components_path} 패치 완료")


def patch_connectivity(connectivity_path: Path):
    original = dedent(
        """
        def __repr__(self):
            name_str = f"'{{self.name}}'" if self.name else "unnamed"
            return f"Net({{name_str}}, {{len(self.pins)}} pins, {{len(self.wires)}} wires)"
        """
    ).strip()

    replacement = dedent(
        """
        def __repr__(self):
            name_str = f"'{{self.name}}'" if self.name else "unnamed"
            return f"Net({{name_str}}, {{len(self.pins)}} pins, {{len(self.wires)}} wires)"

        def __hash__(self):
            \"\"\"
            Allow Net instances to participate in sets/dicts.

            Nets are mutable, so we base the hash on object identity which is
            stable for the lifetime of the instance and sufficient for detecting
            duplicate references during connectivity merging.
            \"\"\"
            return id(self)
        """
    ).strip()

    text = connectivity_path.read_text(encoding="utf-8")
    updated = _patch_text(text, original, replacement, "connectivity.py Net.__hash__")

    if updated != text:
        connectivity_path.write_text(updated, encoding="utf-8")
        print(f"[ok] {connectivity_path} 패치 완료")


def locate_module_root() -> Path:
    try:
        import kicad_sch_api  # type: ignore
    except ImportError as exc:
        raise SystemExit("kicad_sch_api를 import 할 수 없습니다. 가상환경이 활성화됐는지 확인하세요.") from exc

    return Path(kicad_sch_api.__file__).resolve().parent


def main():
    module_root = locate_module_root()

    components_path = module_root / "collections" / "components.py"
    connectivity_path = module_root / "core" / "connectivity.py"

    if not components_path.exists() or not connectivity_path.exists():
        raise SystemExit("kicad_sch_api 파일을 찾을 수 없습니다. 설치 경로를 확인하세요.")

    patch_components(components_path)
    patch_connectivity(connectivity_path)
    print("모든 패치가 완료되었습니다.")


if __name__ == "__main__":
    sys.exit(main())
