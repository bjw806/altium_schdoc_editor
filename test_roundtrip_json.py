#!/usr/bin/env python3
"""
JSON-based Round-trip Validation
==================================
Tests parsing accuracy by comparing with JSON data.

This verifies:
1. DI.schdoc can be parsed
2. Parsed data matches DI.json
3. Data integrity is maintained
"""

import json
from altium_parser import AltiumParser

def main():
    print("=" * 70)
    print("DI.schdoc JSON Round-trip Validation")
    print("=" * 70)

    # Parse SchDoc file
    print(f"\n[1/3] Parsing DI.SchDoc...")
    parser = AltiumParser()
    doc = parser.parse_file("DI.SchDoc")
    print(f"✓ Parsed successfully")
    print(f"  - Total objects: {len(doc.objects)}")
    print(f"  - Components: {len(doc.get_components())}")
    print(f"  - Wires: {len(doc.get_wires())}")
    print(f"  - Net labels: {len(doc.get_net_labels())}")
    print(f"  - Power ports: {len(doc.get_power_ports())}")

    # Load reference JSON
    print(f"\n[2/3] Loading reference DI.json...")
    with open("DI.json", 'r') as f:
        ref_data = json.load(f)

    print(f"✓ Loaded reference JSON")
    print(f"  - Components in JSON: {len(ref_data.get('components', []))}")
    print(f"  - Wires in JSON: {len(ref_data.get('wires', []))}")

    # Compare
    print(f"\n[3/3] Comparing parsed data with JSON reference...")

    issues = []
    matches = []

    # Compare component count
    json_comp_count = len(ref_data.get('components', []))
    parsed_comp_count = len(doc.get_components())

    if json_comp_count == parsed_comp_count:
        matches.append(f"Component count: {parsed_comp_count}")
    else:
        issues.append(f"Component count mismatch: JSON has {json_comp_count}, parsed has {parsed_comp_count}")

    # Compare wire count
    json_wire_count = len(ref_data.get('wires', []))
    parsed_wire_count = len(doc.get_wires())

    if json_wire_count == parsed_wire_count:
        matches.append(f"Wire count: {parsed_wire_count}")
    else:
        issues.append(f"Wire count mismatch: JSON has {json_wire_count}, parsed has {parsed_wire_count}")

    # Compare specific components
    print(f"\n  Checking component details...")
    for i, json_comp in enumerate(ref_data.get('components', [])):
        if i >= len(doc.get_components()):
            break

        parsed_comp = doc.get_components()[i]
        json_lib_ref = json_comp.get('libraryReference', '')

        if parsed_comp.library_reference == json_lib_ref:
            matches.append(f"Component {i} library_reference: {json_lib_ref}")
        else:
            issues.append(f"Component {i} mismatch: JSON={json_lib_ref}, Parsed={parsed_comp.library_reference}")

    # Summary
    print("\n" + "=" * 70)
    print(f"VALIDATION RESULTS:")
    print(f"\n✓ Matches: {len(matches)}")
    for match in matches[:5]:  # Show first 5
        print(f"  - {match}")
    if len(matches) > 5:
        print(f"  ... and {len(matches) - 5} more")

    if issues:
        print(f"\n✗ Issues found: {len(issues)}")
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
    else:
        print(f"\n✓ No issues found - perfect match!")

    print("=" * 70)

    # Write parsed data to new JSON for comparison
    print(f"\nSaving parsed data to DI_parsed.json...")
    output_data = {
        "metadata": {
            "total_objects": len(doc.objects),
            "component_count": len(doc.get_components()),
            "wire_count": len(doc.get_wires()),
            "net_label_count": len(doc.get_net_labels()),
            "power_port_count": len(doc.get_power_ports()),
        },
        "components": [
            {
                "library_reference": c.library_reference,
                "location": [c.location_x, c.location_y],
                "designator": c.designator,
            }
            for c in doc.get_components()
        ],
        "wires": [
            {
                "points": w.points,
                "color": w.color,
            }
            for w in doc.get_wires()
        ],
        "net_labels": [
            {
                "text": nl.text,
                "location": [nl.location_x, nl.location_y],
            }
            for nl in doc.get_net_labels()
        ],
    }

    with open("DI_parsed.json", 'w') as f:
        json.dump(output_data, f, indent=2)

    print("✓ Saved to DI_parsed.json")
    print("\nYou can now compare DI.json and DI_parsed.json")

    return len(issues) == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
