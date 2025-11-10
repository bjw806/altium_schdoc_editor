# Altium SchDoc Editor

A comprehensive Python library for parsing and editing Altium Designer schematic files (.SchDoc). Designed specifically for AI/LLM usage with intuitive, high-level APIs.

## Features

- **Complete SchDoc Parser**: Read and parse Altium schematic files into Python objects
- **LLM-Friendly API**: Simple, intuitive methods designed for AI-assisted schematic editing
- **Comprehensive Object Model**: Support for all major schematic elements:
  - Components (with pins, designators, values)
  - Wires and buses
  - Net labels and power ports
  - Junctions
  - Graphical elements (lines, rectangles, polygons, arcs, etc.)
  - Parameters and text labels
- **High-Level Editor**: Easy-to-use API for creating and modifying schematics
- **Altium to KiCad Converter**: Convert Altium schematics to KiCad via SKiDL
- **Tested**: Validated with real Altium schematic files

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Altium to KiCad Conversion

Convert Altium SchDoc files to KiCad format via SKiDL (Python-based circuit description language).

### Quick Conversion

```bash
# Convert Altium schematic to KiCad
python3 convert_pipeline.py input.SchDoc
```

This will generate:
- `input.py` - SKiDL Python code representing the circuit
- `input.net` - KiCad netlist file
- `input.kicad_pcb` - KiCad PCB file (if SKiDL is installed)

### Conversion Pipeline

The conversion follows these steps:

1. **Parse Altium File** - Extract components, nets, and connections using `altium_parser.py`
2. **Analyze Schematic** - Identify net connectivity by tracing wires and pin connections
3. **Generate SKiDL Code** - Create Python code that describes the circuit
4. **Execute SKiDL** - Run the generated code to produce KiCad files

### Using the Converter Programmatically

```python
from altium_to_skidl import AltiumToSKiDLConverter

# Create converter
converter = AltiumToSKiDLConverter("input.SchDoc")

# Run full conversion
converter.convert(
    skidl_output="circuit.py",
    pcb_output="output.kicad_pcb",
    netlist_output="output.net",
    execute=True  # Set False to only generate SKiDL code
)

# Print analysis summary
converter.print_analysis_summary()
```

### Understanding the Generated SKiDL Code

The generated SKiDL Python file contains:
- Net definitions (power, ground, signal nets)
- Component definitions with part numbers and footprints
- Connection specifications (which pins connect to which nets)

You can edit this file to:
- Fix part mappings
- Update footprints
- Modify net names
- Add constraints

Then re-run it to regenerate KiCad files:
```bash
python3 circuit.py
```

### Importing to Altium

After generating KiCad files, you can import them back to Altium:
1. Open KiCad and load the generated `.kicad_pcb` file
2. Export from KiCad in a format Altium supports (e.g., IPC netlist)
3. Import into Altium Designer

## Quick Start

### Parsing an Existing Schematic

```python
from altium_parser import AltiumParser

# Parse a SchDoc file
parser = AltiumParser()
doc = parser.parse_file("schematic.SchDoc")

# Access schematic contents
print(f"Components: {len(doc.get_components())}")
print(f"Wires: {len(doc.get_wires())}")
print(f"Net Labels: {len(doc.get_net_labels())}")

# Examine components
for comp in doc.get_components():
    print(f"Component: {comp.library_reference} at ({comp.location_x}, {comp.location_y})")
```

### Using the High-Level Editor

```python
from altium_editor import SchematicEditor
from altium_objects import Orientation, PowerPortStyle

# Create new schematic
editor = SchematicEditor()
editor.new()

# Add components
u1 = editor.add_component("LM358", x=1000, y=2000, designator="U1")
r1 = editor.add_resistor(x=1500, y=2500, value="10k", designator="R1")
c1 = editor.add_capacitor(x=2000, y=2500, value="100nF", designator="C1")

# Add connections
wire1 = editor.add_wire([(1000, 2000), (1500, 2000)])
wire2 = editor.add_wire([(1500, 2000), (1500, 2500)])

# Add junction at wire intersection
junction = editor.add_junction(1500, 2000)

# Add power ports
gnd = editor.add_power_port(1000, 1500, "GND", PowerPortStyle.POWER_GROUND)
vcc = editor.add_power_port(2000, 3000, "VCC", PowerPortStyle.ARROW)

# Add net label
label = editor.add_net_label(1500, 2100, "SIGNAL")

# Save schematic
editor.save("new_schematic.SchDoc")
```

### Modifying an Existing Schematic

```python
from altium_editor import SchematicEditor

# Load existing schematic
editor = SchematicEditor()
editor.load("existing.SchDoc")

# Add new components
new_comp = editor.add_component("74HC595", x=3000, y=2000, designator="U5")

# Add wire to connect it
editor.add_wire([(3000, 2000), (3500, 2000)])

# Save modified schematic
editor.save("modified.SchDoc")
```

## API Reference

### SchematicEditor

The main high-level API for creating and modifying schematics.

#### File Operations

- `new()`: Create a new blank schematic
- `load(filename)`: Load an existing SchDoc file
- `save(filename)`: Save the schematic to a file

#### Component Operations

- `add_component(library_ref, x, y, designator, orientation=Orientation.RIGHT, description="")`: Add a component
- `add_resistor(x, y, value="10k", designator="R?", orientation=Orientation.RIGHT)`: Add a resistor
- `add_capacitor(x, y, value="10uF", designator="C?", orientation=Orientation.RIGHT)`: Add a capacitor
- `find_component(designator)`: Find a component by designator
- `remove_component(component)`: Remove a component

#### Wire and Connection Operations

- `add_wire(points, color=0x000000, line_width=1)`: Add a wire with list of (x, y) points
- `add_junction(x, y, color=0x000000)`: Add a junction dot
- `add_net_label(x, y, text, orientation=Orientation.RIGHT)`: Add a net label
- `add_power_port(x, y, text="GND", style=PowerPortStyle.POWER_GROUND, orientation=Orientation.DOWN)`: Add a power port
- `connect_points(point1, point2, add_junction=False)`: Connect two points with a wire

#### Graphical Operations

- `add_line(x1, y1, x2, y2, color=0x000000, line_width=1)`: Add a line
- `add_rectangle(x1, y1, x2, y2, color=0x000000, fill_color=None, is_solid=False)`: Add a rectangle
- `add_label(x, y, text, orientation=Orientation.RIGHT, color=0x000000)`: Add a text label

#### Query Operations

- `get_components()`: Get all components
- `get_wires()`: Get all wires
- `get_net_labels()`: Get all net labels
- `get_power_ports()`: Get all power ports
- `get_component_by_designator(designator)`: Find component by designator
- `print_summary()`: Print a summary of schematic contents

### Object Model

All schematic objects inherit from `AltiumObject` and have clear, descriptive properties.

#### Component

- `library_reference`: Component library reference (e.g., "LM358")
- `location_x`, `location_y`: Position in 1/100 inch units
- `orientation`: Orientation (Orientation.RIGHT, UP, LEFT, DOWN)
- `children`: List of child objects (pins, designators, etc.)

#### Wire

- `points`: List of (x, y) coordinate tuples
- `color`: RGB color integer
- `line_width`: Line width

#### Pin

- `location_x`, `location_y`: Position relative to component
- `name`: Pin name
- `designator`: Pin number
- `electrical`: Electrical type (PinElectrical.INPUT, OUTPUT, PASSIVE, etc.)
- `orientation`: Pin orientation
- `length`: Pin length

#### NetLabel

- `location_x`, `location_y`: Position
- `text`: Label text
- `orientation`: Text orientation

#### PowerPort

- `location_x`, `location_y`: Position
- `text`: Port name (e.g., "VCC", "GND")
- `style`: Symbol style (PowerPortStyle.POWER_GROUND, ARROW, BAR, WAVE, etc.)
- `orientation`: Port orientation

## Coordinate System

- Coordinates are in **1/100 inch units** (also known as mils/100)
- Origin is at bottom-left
- To convert to millimeters: `mm = mils * 0.254`
- To convert from millimeters: `mils = mm / 0.254`

Helper functions are provided:
```python
from altium_objects import mils_to_mm, mm_to_mils

mm_value = mils_to_mm(1000)  # 254 mm
mils_value = mm_to_mils(25.4)  # 100 mils
```

## Colors

Colors are stored as RGB integers:
```python
from altium_objects import color_to_rgb, rgb_to_color

# Convert color integer to RGB tuple
r, g, b = color_to_rgb(0xFF0000)  # (255, 0, 0) - Red

# Convert RGB to color integer
color = rgb_to_color(0, 255, 0)  # 0x00FF00 - Green
```

Common colors:
- `0x000000` - Black
- `0xFFFFFF` - White
- `0xFF0000` - Red
- `0x00FF00` - Green
- `0x0000FF` - Blue

## Enumerations

### Orientation
- `Orientation.RIGHT` (0°)
- `Orientation.UP` (90°)
- `Orientation.LEFT` (180°)
- `Orientation.DOWN` (270°)

### PowerPortStyle
- `PowerPortStyle.ARROW`
- `PowerPortStyle.BAR`
- `PowerPortStyle.WAVE`
- `PowerPortStyle.POWER_GROUND`
- `PowerPortStyle.SIGNAL_GROUND`
- `PowerPortStyle.EARTH`

### PinElectrical
- `PinElectrical.INPUT`
- `PinElectrical.OUTPUT`
- `PinElectrical.IO`
- `PinElectrical.PASSIVE`
- `PinElectrical.POWER`
- `PinElectrical.OPEN_COLLECTOR`
- `PinElectrical.OPEN_EMITTER`
- `PinElectrical.HI_Z`

## File Format

Altium SchDoc files are OLE Compound Documents containing:
- **FileHeader stream**: Main schematic data (records in pipe-delimited format)
- **Storage stream**: Embedded images/icons
- **Additional stream** (optional): Supplementary data

Each record has:
- 2-byte length (little-endian)
- 1 zero byte
- 1 type byte (always 0 for property lists)
- Property data: `|NAME=value|NAME=value|...`

## Testing

Run the comprehensive test suite:

```bash
python test_parser.py
```

Tests include:
- Parsing DI.SchDoc example file
- Round-trip integrity (parse → serialize → parse)
- High-level editor operations
- Modifying existing schematics
- Query operations

## Examples

### Example 1: Analyze a Schematic

```python
from altium_editor import SchematicEditor

editor = SchematicEditor()
editor.load("schematic.SchDoc")

# Print summary
editor.print_summary()

# Find specific components
for comp in editor.get_components():
    # Get designator from children
    designator = "?"
    for child in comp.children:
        if hasattr(child, 'name') and child.name == "Designator":
            designator = child.text
            break

    print(f"{designator}: {comp.library_reference}")

# List all nets
for label in editor.get_net_labels():
    print(f"Net: {label.text} at ({label.location_x}, {label.location_y})")
```

### Example 2: Create a Simple Circuit

```python
from altium_editor import SchematicEditor
from altium_objects import Orientation, PowerPortStyle

editor = SchematicEditor()
editor.new()

# Add resistor and capacitor
r1 = editor.add_resistor(1000, 2000, "10k", "R1", Orientation.RIGHT)
c1 = editor.add_capacitor(2000, 2000, "100nF", "C1", Orientation.RIGHT)

# Connect them
editor.add_wire([(1100, 2000), (2000, 2000)])
editor.add_junction(2000, 2000)

# Add ground
editor.add_power_port(2000, 1800, "GND", PowerPortStyle.POWER_GROUND, Orientation.DOWN)
editor.add_wire([(2000, 1800), (2000, 2000)])

# Add labels
editor.add_net_label(1500, 2100, "INPUT")

editor.save("simple_circuit.SchDoc")
```

### Example 3: Batch Modify Components

```python
from altium_editor import SchematicEditor

editor = SchematicEditor()
editor.load("schematic.SchDoc")

# Find all resistors and move them
for comp in editor.get_components():
    if "RES" in comp.library_reference:
        # Move down by 100 units
        comp.location_y -= 100

editor.save("modified_schematic.SchDoc")
```

## Design Philosophy for LLM Usage

This library is designed to be easily understood and used by Large Language Models:

1. **Clear Naming**: Property names are descriptive and intuitive
2. **Type Hints**: All functions have clear type hints
3. **Simple Data Structures**: Uses standard Python types (lists, dicts, dataclasses)
4. **High-Level API**: Common operations have dedicated methods
5. **Comprehensive Documentation**: Docstrings on all public methods
6. **Examples**: Numerous examples for common tasks

## Limitations

- **OLE File Creation**: Creating new OLE files from scratch is complex. The library uses template-based approaches for best results.
- **Round-Trip Fidelity**: When parsing and re-serializing files, some formatting differences may occur (though all data is preserved).
- **Mini Streams**: Small embedded files (<4KB) use OLE mini streams which have limited support in the current writer.
- **Image Support**: Embedded images in the Storage stream are not yet fully supported.

## Contributing

This project is designed for use with Claude Code and other AI assistants. The codebase is well-documented and structured for easy understanding and modification.

Key files:
- `altium_objects.py`: Data structure definitions
- `altium_parser.py`: Parser implementation
- `altium_serializer.py`: Serializer implementation
- `altium_editor.py`: High-level editor API
- `ole_writer.py`: OLE file writer
- `ole_patcher.py`: OLE file patcher for same-size modifications
- `test_parser.py`: Comprehensive test suite

## References

This implementation is based on research from:
- [gsuberland/altium_js](https://github.com/gsuberland/altium_js) - Primary reference
- [vadmium/python-altium](https://github.com/vadmium/python-altium) - Format documentation
- [pluots/PyAltium](https://github.com/pluots/PyAltium) - Python implementation reference

## License

This project is open source and available for use in AI-assisted development workflows.

## Version

Version: 1.0.0
Last Updated: 2025-11-09

---

Created for use with Claude Code and AI-assisted schematic editing workflows.
