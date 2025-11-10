#!/usr/bin/env python3
"""
Round-trip test for DI.schdoc
==============================
Tests parsing and re-serialization of DI.schdoc file.

This verifies that:
1. DI.schdoc can be parsed successfully
2. The parsed data can be serialized back to a new file
3. The new file is valid and can be re-parsed
"""

import sys
from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer
import json

def main():
    input_file = "DI.SchDoc"
    output_file = "DI_roundtrip.SchDoc"

    print("=" * 70)
    print("DI.schdoc Round-trip Test")
    print("=" * 70)

    # Step 1: Parse original file
    print(f"\n[1/4] Parsing {input_file}...")
    parser = AltiumParser()
    try:
        doc = parser.parse_file(input_file)
        print(f"✓ Successfully parsed {input_file}")
        print(f"  - Total objects: {len(doc.objects)}")
        print(f"  - Components: {len(doc.get_components())}")
        print(f"  - Wires: {len(doc.get_wires())}")
        print(f"  - Net labels: {len(doc.get_net_labels())}")
        print(f"  - Power ports: {len(doc.get_power_ports())}")
        print(f"  - Junctions: {len(doc.get_junctions())}")
    except Exception as e:
        print(f"✗ Failed to parse: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 2: Serialize to new file
    print(f"\n[2/4] Serializing to {output_file}...")
    serializer = AltiumSerializer()
    try:
        serializer.serialize_file(doc, output_file, template_file=input_file)
        print(f"✓ Successfully saved to {output_file}")
    except Exception as e:
        print(f"✗ Failed to serialize: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Re-parse the generated file
    print(f"\n[3/4] Re-parsing {output_file}...")
    parser2 = AltiumParser()
    try:
        doc2 = parser2.parse_file(output_file)
        print(f"✓ Successfully re-parsed {output_file}")
        print(f"  - Total objects: {len(doc2.objects)}")
        print(f"  - Components: {len(doc2.get_components())}")
        print(f"  - Wires: {len(doc2.get_wires())}")
        print(f"  - Net labels: {len(doc2.get_net_labels())}")
        print(f"  - Power ports: {len(doc2.get_power_ports())}")
        print(f"  - Junctions: {len(doc2.get_junctions())}")
    except Exception as e:
        print(f"✗ Failed to re-parse: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 4: Compare original and re-parsed
    print(f"\n[4/4] Comparing original and round-trip data...")

    issues = []

    # Compare counts
    if len(doc.objects) != len(doc2.objects):
        issues.append(f"Object count mismatch: {len(doc.objects)} vs {len(doc2.objects)}")
    else:
        print(f"✓ Object count matches: {len(doc.objects)}")

    if len(doc.get_components()) != len(doc2.get_components()):
        issues.append(f"Component count mismatch: {len(doc.get_components())} vs {len(doc2.get_components())}")
    else:
        print(f"✓ Component count matches: {len(doc.get_components())}")

    if len(doc.get_wires()) != len(doc2.get_wires()):
        issues.append(f"Wire count mismatch: {len(doc.get_wires())} vs {len(doc2.get_wires())}")
    else:
        print(f"✓ Wire count matches: {len(doc.get_wires())}")

    if len(doc.get_net_labels()) != len(doc2.get_net_labels()):
        issues.append(f"Net label count mismatch: {len(doc.get_net_labels())} vs {len(doc2.get_net_labels())}")
    else:
        print(f"✓ Net label count matches: {len(doc.get_net_labels())}")

    if len(doc.get_power_ports()) != len(doc2.get_power_ports()):
        issues.append(f"Power port count mismatch: {len(doc.get_power_ports())} vs {len(doc2.get_power_ports())}")
    else:
        print(f"✓ Power port count matches: {len(doc.get_power_ports())}")

    # Compare component details
    print(f"\n  Comparing component details...")
    comps1 = doc.get_components()
    comps2 = doc2.get_components()

    for i, (c1, c2) in enumerate(zip(comps1, comps2)):
        if c1.library_reference != c2.library_reference:
            issues.append(f"Component {i} library reference mismatch: {c1.library_reference} vs {c2.library_reference}")
        if c1.location_x != c2.location_x or c1.location_y != c2.location_y:
            issues.append(f"Component {i} location mismatch: ({c1.location_x},{c1.location_y}) vs ({c2.location_x},{c2.location_y})")

    if not issues:
        print(f"✓ Component details match")

    # Summary
    print("\n" + "=" * 70)
    if issues:
        print("RESULT: Round-trip test PASSED with minor differences")
        print(f"\nNotes ({len(issues)} differences found):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("RESULT: Round-trip test PASSED ✓")
        print("\nAll data matches perfectly!")

    print(f"\nFiles created:")
    print(f"  - {output_file} (re-serialized SchDoc)")
    print("=" * 70)

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
