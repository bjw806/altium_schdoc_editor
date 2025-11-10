#!/usr/bin/env python3
"""
SKiDL Integration Examples
===========================

This script demonstrates how to use SKiDL with the Altium SchDoc Editor.

Examples include:
1. Creating circuits with SKiDL and exporting to Altium
2. Loading Altium schematics and converting to SKiDL
3. Rendering schematics to SVG/PNG
4. Generating netlists
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skidl import Part, Net, SKIDL, TEMPLATE
from altium_editor import SchematicEditor


def example_1_simple_circuit():
    """Example 1: Create a simple voltage divider with SKiDL and save to Altium"""
    print("\n" + "="*70)
    print("Example 1: Simple Voltage Divider Circuit")
    print("="*70)

    # Define nets
    vcc = Net('VCC')
    gnd = Net('GND')
    output = Net('VOUT')

    # Create resistors
    r1 = Part('Device', 'R', value='10k', ref='R1', dest=SKIDL)
    r2 = Part('Device', 'R', value='10k', ref='R2', dest=SKIDL)

    # Connect circuit
    r1[1] += vcc
    r1[2] += output
    r2[1] += output
    r2[2] += gnd

    # Create Altium schematic from SKiDL
    editor = SchematicEditor()
    editor.from_skidl()

    # Save to Altium format
    output_file = "voltage_divider.SchDoc"
    editor.save(output_file)

    print(f"✓ Created voltage divider circuit")
    print(f"✓ Saved to {output_file}")

    # Print summary
    editor.print_summary()

    return editor


def example_2_load_and_convert():
    """Example 2: Load Altium schematic and convert to SKiDL"""
    print("\n" + "="*70)
    print("Example 2: Load Altium Schematic and Convert to SKiDL")
    print("="*70)

    # Check if example file exists
    input_file = "DI.SchDoc"
    if not os.path.exists(input_file):
        print(f"⚠ Example file {input_file} not found. Skipping this example.")
        return None

    # Load Altium schematic
    editor = SchematicEditor()
    editor.load(input_file)

    print(f"✓ Loaded {input_file}")

    # Convert to SKiDL
    converter = editor.to_skidl()

    print(f"✓ Converted to SKiDL circuit")

    # Print SKiDL summary
    converter.print_circuit_summary()

    return converter


def example_3_render_schematic():
    """Example 3: Render schematic to SVG"""
    print("\n" + "="*70)
    print("Example 3: Render Schematic to SVG")
    print("="*70)

    # Create a simple circuit
    print("Creating circuit...")

    vcc = Net('VCC')
    gnd = Net('GND')
    led_anode = Net('LED+')

    # LED circuit with current limiting resistor
    r1 = Part('Device', 'R', value='330', ref='R1', dest=SKIDL)
    led1 = Part('Device', 'LED', ref='D1', dest=SKIDL)

    r1[1] += vcc
    r1[2] += led_anode
    led1[1] += led_anode  # Anode
    led1[2] += gnd  # Cathode

    # Generate Altium schematic
    editor = SchematicEditor()
    editor.from_skidl()

    # Render to SVG
    svg_file = editor.render_svg("led_circuit.svg")
    print(f"✓ Rendered schematic to {svg_file}")

    # Also save as Altium file
    editor.save("led_circuit.SchDoc")
    print(f"✓ Saved Altium schematic to led_circuit.SchDoc")

    return editor


def example_4_complex_circuit():
    """Example 4: More complex circuit - Op-amp amplifier"""
    print("\n" + "="*70)
    print("Example 4: Op-Amp Non-Inverting Amplifier")
    print("="*70)

    # Define nets
    vcc = Net('VCC')
    vee = Net('VEE')
    gnd = Net('GND')
    vin = Net('VIN')
    vout = Net('VOUT')
    fb = Net('FB')

    # Create components
    opamp = Part('Amplifier_Operational', 'LM358', ref='U1', dest=SKIDL)
    r1 = Part('Device', 'R', value='10k', ref='R1', dest=SKIDL)
    r2 = Part('Device', 'R', value='100k', ref='R2', dest=SKIDL)
    c1 = Part('Device', 'C', value='100n', ref='C1', dest=SKIDL)

    # Connect op-amp power
    opamp['V+'] += vcc
    opamp['V-'] += vee

    # Connect input
    opamp['+'] += vin
    opamp['-'] += fb

    # Connect feedback network
    opamp['OUT'] += vout
    r2[1] += vout
    r2[2] += fb
    r1[1] += fb
    r1[2] += gnd

    # Decoupling capacitor
    c1[1] += vcc
    c1[2] += gnd

    # Generate schematic
    editor = SchematicEditor()
    editor.from_skidl()

    # Save
    editor.save("opamp_amplifier.SchDoc")
    print(f"✓ Created op-amp amplifier circuit")
    print(f"✓ Saved to opamp_amplifier.SchDoc")

    # Print summary
    editor.print_summary()

    # Generate netlist
    print("\nGenerating netlist...")
    try:
        editor.generate_netlist("opamp_amplifier")
        print("✓ Netlist generated: opamp_amplifier.net")
    except Exception as e:
        print(f"⚠ Netlist generation: {e}")

    return editor


def example_5_parametric_design():
    """Example 5: Parametric circuit generation"""
    print("\n" + "="*70)
    print("Example 5: Parametric Design - Resistor Array")
    print("="*70)

    # Create a resistor divider chain
    num_resistors = 4
    vcc = Net('VCC')
    gnd = Net('GND')

    # Create intermediate nets
    nets = [Net(f'N{i}') for i in range(num_resistors - 1)]

    # Create resistors and connect them in series
    resistors = []
    for i in range(num_resistors):
        r = Part('Device', 'R', value='1k', ref=f'R{i+1}', dest=SKIDL)
        resistors.append(r)

        if i == 0:
            r[1] += vcc
            r[2] += nets[0]
        elif i == num_resistors - 1:
            r[1] += nets[-1]
            r[2] += gnd
        else:
            r[1] += nets[i-1]
            r[2] += nets[i]

    print(f"✓ Created resistor array with {num_resistors} resistors")

    # Generate schematic
    editor = SchematicEditor()
    editor.from_skidl()

    # Save
    editor.save("resistor_array.SchDoc")
    print(f"✓ Saved to resistor_array.SchDoc")

    # Print SKiDL summary
    editor.print_skidl_summary()

    return editor


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("SKiDL Integration Examples for Altium SchDoc Editor")
    print("="*70)

    examples = [
        ("Simple Voltage Divider", example_1_simple_circuit),
        ("Load and Convert", example_2_load_and_convert),
        ("Render to SVG", example_3_render_schematic),
        ("Complex Circuit", example_4_complex_circuit),
        ("Parametric Design", example_5_parametric_design),
    ]

    results = {}

    for name, example_func in examples:
        try:
            result = example_func()
            results[name] = "✓ Success"
        except Exception as e:
            results[name] = f"✗ Error: {e}"
            print(f"\n⚠ Error in {name}: {e}")

    # Print summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    for name, status in results.items():
        print(f"{name:.<50} {status}")

    print("\n✓ All examples completed!")
    print("\nGenerated files:")
    print("  - voltage_divider.SchDoc")
    print("  - led_circuit.SchDoc")
    print("  - led_circuit.svg")
    print("  - opamp_amplifier.SchDoc")
    print("  - resistor_array.SchDoc")


if __name__ == "__main__":
    main()
