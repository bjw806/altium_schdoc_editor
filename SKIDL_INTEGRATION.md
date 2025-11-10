# SKiDL Integration for Altium SchDoc Editor

SKiDL (SKiDL Is a Design Language) integration enables programmatic circuit design and visual schematic rendering for Altium schematics.

## Features

✅ **Bidirectional Conversion**
- Convert Altium schematics to SKiDL circuits
- Generate Altium schematics from SKiDL code

✅ **Visual Rendering**
- Render schematics to SVG format
- Export to PNG/JPEG images
- Generate KiCad schematics

✅ **Programmatic Circuit Design**
- Define circuits as Python code
- Parametric and algorithmic circuit generation
- Version control friendly (circuits as code)

✅ **Netlist Generation**
- Generate netlists for PCB tools
- Export connectivity information
- Electrical rules checking (via SKiDL)

## Installation

```bash
# Install SKiDL and dependencies
pip install -r requirements.txt

# Or install manually
pip install skidl schemdraw pillow
```

## Quick Start

### Creating Circuits with SKiDL

```python
from skidl import Part, Net, SKIDL
from altium_editor import SchematicEditor

# Define a simple voltage divider
vcc = Net('VCC')
gnd = Net('GND')
output = Net('VOUT')

r1 = Part('Device', 'R', value='10k', ref='R1', dest=SKIDL)
r2 = Part('Device', 'R', value='10k', ref='R2', dest=SKIDL)

r1[1] += vcc
r1[2] += output
r2[1] += output
r2[2] += gnd

# Generate Altium schematic
editor = SchematicEditor()
editor.from_skidl()
editor.save("voltage_divider.SchDoc")
```

### Converting Existing Schematics

```python
from altium_editor import SchematicEditor

# Load Altium schematic
editor = SchematicEditor()
editor.load("circuit.SchDoc")

# Convert to SKiDL
converter = editor.to_skidl()

# Generate netlist
converter.generate_netlist("output")

# Print circuit summary
converter.print_circuit_summary()
```

### Rendering Schematics

```python
from altium_editor import SchematicEditor

editor = SchematicEditor()
editor.load("circuit.SchDoc")

# Render to SVG
editor.render_svg("circuit.svg")

# Render to PNG
editor.render_image("circuit.png", format='png')

# Export to KiCad
editor.export_kicad("circuit.kicad_sch")
```

## API Reference

### SchematicEditor Methods

#### `to_skidl() -> AltiumToSKiDL`
Convert the current Altium schematic to a SKiDL circuit.

```python
editor = SchematicEditor()
editor.load("input.SchDoc")
converter = editor.to_skidl()
```

#### `from_skidl(parts=None, nets=None) -> SchematicEditor`
Generate Altium schematic from SKiDL circuit.

```python
editor = SchematicEditor()
editor.from_skidl()  # Uses SKiDL's default_circuit
editor.save("output.SchDoc")
```

#### `render_svg(output_file="schematic.svg") -> str`
Render schematic to SVG format.

```python
svg_file = editor.render_svg("circuit.svg")
```

#### `render_image(output_file="schematic.png", format="png") -> str`
Render schematic to image format (PNG, JPEG, etc.).

```python
png_file = editor.render_image("circuit.png", format='png')
```

#### `export_kicad(output_file="schematic.kicad_sch") -> str`
Export schematic to KiCad format.

```python
kicad_file = editor.export_kicad("circuit.kicad_sch")
```

#### `generate_netlist(output_file=None) -> str`
Generate netlist from schematic using SKiDL.

```python
netlist = editor.generate_netlist("circuit")
```

#### `print_skidl_summary()`
Print SKiDL circuit summary (parts, nets, connections).

```python
editor.print_skidl_summary()
```

## Module Overview

### `skidl_converter.py`
Converts Altium schematics to SKiDL circuits.

**Key Classes:**
- `AltiumToSKiDL`: Main converter class
  - `convert_schematic(doc: SchDoc) -> Circuit`
  - `generate_netlist(filename: str) -> str`
  - `generate_svg(filename: str) -> str`
  - `print_circuit_summary()`

**Usage:**
```python
from skidl_converter import convert_altium_to_skidl

converter = convert_altium_to_skidl("input.SchDoc")
converter.print_circuit_summary()
converter.generate_netlist("output")
```

### `skidl_generator.py`
Generates Altium schematics from SKiDL circuits.

**Key Classes:**
- `SKiDLToAltium`: Main generator class
  - `generate_schematic(parts, nets) -> SchDoc`
  - `save_schematic(filename: str)`

**Usage:**
```python
from skidl_generator import generate_altium_from_skidl
from skidl import Part, Net, SKIDL

# Define circuit
vcc, gnd = Net('VCC'), Net('GND')
r1 = Part('Device', 'R', ref='R1', dest=SKIDL)
r1[1] += vcc
r1[2] += gnd

# Generate Altium file
generate_altium_from_skidl("output.SchDoc")
```

### `skidl_renderer.py`
Provides visual rendering capabilities.

**Key Classes:**
- `SchematicRenderer`: Main renderer class
  - `render_to_svg(doc: SchDoc, output_file: str) -> str`
  - `render_to_image(doc: SchDoc, output_file: str, format: str) -> str`
  - `render_to_kicad(doc: SchDoc, output_file: str) -> str`
  - `generate_preview(doc: SchDoc, max_size: tuple) -> str`

**Usage:**
```python
from skidl_renderer import render_altium_schematic

svg_file = render_altium_schematic("input.SchDoc", output_format="svg")
png_file = render_altium_schematic("input.SchDoc", output_format="png")
```

## Examples

Comprehensive examples are available in `examples/skidl_example.py`:

1. **Simple Voltage Divider** - Basic circuit creation
2. **Load and Convert** - Converting existing Altium schematics
3. **Render to SVG** - Visual rendering
4. **Complex Circuit** - Op-amp amplifier design
5. **Parametric Design** - Algorithmic circuit generation

Run all examples:
```bash
python examples/skidl_example.py
```

## Architecture

The SKiDL integration follows a modular architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    altium_editor.py                         │
│              (High-level API with SKiDL methods)            │
└───────────────────────────┬─────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│ skidl_converter  │ │   skidl_     │ │   skidl_     │
│      .py         │ │ generator.py │ │ renderer.py  │
│                  │ │              │ │              │
│ Altium → SKiDL   │ │ SKiDL→Altium │ │ SVG/PNG/     │
│                  │ │              │ │ KiCad Export │
└──────────────────┘ └──────────────┘ └──────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ altium_objects   │
                  │   altium_parser  │
                  │ altium_serializer│
                  └──────────────────┘
```

## Benefits

1. **Programmatic Design**: Create circuits with code instead of manual drawing
2. **Version Control**: SKiDL circuits are Python code - perfect for Git
3. **Parametric Generation**: Easily create circuit variations algorithmically
4. **Visualization**: Add visual rendering capabilities to Altium editor
5. **Interoperability**: Bridge between Altium and KiCad ecosystems
6. **Automation**: Generate documentation, BOMs, and netlists automatically
7. **Testing**: Write unit tests for circuit designs

## Advanced Usage

### Parametric Circuit Generation

```python
from skidl import Part, Net, SKIDL
from altium_editor import SchematicEditor

def create_resistor_divider(n_stages, value='1k'):
    """Create n-stage resistor divider"""
    vcc = Net('VCC')
    gnd = Net('GND')
    nets = [Net(f'N{i}') for i in range(n_stages - 1)]

    for i in range(n_stages):
        r = Part('Device', 'R', value=value, ref=f'R{i+1}', dest=SKIDL)
        if i == 0:
            r[1] += vcc
            r[2] += nets[0]
        elif i == n_stages - 1:
            r[1] += nets[-1]
            r[2] += gnd
        else:
            r[1] += nets[i-1]
            r[2] += nets[i]

# Generate 10-stage divider
create_resistor_divider(10, '10k')

editor = SchematicEditor()
editor.from_skidl()
editor.save("divider_10stage.SchDoc")
```

### Circuit Analysis

```python
from altium_editor import SchematicEditor

editor = SchematicEditor()
editor.load("complex_circuit.SchDoc")

# Convert to SKiDL
converter = editor.to_skidl()

# Analyze circuit
print(f"Total parts: {len(converter.parts)}")
print(f"Total nets: {len(converter.nets)}")

# Check connectivity
for net_name, connections in converter.nets.items():
    print(f"Net {net_name}: {len(connections)} connections")
```

## Limitations

1. **Component Libraries**: SKiDL uses KiCad component libraries. Complex Altium symbols may not convert perfectly.
2. **Visual Layout**: Auto-layout is basic. Manual adjustment may be needed for complex schematics.
3. **Hierarchical Sheets**: Limited support for multi-sheet hierarchical designs.
4. **Custom Symbols**: Custom Altium symbols require manual mapping to SKiDL parts.

## Troubleshooting

### ImportError: No module named 'skidl'
```bash
pip install skidl
```

### SVG Rendering Issues
Install additional dependencies:
```bash
pip install cairosvg
```

### Component Not Found
SKiDL uses KiCad libraries. Ensure the component exists in KiCad's symbol library or use a generic part:
```python
part = Part('Device', 'R', ref='R1', dest=SKIDL)  # Generic resistor
```

## Testing

Run the integration test:
```bash
python test_skidl_integration.py
```

Run example suite:
```bash
python examples/skidl_example.py
```

## Resources

- [SKiDL Documentation](https://devbisme.github.io/skidl/)
- [SKiDL GitHub](https://github.com/devbisme/skidl)
- [KiCad Symbol Libraries](https://kicad.github.io/)
- [Altium SchDoc Format](README.md)

## Contributing

Contributions are welcome! Areas for improvement:

- [ ] Better component library mapping
- [ ] Improved auto-layout algorithms
- [ ] Hierarchical sheet support
- [ ] Enhanced wire routing
- [ ] Symbol library creation tools

## License

Same license as the parent Altium SchDoc Editor project.
