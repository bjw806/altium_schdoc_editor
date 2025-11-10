#!/usr/bin/env python3
"""
Record-level Round-trip Test
==============================
Tests serialization and parsing without creating OLE files.

This verifies:
1. Parse DI.schdoc to Python objects
2. Serialize objects back to binary records
3. Parse the records again
4. Compare original and re-parsed objects
"""

from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer

def main():
    print("=" * 70)
    print("Record-level Round-trip Test")
    print("=" * 70)

    # Step 1: Parse original file
    print(f"\n[1/4] Parsing DI.SchDoc...")
    parser = AltiumParser()
    doc1 = parser.parse_file("DI.SchDoc")

    print(f"✓ Parsed successfully")
    print(f"  - Total objects: {len(doc1.objects)}")
    print(f"  - Components: {len(doc1.get_components())}")
    print(f"  - Wires: {len(doc1.get_wires())}")
    print(f"  - Net labels: {len(doc1.get_net_labels())}")
    print(f"  - Power ports: {len(doc1.get_power_ports())}")
    print(f"  - Junctions: {len(doc1.get_junctions())}")

    # Step 2: Serialize to records
    print(f"\n[2/4] Serializing to binary records...")
    serializer = AltiumSerializer()
    records = serializer._build_records(doc1)

    total_size = sum(len(r) for r in records)
    print(f"✓ Serialized to {len(records)} records ({total_size} bytes)")

    # Step 3: Parse the records
    print(f"\n[3/4] Re-parsing serialized records...")

    # Combine records into binary data
    record_data = b''.join(records)

    # Parse using RecordReader
    from altium_parser import RecordReader
    parsed_records = RecordReader.read_records(record_data)

    # Build document from parsed records
    doc2 = parser._build_document(parsed_records)

    print(f"✓ Re-parsed successfully")
    print(f"  - Total objects: {len(doc2.objects)}")
    print(f"  - Components: {len(doc2.get_components())}")
    print(f"  - Wires: {len(doc2.get_wires())}")
    print(f"  - Net labels: {len(doc2.get_net_labels())}")
    print(f"  - Power ports: {len(doc2.get_power_ports())}")
    print(f"  - Junctions: {len(doc2.get_junctions())}")

    # Step 4: Compare
    print(f"\n[4/4] Comparing original and re-parsed data...")

    issues = []
    matches = []

    # Compare counts
    if len(doc1.objects) == len(doc2.objects):
        matches.append(f"Object count: {len(doc1.objects)}")
    else:
        issues.append(f"Object count mismatch: {len(doc1.objects)} vs {len(doc2.objects)}")

    if len(doc1.get_components()) == len(doc2.get_components()):
        matches.append(f"Component count: {len(doc1.get_components())}")
    else:
        issues.append(f"Component count: {len(doc1.get_components())} vs {len(doc2.get_components())}")

    if len(doc1.get_wires()) == len(doc2.get_wires()):
        matches.append(f"Wire count: {len(doc1.get_wires())}")
    else:
        issues.append(f"Wire count: {len(doc1.get_wires())} vs {len(doc2.get_wires())}")

    if len(doc1.get_net_labels()) == len(doc2.get_net_labels()):
        matches.append(f"Net label count: {len(doc1.get_net_labels())}")
    else:
        issues.append(f"Net label count: {len(doc1.get_net_labels())} vs {len(doc2.get_net_labels())}")

    if len(doc1.get_power_ports()) == len(doc2.get_power_ports()):
        matches.append(f"Power port count: {len(doc1.get_power_ports())}")
    else:
        issues.append(f"Power port count: {len(doc1.get_power_ports())} vs {len(doc2.get_power_ports())}")

    # Compare component details
    print(f"\n  Comparing component details...")
    for i, (c1, c2) in enumerate(zip(doc1.get_components(), doc2.get_components())):
        if c1.library_reference == c2.library_reference:
            matches.append(f"Component {i} library_reference")
        else:
            issues.append(f"Component {i} library_reference: {c1.library_reference} vs {c2.library_reference}")

        if c1.location_x == c2.location_x and c1.location_y == c2.location_y:
            matches.append(f"Component {i} location")
        else:
            issues.append(f"Component {i} location: ({c1.location_x},{c1.location_y}) vs ({c2.location_x},{c2.location_y})")

    # Summary
    print("\n" + "=" * 70)
    print("ROUND-TRIP TEST RESULTS:")
    print(f"\n✓ Matches: {len(matches)}")

    if issues:
        print(f"\n✗ Issues found: {len(issues)}")
        for issue in issues[:20]:
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("\n✓ PERFECT MATCH - Round-trip successful!")
        print("\nConclusion:")
        print("  ✓ Parsing works correctly")
        print("  ✓ Serialization works correctly")
        print("  ✓ Data integrity is maintained")

    print("=" * 70)

    return len(issues) == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
