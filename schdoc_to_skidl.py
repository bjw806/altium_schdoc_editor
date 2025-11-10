#!/usr/bin/env python3
"""Convert Altium SchDoc files into standalone SKiDL design scripts."""

from __future__ import annotations

import argparse
import json
import pprint
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from json_parser import parse as parse_schdoc

# Mapping from Altium pin electrical codes to SKiDL pin functions.
PIN_FUNC_MAP: Dict[int, str] = {
    0: "Pin.types.INPUT",
    1: "Pin.types.BIDIR",
    2: "Pin.types.OUTPUT",
    3: "Pin.types.OPENCOLL",
    4: "Pin.types.PASSIVE",
    5: "Pin.types.TRISTATE",
    6: "Pin.types.OPENEMIT",
    7: "Pin.types.PWRIN",
}


def augment_record_keys(record: Dict[str, Any]) -> None:
    """Add uppercase/sanitised aliases for record keys in-place."""

    keys = list(record.keys())
    for key in keys:
        if key == "children":
            for child in record["children"]:
                augment_record_keys(child)
            continue
        value = record[key]
        upper = key.upper()
        if upper not in record:
            record[upper] = value
        dotted = key.replace(".", "_").upper()
        if dotted not in record:
            record[dotted] = value
    if "index" in record:
        try:
            idx = int(record["index"])
            record["index"] = idx
            record.setdefault("INDEX", idx)
        except (TypeError, ValueError):
            pass


def walk_records(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    """Yield each record in the hierarchy."""

    for record in records:
        yield record
        for child in record.get("children", []):
            yield from walk_records([child])


def py_string(value: str | None) -> str:
    """Return a Python string literal for ``value``."""

    if value is None:
        value = ""
    return json.dumps(value)


def sanitize_identifier(name: str, prefix: str, used: set[str]) -> str:
    """Sanitise ``name`` to a valid, unique Python identifier."""

    cleaned = re.sub(r"\W+", "_", name)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}" if cleaned else prefix
    while cleaned in used:
        cleaned = f"{cleaned}_"
    used.add(cleaned)
    return cleaned


def map_pin_function(raw_value: Any) -> Tuple[str, str]:
    """Map an Altium electrical code to (SKiDL expression, label)."""

    try:
        code = int(raw_value)
    except (TypeError, ValueError):
        return "Pin.types.UNSPEC", "UNSPEC"
    return PIN_FUNC_MAP.get(code, "Pin.types.UNSPEC"), {
        0: "INPUT",
        1: "BIDIR",
        2: "OUTPUT",
        3: "OPENCOLL",
        4: "PASSIVE",
        5: "TRISTATE",
        6: "OPENEMIT",
        7: "PWRIN",
    }.get(code, "UNSPEC")


def extract_component(record: Dict[str, Any]) -> Dict[str, Any]:
    """Extract component metadata and pins from a RECORD=1 entry."""

    ref = ""
    value = ""
    footprint = ""
    pins: List[Dict[str, str]] = []

    for child in record.get("children", []):
        rec_type = child.get("RECORD")
        if rec_type == "34":
            ref = child.get("TEXT") or child.get("NAME") or ref
        elif rec_type == "41":
            name = (child.get("NAME") or "").upper()
            if name == "VALUE" and child.get("TEXT"):
                value = child["TEXT"]
            elif name == "COMMENT" and child.get("TEXT") and not value:
                value = child["TEXT"]
            elif name == "DESIGNATOR" and child.get("TEXT") and not ref:
                ref = child["TEXT"]
        elif rec_type == "45":
            footprint = child.get("MODELDATAFILEENTITY0") or child.get("MODELNAME") or footprint
        elif rec_type == "2":
            num = child.get("DESIGNATOR") or child.get("PINNUMBER") or child.get("NAME") or str(len(pins) + 1)
            pin_name = child.get("NAME") or ""
            func_expr, func_label = map_pin_function(child.get("ELECTRICAL"))
            pins.append({
                "num": str(num),
                "name": pin_name,
                "func_expr": func_expr,
                "func_label": func_label,
            })

    return {
        "index": record.get("index"),
        "ref": ref or record.get("LIBREFERENCE") or "U?",
        "library_reference": record.get("LIBREFERENCE") or "",
        "source_library": record.get("SOURCELIBRARYNAME") or "",
        "value": value or record.get("COMPONENTDESCRIPTION") or "",
        "footprint": footprint,
        "pins": pins,
    }


def collect_components(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """Return all components and a map from index to record."""

    components: List[Dict[str, Any]] = []
    index_map: Dict[int, Dict[str, Any]] = {}

    for record in walk_records(records):
        idx = record.get("index")
        if isinstance(idx, int):
            index_map[idx] = record
        if record.get("RECORD") == "1":
            comp = extract_component(record)
            components.append(comp)
    return components, index_map


def generate_part_metadata(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a serialisable metadata dictionary for parts."""

    metadata: Dict[str, Any] = {}
    for comp in components:
        metadata[comp["ref"]] = {
            "library_reference": comp["library_reference"],
            "source_library": comp["source_library"],
            "value": comp["value"],
            "footprint": comp["footprint"],
            "pin_count": len(comp["pins"]),
            "pins": [
                {
                    "num": pin["num"],
                    "name": pin["name"],
                    "type": pin["func_label"],
                }
                for pin in comp["pins"]
            ],
        }
    return metadata


def collect_nets(net_entries: List[Dict[str, Any]], component_map: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract net connectivity information and merge duplicate entries."""

    nets: List[Dict[str, Any]] = []

    for idx, net in enumerate(net_entries or []):
        raw_name = net.get("name")
        connections: List[Tuple[str, str]] = []

        for device in net.get("devices", []):
            rec_type = device.get("RECORD")
            if rec_type == "2":
                owner = device.get("OWNERINDEX") or device.get("OWNER_INDEX")
                try:
                    owner_idx = int(owner)
                except (TypeError, ValueError):
                    continue
                component = component_map.get(owner_idx)
                if not component:
                    continue
                comp_ref = component.get("ref")
                pin_num = device.get("DESIGNATOR") or device.get("PINNUMBER") or device.get("NAME")
                if not comp_ref or not pin_num:
                    continue
                connections.append((str(comp_ref), str(pin_num)))
            elif rec_type in {"17", "25"} and not raw_name:
                raw_name = device.get("TEXT") or device.get("NAME")

        unique_connections = sorted(set(connections))
        display_name = raw_name or (
            f"Net{unique_connections[0][0]}_{unique_connections[0][1]}"
            if unique_connections
            else f"Net_{idx}"
        )

        nets.append({
            "raw_name": raw_name,
            "display_name": display_name,
            "connections": unique_connections,
        })

    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for entry in nets:
        key = entry["display_name"]
        if key not in merged:
            merged[key] = {
                "raw_name": entry["raw_name"],
                "display_name": key,
                "connections": list(entry["connections"]),
            }
            order.append(key)
            continue
        existing = merged[key]
        existing_conn = {tuple(conn) for conn in existing["connections"]}
        existing_conn.update(entry["connections"])
        existing["connections"] = sorted(existing_conn)
        if not existing["raw_name"] and entry["raw_name"]:
            existing["raw_name"] = entry["raw_name"]

    return [merged[name] for name in order]
    return nets


def generate_net_metadata(nets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build metadata for nets."""

    metadata: Dict[str, Any] = {}
    for entry in nets:
        key = entry["display_name"]
        metadata[key] = {
            "source_name": entry["raw_name"],
            "connection_count": len(entry["connections"]),
            "connections": [
                {"ref": ref, "pin": pin}
                for ref, pin in entry["connections"]
            ],
        }
    return metadata


def render_skidl(
    components: List[Dict[str, Any]],
    nets: List[Dict[str, Any]],
    part_metadata: Dict[str, Any],
    net_metadata: Dict[str, Any],
    output_path: Path,
) -> str:
    """Render the SKiDL Python script."""

    used_names: set[str] = set()
    for comp in sorted(components, key=lambda c: c["ref"]):
        comp["var_name"] = sanitize_identifier(comp["ref"], "part", used_names)
    for net in nets:
        net["var_name"] = sanitize_identifier(net["display_name"], "net", used_names)

    part_meta_literal = pprint.pformat(part_metadata, sort_dicts=True, width=120)
    net_meta_literal = pprint.pformat(net_metadata, sort_dicts=True, width=120)

    stem = output_path.stem.split("_skidl")[0]
    default_netlist = f"{stem}.net"
    default_pcb = f"{stem}.kicad_pcb"

    lines: List[str] = []
    lines.append("\"\"\"\nAuto-generated SKiDL circuit extracted from an Altium SchDoc file.\n\"\"\"")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import argparse")
    lines.append("from pathlib import Path")
    lines.append("from typing import Any, Dict")
    lines.append("")
    lines.append(
        "from skidl import (Circuit, Net, Part, Pin, TEMPLATE, SKIDL, KICAD8, ERC, reset, set_default_tool)"
    )
    lines.append("from skidl.logger import active_logger")
    lines.append("")
    lines.append(f"DEFAULT_NETLIST_FILE = {py_string(default_netlist)}")
    lines.append(f"DEFAULT_PCB_FILE = {py_string(default_pcb)}")
    lines.append("")
    lines.append(f"PART_METADATA: Dict[str, Dict[str, Any]] = {part_meta_literal}")
    lines.append("")
    lines.append(f"NET_METADATA: Dict[str, Dict[str, Any]] = {net_meta_literal}")
    lines.append("")
    lines.append("def build_circuit() -> Dict[str, Any]:")
    lines.append("    \"\"\"Build the SKiDL circuit and return helpers for analysis.\"\"\"")
    lines.append("    reset()")
    lines.append("    circuit = Circuit()")
    lines.append("    nets: Dict[str, Net] = {}")
    lines.append("    parts: Dict[str, Part] = {}")
    lines.append("    with circuit:")
    lines.append("        set_default_tool(KICAD8)")

    # Net declarations.
    lines.append("        # Net declarations")
    for net in sorted(nets, key=lambda n: n["display_name"]):
        var = net["var_name"]
        display_name = net["display_name"]
        lines.append(f"        {var} = Net({py_string(display_name)})")
        lines.append(f"        {var}.tag = {py_string(display_name)}")
        lines.append(f"        nets[{py_string(display_name)}] = {var}")

    # Component declarations.
    lines.append("\n        # Component templates and instances")
    for comp in sorted(components, key=lambda c: c["ref"]):
        var = comp["var_name"]
        pins_repr = ",\n            ".join(
            f"Pin(num={py_string(pin['num'])}, name={py_string(pin['name'])}, func={pin['func_expr']})"
            for pin in comp["pins"]
        ) or "Pin(num=\"1\", name=\"\", func=Pin.types.UNSPEC)"
        lines.append(
            f"        {var} = Part(name={py_string(comp['library_reference'] or comp['ref'])}, dest=TEMPLATE, tool=SKIDL, pins=[\n            {pins_repr}\n        ])(ref={py_string(comp['ref'])}, value={py_string(comp['value'])})"
        )
        lines.append(f"        {var}.tool = KICAD8")
        lines.append(f"        {var}.tag = {py_string(comp['ref'])}")
        if comp.get("footprint"):
            lines.append(f"        {var}.footprint = {py_string(comp['footprint'])}")
        lines.append(f"        parts[{py_string(comp['ref'])}] = {var}")

    # Net connections.
    lines.append("\n        # Net connections")
    for net in sorted(nets, key=lambda n: n["display_name"]):
        var = net["var_name"]
        if not net["connections"]:
            continue
        lines.append(f"        # Connections for {net['display_name']}")
        for ref, pin in net["connections"]:
            comp = next((c for c in components if c["ref"] == ref), None)
            if not comp:
                continue
            lines.append(
                f"        {var} += {comp['var_name']}[{py_string(pin)}]"
            )

    lines.append("    return {\"circuit\": circuit, \"nets\": nets, \"parts\": parts}")
    lines.append("")

    # Export helper.
    lines.append("def export_to_kicad(netlist_path: str | None = DEFAULT_NETLIST_FILE, pcb_path: str | None = DEFAULT_PCB_FILE, run_erc: bool = True) -> None:")
    lines.append("    \"\"\"Run ERC and export KiCad artefacts from the generated circuit.\"\"\"")
    lines.append("    data = build_circuit()")
    lines.append("    circuit = data['circuit']")
    lines.append("    set_default_tool(KICAD8)")
    lines.append("    import skidl")
    lines.append("    def _suppress_empty_footprint(part):")
    lines.append("        active_logger.warning(f'No footprint assigned to {part.ref} ({part.name}).')")
    lines.append("    skidl.empty_footprint_handler = _suppress_empty_footprint")
    lines.append("    for part in circuit.parts:")
    lines.append("        part.tool = KICAD8")
    lines.append("        if not getattr(part, 'tag', None):")
    lines.append("            part.tag = part.ref")
    lines.append("    for net in circuit.nets:")
    lines.append("        if not getattr(net, 'tag', None):")
    lines.append("            net.tag = net.name")
    lines.append("    if run_erc:")
    lines.append("        circuit.ERC()")
    lines.append("    if netlist_path:")
    lines.append("        path = Path(netlist_path)")
    lines.append("        circuit.generate_netlist(file_=str(path), tool=KICAD8, do_backup=False)")
    lines.append("    if pcb_path:")
    lines.append("        try:")
    lines.append("            path = Path(pcb_path)")
    lines.append("            circuit.generate_pcb(file_=str(path), tool=KICAD8, do_backup=False)")
    lines.append("        except Exception as exc:")
    lines.append("            print(f'PCB export failed: {exc}')")
    lines.append("")

    # CLI entry point.
    lines.append("def main() -> None:")
    lines.append("    parser = argparse.ArgumentParser(description='Generate KiCad outputs from this SKiDL design.')")
    lines.append("    parser.add_argument('--netlist', default=DEFAULT_NETLIST_FILE, help='Output KiCad netlist file path.')")
    lines.append("    parser.add_argument('--pcb', default=None, help='Optional KiCad PCB file path to generate.')")
    lines.append("    parser.add_argument('--skip-erc', action='store_true', help='Skip electrical rule check before export.')")
    lines.append("    args = parser.parse_args()")
    lines.append("    export_to_kicad(netlist_path=args.netlist, pcb_path=args.pcb, run_erc=not args.skip_erc)")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    main()")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert an Altium SchDoc into a SKiDL Python script.")
    parser.add_argument("input", help="Path to the .SchDoc file to convert.")
    parser.add_argument(
        "--output",
        help="Path for the generated SKiDL script (default: <stem>_skidl.py).",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = Path(args.output).resolve() if args.output else input_path.with_name(f"{input_path.stem}_skidl.py")

    hierarchy = parse_schdoc(str(input_path), format="all-hierarchy")
    for record in hierarchy.get("records", []):
        augment_record_keys(record)

    components, _ = collect_components(hierarchy.get("records", []))
    component_index_map: Dict[int, Dict[str, Any]] = {}
    for comp in components:
        idx = comp.get("index")
        if isinstance(idx, int):
            component_index_map[idx] = comp

    net_data = parse_schdoc(str(input_path), format="net-list")
    nets = collect_nets(net_data.get("nets", []), component_index_map)

    part_metadata = generate_part_metadata(components)
    net_metadata = generate_net_metadata(nets)

    skidl_code = render_skidl(components, nets, part_metadata, net_metadata, output_path)
    output_path.write_text(skidl_code, encoding="utf-8")
    print(f"Wrote SKiDL design to {output_path}")


if __name__ == "__main__":
    main()
