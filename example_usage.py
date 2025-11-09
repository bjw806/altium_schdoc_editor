#!/usr/bin/env python3
"""
Example Usage of Altium SchDoc Editor
======================================
Demonstrates key features of the library for LLM usage.
"""

from altium_editor import SchematicEditor
from altium_objects import Orientation, PowerPortStyle, color_to_rgb, rgb_to_color


def example_1_parse_and_analyze():
    """Example 1: Parse and analyze an existing schematic"""
    print("=" * 70)
    print("Example 1: Parse and Analyze Existing Schematic")
    print("=" * 70)

    editor = SchematicEditor()
    editor.load("DI.SchDoc")

    # Print summary
    print("\nSchematic Summary:")
    editor.print_summary()

    # Show first few components with details
    print("\nComponent Details:")
    for i, comp in enumerate(editor.get_components()[:3], 1):
        print(f"\n{i}. Library: {comp.library_reference}")
        print(f"   Position: ({comp.location_x}, {comp.location_y})")
        print(f"   Orientation: {comp.orientation.name}")

        # Show parameters
        for child in comp.children[:3]:
            if hasattr(child, 'name') and hasattr(child, 'text'):
                print(f"   {child.name}: {child.text}")

    # Show nets
    print("\nNet Labels:")
    for i, label in enumerate(editor.get_net_labels()[:5], 1):
        print(f"{i}. {label.text} at ({label.location_x}, {label.location_y})")

    print("\n" + "=" * 70 + "\n")


def example_2_create_new_schematic():
    """Example 2: Create a new schematic from scratch"""
    print("=" * 70)
    print("Example 2: Create New Schematic")
    print("=" * 70)

    editor = SchematicEditor()
    editor.new()

    print("\nCreating a simple RC filter circuit...")

    # Add components
    print("  Adding R1 (10k resistor)...")
    r1 = editor.add_resistor(x=1000, y=2000, value="10k", designator="R1")

    print("  Adding C1 (100nF capacitor)...")
    c1 = editor.add_capacitor(x=2000, y=2000, value="100nF", designator="C1")

    # Add connections
    print("  Adding wires...")
    editor.add_wire([(1000, 2000), (1500, 2000)])
    editor.add_wire([(1500, 2000), (2000, 2000)])

    # Add junction
    print("  Adding junction...")
    editor.add_junction(1500, 2000)

    # Add power ports
    print("  Adding power ports...")
    editor.add_power_port(900, 2000, "VIN", PowerPortStyle.ARROW, Orientation.LEFT)
    editor.add_power_port(2000, 1800, "GND", PowerPortStyle.POWER_GROUND, Orientation.DOWN)

    # Add connection to ground
    editor.add_wire([(2000, 1800), (2000, 2000)])

    # Add net labels
    print("  Adding net labels...")
    editor.add_net_label(1500, 2100, "SIGNAL", Orientation.RIGHT)
    editor.add_net_label(2200, 2000, "VOUT", Orientation.RIGHT)

    # Add title
    print("  Adding title...")
    editor.add_label(1000, 2500, "RC Low-Pass Filter", Orientation.RIGHT)

    # Save
    output_file = "example_rc_filter.SchDoc"
    print(f"\nSaving to {output_file}...")
    editor.save(output_file)

    print(f"✓ Created {output_file}")
    print("\n" + "=" * 70 + "\n")


def example_3_modify_existing():
    """Example 3: Modify an existing schematic"""
    print("=" * 70)
    print("Example 3: Modify Existing Schematic")
    print("=" * 70)

    editor = SchematicEditor()
    editor.load("DI.SchDoc")

    print(f"\nOriginal schematic has {len(editor.get_components())} components")

    # Add new component
    print("\nAdding new component U100 (74HC595)...")
    new_comp = editor.add_component(
        library_reference="74HC595",
        x=3000,
        y=3000,
        designator="U100",
        orientation=Orientation.RIGHT,
        description="8-bit shift register"
    )

    # Add connection
    print("Adding wire to new component...")
    editor.add_wire([(3000, 3000), (3500, 3000)])

    # Add label
    print("Adding net label...")
    editor.add_net_label(3200, 3100, "DATA_OUT", Orientation.RIGHT)

    print(f"\nModified schematic now has {len(editor.get_components())} components")

    # Save modified version
    output_file = "DI_with_additions.SchDoc"
    print(f"\nSaving to {output_file}...")
    editor.save(output_file)

    print(f"✓ Saved modified schematic to {output_file}")
    print("\n" + "=" * 70 + "\n")


def example_4_color_and_coordinates():
    """Example 4: Working with colors and coordinates"""
    print("=" * 70)
    print("Example 4: Colors and Coordinates")
    print("=" * 70)

    # Color conversion
    print("\nColor Conversion:")
    red_int = rgb_to_color(255, 0, 0)
    print(f"  RGB(255, 0, 0) → 0x{red_int:06X}")

    r, g, b = color_to_rgb(0x00FF00)
    print(f"  0x00FF00 → RGB({r}, {g}, {b})")

    # Coordinate conversion
    print("\nCoordinate Conversion:")
    from altium_objects import mils_to_mm, mm_to_mils

    mils = 1000
    mm = mils_to_mm(mils)
    print(f"  {mils} mils → {mm} mm")

    mm = 25.4
    mils = mm_to_mils(mm)
    print(f"  {mm} mm → {mils} mils")

    # Create schematic with custom colors
    print("\nCreating schematic with custom colors...")
    editor = SchematicEditor()
    editor.new()

    # Add colored shapes
    red = rgb_to_color(255, 0, 0)
    green = rgb_to_color(0, 255, 0)
    blue = rgb_to_color(0, 0, 255)

    editor.add_rectangle(500, 500, 800, 800, color=red, fill_color=red, is_solid=True)
    editor.add_rectangle(900, 500, 1200, 800, color=green, fill_color=green, is_solid=True)
    editor.add_rectangle(1300, 500, 1600, 800, color=blue, fill_color=blue, is_solid=True)

    editor.add_label(900, 900, "RGB Color Demo", Orientation.RIGHT)

    output_file = "example_colors.SchDoc"
    editor.save(output_file)
    print(f"✓ Saved color demo to {output_file}")

    print("\n" + "=" * 70 + "\n")


def example_5_query_and_search():
    """Example 5: Query and search operations"""
    print("=" * 70)
    print("Example 5: Query and Search Operations")
    print("=" * 70)

    editor = SchematicEditor()
    editor.load("DI.SchDoc")

    # Find all power ports
    print("\nPower Ports:")
    for port in editor.get_power_ports():
        print(f"  {port.text} ({port.style.name}) at ({port.location_x}, {port.location_y})")

    # Find all junctions
    junctions = editor.doc.get_junctions()
    print(f"\nTotal Junctions: {len(junctions)}")

    # Get all unique net names
    net_names = set()
    for label in editor.get_net_labels():
        if label.text:
            net_names.add(label.text)

    print(f"\nUnique Net Names: {len(net_names)}")
    for name in sorted(net_names)[:10]:
        print(f"  - {name}")

    if len(net_names) > 10:
        print(f"  ... and {len(net_names) - 10} more")

    print("\n" + "=" * 70 + "\n")


def main():
    """Run all examples"""
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "  Altium SchDoc Editor - Example Usage".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print("\n")

    try:
        # Run examples
        example_1_parse_and_analyze()
        example_2_create_new_schematic()
        # Skip modify example if you don't want to modify DI.SchDoc
        # example_3_modify_existing()
        example_4_color_and_coordinates()
        example_5_query_and_search()

        print("\n✓ All examples completed successfully!\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
