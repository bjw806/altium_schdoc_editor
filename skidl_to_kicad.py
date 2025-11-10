#!/usr/bin/env python3
"""Execute a SKiDL design script and export KiCad artefacts."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any


def load_env_vars() -> None:
    """Populate os.environ from a local .env before importing SKiDL."""

    # Resolve the repository root relative to this script to avoid cwd assumptions.
    scripts_dir = Path(__file__).resolve().parent
    env_path = scripts_dir / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key and value:
            os.environ.setdefault(key, value)

    # SKiDL looks for versioned KiCad variables when the generic one is set.
    os.environ.setdefault("KICAD_DISABLE_ACTION_PLUGINS", "1")

    generic_symbol_dir = os.environ.get("KICAD_SYMBOL_DIR")
    if generic_symbol_dir:
        generic_symbol_path = Path(generic_symbol_dir)
        for version in ("6", "7", "8", "9"):
            os.environ.setdefault(f"KICAD{version}_SYMBOL_DIR", generic_symbol_dir)

        # Derive KiCad installation directories to resolve pcbnew imports when possible.
        try:
            kicad_root = generic_symbol_path.parents[2]
        except IndexError:
            kicad_root = None

        if kicad_root and kicad_root.exists():
            bin_dir = kicad_root / "bin"
            if bin_dir.exists():
                path_entries = os.environ.get("PATH", "").split(os.pathsep) if os.environ.get("PATH") else []
                if str(bin_dir) not in path_entries:
                    os.environ["PATH"] = os.pathsep.join([str(bin_dir)] + path_entries)
                if str(bin_dir) not in sys.path:
                    sys.path.insert(0, str(bin_dir))

                site_packages = bin_dir / "Lib" / "site-packages"
                if site_packages.exists() and str(site_packages) not in sys.path:
                    sys.path.insert(0, str(site_packages))

    generic_footprint_dir = os.environ.get("KICAD_FOOTPRINT_DIR")
    if not generic_footprint_dir and generic_symbol_dir:
        # Assume standard KiCad layout if footprints are not specified explicitly.
        footprint_path = Path(generic_symbol_dir).parent / "footprints"
        if footprint_path.exists():
            os.environ.setdefault("KICAD_FOOTPRINT_DIR", str(footprint_path))
            for version in ("6", "7", "8", "9"):
                os.environ.setdefault(f"KICAD{version}_FOOTPRINT_DIR", str(footprint_path))


load_env_vars()

def load_module(skidl_path: Path):
    """Dynamically import the SKiDL script as a module."""

    spec = importlib.util.spec_from_file_location(skidl_path.stem, skidl_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load SKiDL module from {skidl_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_output(default: str | None, override: str | None, fallback: str | None) -> str | None:
    """Pick the effective output path with sensible fallbacks."""

    if override is not None:
        return override
    if default:
        return default
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a SKiDL script and export KiCad outputs.")
    parser.add_argument("skidl", help="Path to the generated SKiDL Python file.")
    parser.add_argument("--netlist", help="Override the netlist output path.")
    parser.add_argument("--pcb", help="Optional KiCad PCB output path.")
    parser.add_argument("--skip-erc", action="store_true", help="Skip electrical rule check before exporting.")
    args = parser.parse_args()

    skidl_path = Path(args.skidl).resolve()
    if not skidl_path.exists():
        raise FileNotFoundError(f"SKiDL file not found: {skidl_path}")

    load_env_vars()

    import skidl
    from skidl import ERC, generate_netlist, generate_pcb, reset, set_default_tool

    default_tool = getattr(skidl, "KICAD8", getattr(skidl, "KICAD", None))

    module = load_module(skidl_path)

    default_netlist = getattr(module, "DEFAULT_NETLIST_FILE", None)
    default_pcb = getattr(module, "DEFAULT_PCB_FILE", None)

    netlist_path = resolve_output(default_netlist, args.netlist, skidl_path.with_suffix(".net").as_posix())
    pcb_path = resolve_output(default_pcb, args.pcb, None)

    if hasattr(module, "export_to_kicad"):
        module.export_to_kicad(netlist_path=netlist_path, pcb_path=pcb_path, run_erc=not args.skip_erc)
        return

    if not hasattr(module, "build_circuit"):
        raise AttributeError("SKiDL module must define build_circuit() or export_to_kicad().")

    reset()
    result: Any = module.build_circuit()
    circuit = result.get("circuit") if isinstance(result, dict) else result
    if circuit is None:
        raise RuntimeError("build_circuit() did not return a Circuit instance.")

    if default_tool is not None:
        set_default_tool(default_tool)
    if not args.skip_erc:
        ERC()
    if netlist_path:
        generate_netlist(file_=str(netlist_path))
    if pcb_path:
        try:
            generate_pcb(file_=str(pcb_path))
        except Exception as exc:
            print(f"PCB export failed: {exc}")


if __name__ == "__main__":
    main()
