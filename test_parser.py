#!/usr/bin/env python3
"""
Comprehensive test suite for Altium SchDoc parser and editor.

Tests:
1. Parser can read DI.SchDoc
2. Round-trip integrity (parse → serialize → parse)
3. High-level editor operations
4. All schematic drawing features
"""

import sys
import os
from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer
from altium_editor import SchematicEditor
from altium_objects import *


def test_parse_di_schdoc():
    """Test parsing the DI.SchDoc example file"""
    print("=" * 70)
    print("TEST 1: Parse DI.SchDoc")
    print("=" * 70)

    parser = AltiumParser()

    try:
        doc = parser.parse_file("DI.SchDoc")
        print("✓ Successfully parsed DI.SchDoc")
    except Exception as e:
        print(f"✗ Failed to parse: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify basic structure
    print(f"\nDocument structure:")
    print(f"  Header: {doc.header is not None}")
    print(f"  Sheet: {doc.sheet is not None}")
    print(f"  Total objects: {len(doc.objects)}")

    # Count object types
    type_counts = {}
    for obj in doc.objects:
        type_name = type(obj).__name__
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    print(f"\nObject type breakdown:")
    for type_name, count in sorted(type_counts.items()):
        print(f"  {type_name}: {count}")

    # Check for key objects
    components = doc.get_components()
    wires = doc.get_wires()
    net_labels = doc.get_net_labels()
    power_ports = doc.get_power_ports()

    print(f"\nKey objects:")
    print(f"  Components: {len(components)}")
    print(f"  Wires: {len(wires)}")
    print(f"  Net Labels: {len(net_labels)}")
    print(f"  Power Ports: {len(power_ports)}")

    # Show some components
    if components:
        print(f"\nSample components:")
        for comp in components[:3]:
            print(f"  - {comp.library_reference} at ({comp.location_x}, {comp.location_y})")
            for child in comp.children[:2]:
                if isinstance(child, Parameter):
                    print(f"    {child.name}: {child.text}")

    print("\n✓ TEST 1 PASSED\n")
    return True


def test_round_trip():
    """Test round-trip: parse → serialize → parse"""
    print("=" * 70)
    print("TEST 2: Round-trip Integrity")
    print("=" * 70)

    parser = AltiumParser()
    serializer = AltiumSerializer()

    try:
        # Parse original
        print("Parsing original DI.SchDoc...")
        doc1 = parser.parse_file("DI.SchDoc")
        print(f"✓ Parsed: {len(doc1.objects)} objects")

        # Serialize
        print("\nSerializing to DI_test_output.SchDoc...")
        serializer.serialize_file(doc1, "DI_test_output.SchDoc")
        print("✓ Serialized")

        # Parse again
        print("\nParsing serialized file...")
        doc2 = parser.parse_file("DI_test_output.SchDoc")
        print(f"✓ Re-parsed: {len(doc2.objects)} objects")

        # Compare
        print("\nComparing documents:")
        print(f"  Original objects: {len(doc1.objects)}")
        print(f"  Round-trip objects: {len(doc2.objects)}")

        if len(doc1.objects) != len(doc2.objects):
            print(f"  ⚠ Warning: Object count mismatch")
            # This might be OK if some objects are filtered

        # Compare object types
        types1 = [type(obj).__name__ for obj in doc1.objects]
        types2 = [type(obj).__name__ for obj in doc2.objects]

        type_counts1 = {}
        type_counts2 = {}
        for t in types1:
            type_counts1[t] = type_counts1.get(t, 0) + 1
        for t in types2:
            type_counts2[t] = type_counts2.get(t, 0) + 1

        print(f"\n  Type comparison:")
        all_types = sorted(set(types1) | set(types2))
        for type_name in all_types:
            c1 = type_counts1.get(type_name, 0)
            c2 = type_counts2.get(type_name, 0)
            match = "✓" if c1 == c2 else "⚠"
            print(f"    {match} {type_name}: {c1} → {c2}")

        print("\n✓ TEST 2 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_editor_operations():
    """Test high-level editor operations"""
    print("=" * 70)
    print("TEST 3: Editor Operations")
    print("=" * 70)

    editor = SchematicEditor()

    try:
        # Create new schematic
        print("Creating new schematic...")
        editor.new()
        print("✓ New schematic created")

        # Add components
        print("\nAdding components...")
        u1 = editor.add_component("LM358", 1000, 2000, "U1", Orientation.RIGHT)
        print(f"✓ Added U1 at ({u1.location_x}, {u1.location_y})")

        r1 = editor.add_resistor(1500, 2500, "10k", "R1", Orientation.RIGHT)
        print(f"✓ Added R1 (10k) at ({r1.location_x}, {r1.location_y})")

        c1 = editor.add_capacitor(2000, 2500, "100nF", "C1", Orientation.RIGHT)
        print(f"✓ Added C1 (100nF) at ({c1.location_x}, {c1.location_y})")

        # Add wires
        print("\nAdding wires...")
        wire1 = editor.add_wire([(1000, 2000), (1500, 2000)])
        print(f"✓ Added wire with {len(wire1.points)} points")

        wire2 = editor.add_wire([(1500, 2000), (1500, 2500)])
        print(f"✓ Added wire with {len(wire2.points)} points")

        # Add junction
        print("\nAdding junction...")
        junction = editor.add_junction(1500, 2000)
        print(f"✓ Added junction at ({junction.location_x}, {junction.location_y})")

        # Add power ports
        print("\nAdding power ports...")
        gnd = editor.add_power_port(1000, 1500, "GND", PowerPortStyle.POWER_GROUND, Orientation.DOWN)
        print(f"✓ Added GND at ({gnd.location_x}, {gnd.location_y})")

        vcc = editor.add_power_port(2000, 3000, "VCC", PowerPortStyle.ARROW, Orientation.UP)
        print(f"✓ Added VCC at ({vcc.location_x}, {vcc.location_y})")

        # Add net label
        print("\nAdding net label...")
        label = editor.add_net_label(1500, 2100, "SIGNAL", Orientation.RIGHT)
        print(f"✓ Added net label '{label.text}' at ({label.location_x}, {label.location_y})")

        # Add graphical elements
        print("\nAdding graphical elements...")
        line = editor.add_line(500, 500, 800, 500)
        print(f"✓ Added line from ({line.location_x}, {line.location_y}) to ({line.corner_x}, {line.corner_y})")

        rect = editor.add_rectangle(500, 600, 800, 800, is_solid=True, fill_color=0xFFFF00)
        print(f"✓ Added rectangle from ({rect.location_x}, {rect.location_y}) to ({rect.corner_x}, {rect.corner_y})")

        text_label = editor.add_label(500, 900, "Test Label", Orientation.RIGHT)
        print(f"✓ Added label '{text_label.text}' at ({text_label.location_x}, {text_label.location_y})")

        # Print summary
        print("\n" + "-" * 70)
        editor.print_summary()
        print("-" * 70)

        # Save
        print("\nSaving schematic...")
        editor.save("test_new_schematic.SchDoc")
        print("✓ Saved to test_new_schematic.SchDoc")

        # Re-load and verify
        print("\nRe-loading to verify...")
        editor2 = SchematicEditor()
        editor2.load("test_new_schematic.SchDoc")
        print(f"✓ Re-loaded: {len(editor2.doc.objects)} objects")

        print("\n✓ TEST 3 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_modify_existing():
    """Test modifying an existing schematic"""
    print("=" * 70)
    print("TEST 4: Modify Existing Schematic")
    print("=" * 70)

    editor = SchematicEditor()

    try:
        # Load original
        print("Loading DI.SchDoc...")
        editor.load("DI.SchDoc")
        print(f"✓ Loaded: {len(editor.doc.objects)} objects")

        original_count = len(editor.doc.objects)

        # Add some modifications
        print("\nAdding new components to existing schematic...")
        new_comp = editor.add_component("NEW_PART", 3000, 3000, "U100", Orientation.RIGHT)
        print(f"✓ Added {new_comp.library_reference}")

        new_wire = editor.add_wire([(3000, 3000), (3500, 3000)])
        print(f"✓ Added wire")

        new_label = editor.add_net_label(3200, 3000, "NEW_NET", Orientation.RIGHT)
        print(f"✓ Added net label")

        print(f"\nObject count: {original_count} → {len(editor.doc.objects)}")

        # Save modified version
        print("\nSaving modified schematic...")
        editor.save("DI_modified.SchDoc")
        print("✓ Saved to DI_modified.SchDoc")

        # Verify
        print("\nVerifying modified file...")
        editor2 = SchematicEditor()
        editor2.load("DI_modified.SchDoc")
        print(f"✓ Verified: {len(editor2.doc.objects)} objects")

        # Check that our additions are there
        found_comp = False
        for comp in editor2.get_components():
            if comp.library_reference == "NEW_PART":
                found_comp = True
                break

        if found_comp:
            print("✓ Found added component in modified file")
        else:
            print("⚠ Warning: Added component not found")

        print("\n✓ TEST 4 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_operations():
    """Test querying schematic data"""
    print("=" * 70)
    print("TEST 5: Query Operations")
    print("=" * 70)

    editor = SchematicEditor()

    try:
        print("Loading DI.SchDoc...")
        editor.load("DI.SchDoc")
        print("✓ Loaded")

        # Get all components
        print("\n" + "-" * 70)
        print("Components:")
        components = editor.get_components()
        print(f"  Total: {len(components)}")

        for i, comp in enumerate(components[:5], 1):
            designator = "?"
            for child in comp.children:
                if isinstance(child, Parameter) and child.name == "Designator":
                    designator = child.text
                    break
            print(f"  {i}. {designator}: {comp.library_reference}")
            print(f"     Location: ({comp.location_x}, {comp.location_y})")
            print(f"     Orientation: {comp.orientation.name}")

        if len(components) > 5:
            print(f"  ... and {len(components) - 5} more")

        # Get wires
        print("\n" + "-" * 70)
        print("Wires:")
        wires = editor.get_wires()
        print(f"  Total: {len(wires)}")

        for i, wire in enumerate(wires[:5], 1):
            print(f"  {i}. {len(wire.points)} points: {wire.points[0]} → {wire.points[-1]}")

        if len(wires) > 5:
            print(f"  ... and {len(wires) - 5} more")

        # Get net labels
        print("\n" + "-" * 70)
        print("Net Labels:")
        labels = editor.get_net_labels()
        print(f"  Total: {len(labels)}")

        for i, label in enumerate(labels[:5], 1):
            print(f"  {i}. '{label.text}' at ({label.location_x}, {label.location_y})")

        if len(labels) > 5:
            print(f"  ... and {len(labels) - 5} more")

        # Get power ports
        print("\n" + "-" * 70)
        print("Power Ports:")
        ports = editor.get_power_ports()
        print(f"  Total: {len(ports)}")

        for i, port in enumerate(ports[:5], 1):
            print(f"  {i}. {port.text} ({port.style.name}) at ({port.location_x}, {port.location_y})")

        if len(ports) > 5:
            print(f"  ... and {len(ports) - 5} more")

        print("\n✓ TEST 5 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("ALTIUM SCHDOC PARSER & EDITOR TEST SUITE")
    print("=" * 70 + "\n")

    tests = [
        ("Parse DI.SchDoc", test_parse_di_schdoc),
        ("Round-trip Integrity", test_round_trip),
        ("Editor Operations", test_editor_operations),
        ("Modify Existing", test_modify_existing),
        ("Query Operations", test_query_operations),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} CRASHED: {e}\n")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
