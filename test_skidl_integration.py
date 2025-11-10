#!/usr/bin/env python3
"""
Simple test for SKiDL integration
"""

import sys

print("Testing SKiDL Integration...")
print("="*70)

# Test 1: Check if modules can be imported
print("\n1. Testing module imports...")
try:
    from altium_objects import SchDoc, Component, Wire
    print("   ✓ altium_objects imported")
except Exception as e:
    print(f"   ✗ Error importing altium_objects: {e}")
    sys.exit(1)

try:
    from altium_editor import SchematicEditor
    print("   ✓ altium_editor imported")
except Exception as e:
    print(f"   ✗ Error importing altium_editor: {e}")
    sys.exit(1)

# Test 2: Check if SKiDL modules exist
print("\n2. Checking SKiDL integration modules...")
import os

modules = [
    'skidl_converter.py',
    'skidl_generator.py',
    'skidl_renderer.py'
]

for module in modules:
    if os.path.exists(module):
        print(f"   ✓ {module} exists")
    else:
        print(f"   ✗ {module} not found")

# Test 3: Check if SchematicEditor has SKiDL methods
print("\n3. Checking SchematicEditor SKiDL methods...")
editor = SchematicEditor()

skidl_methods = [
    'to_skidl',
    'from_skidl',
    'render_svg',
    'render_image',
    'export_kicad',
    'generate_netlist',
    'print_skidl_summary'
]

for method in skidl_methods:
    if hasattr(editor, method):
        print(f"   ✓ {method}() method exists")
    else:
        print(f"   ✗ {method}() method not found")

# Test 4: Create a simple schematic
print("\n4. Testing basic schematic creation...")
try:
    editor.new()
    editor.add_resistor(1000, 2000, "10k", "R1")
    editor.add_wire([(1000, 2000), (1500, 2000)])
    editor.add_net_label(1500, 2000, "NET1")
    print("   ✓ Created simple schematic")

    # Test summary
    print("\n   Schematic contents:")
    editor.print_summary()

except Exception as e:
    print(f"   ✗ Error creating schematic: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✓ Integration test completed!")
print("\nNote: Full SKiDL functionality requires:")
print("  pip install skidl")
print("\nTo test the complete integration:")
print("  1. Install SKiDL: pip install skidl")
print("  2. Run examples: python examples/skidl_example.py")
