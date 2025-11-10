#!/usr/bin/env python3
"""
Main Conversion Pipeline Script

This script provides a simple interface to convert Altium SchDoc files
to KiCad format via SKiDL.

Usage:
    python convert_pipeline.py input.SchDoc

The script will:
1. Parse the Altium file
2. Analyze the schematic
3. Generate SKiDL Python code
4. Execute SKiDL to create KiCad files
"""

import sys
import os
from pathlib import Path
from altium_to_skidl import AltiumToSKiDLConverter


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python convert_pipeline.py <input.SchDoc>")
        print("\nExample:")
        print("  python convert_pipeline.py DI.SchDoc")
        print("\nThis will generate:")
        print("  - schematic.py    (SKiDL Python code)")
        print("  - output.net      (KiCad netlist)")
        print("  - output.kicad_pcb (KiCad PCB file)")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    # Get base name for output files
    base_name = Path(input_file).stem
    skidl_output = f"{base_name}.py"
    pcb_output = f"{base_name}.kicad_pcb"
    netlist_output = f"{base_name}.net"

    print("="*70)
    print("ALTIUM TO KICAD CONVERTER")
    print("="*70)
    print(f"Input:  {input_file}")
    print(f"Output: {skidl_output}, {pcb_output}, {netlist_output}")
    print("="*70)

    # Create converter
    converter = AltiumToSKiDLConverter(input_file)

    try:
        # Run conversion
        converter.convert(
            skidl_output=skidl_output,
            pcb_output=pcb_output,
            netlist_output=netlist_output,
            execute=True
        )

        # Print summary
        converter.print_analysis_summary()

        print("\n" + "="*70)
        print("CONVERSION COMPLETE!")
        print("="*70)
        print(f"✓ SKiDL code:   {skidl_output}")
        print(f"✓ KiCad netlist: {netlist_output}")
        print(f"✓ KiCad PCB:     {pcb_output}")
        print("\nNext steps:")
        print("1. Open the generated .kicad_pcb file in KiCad PCB Editor")
        print("2. Or open the .net netlist file in KiCad Eeschema")
        print("3. You can then export from KiCad and import into Altium")
        print("="*70)

    except Exception as e:
        print("\n" + "="*70)
        print("ERROR DURING CONVERSION")
        print("="*70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nNote: SKiDL code may still have been generated.")
        print(f"Check {skidl_output} and run it manually:")
        print(f"  python3 {skidl_output}")
        sys.exit(1)


if __name__ == '__main__':
    main()
