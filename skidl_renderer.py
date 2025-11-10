"""
SKiDL Renderer for Altium Schematics
=====================================
Provides visual rendering capabilities for Altium schematics using SKiDL and schemdraw.

This module enables:
- SVG generation from Altium schematics
- PNG/JPEG rendering
- KiCad schematic export
- Visual preview generation
"""

from typing import Optional, Dict, List, Tuple
import os
from pathlib import Path
from altium_objects import SchDoc, Component, Wire, NetLabel, PowerPort, Pin
from skidl_converter import AltiumToSKiDL
import skidl


class SchematicRenderer:
    """
    Renders Altium schematics to various visual formats
    """

    def __init__(self):
        self.converter = AltiumToSKiDL()

    def render_to_svg(self, doc: SchDoc, output_file: str = "schematic.svg") -> str:
        """
        Render schematic to SVG format using SKiDL

        Args:
            doc: SchDoc object to render
            output_file: Output SVG filename

        Returns:
            Path to generated SVG file
        """
        try:
            # Convert to SKiDL circuit
            circuit = self.converter.convert_schematic(doc)

            # Generate SVG using SKiDL
            skidl.generate_svg(filename=output_file)

            return output_file

        except Exception as e:
            print(f"Error generating SVG: {e}")
            # Fallback: create a simple SVG manually
            return self._render_svg_fallback(doc, output_file)

    def _render_svg_fallback(self, doc: SchDoc, output_file: str) -> str:
        """
        Fallback SVG renderer using basic SVG generation

        Args:
            doc: SchDoc object to render
            output_file: Output SVG filename

        Returns:
            Path to generated SVG file
        """
        # Calculate bounding box
        min_x, min_y, max_x, max_y = self._calculate_bounds(doc)

        # Add margins
        margin = 100
        width = max_x - min_x + 2 * margin
        height = max_y - min_y + 2 * margin

        # Create SVG
        svg_lines = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'<g transform="translate({-min_x + margin}, {-min_y + margin})">',
        ]

        # Render components
        for comp in doc.get_components():
            svg_lines.extend(self._render_component_svg(comp))

        # Render wires
        for wire in doc.get_wires():
            svg_lines.extend(self._render_wire_svg(wire))

        # Render labels
        for label in doc.get_net_labels():
            svg_lines.extend(self._render_label_svg(label))

        # Render power ports
        for port in doc.get_power_ports():
            svg_lines.extend(self._render_power_port_svg(port))

        svg_lines.extend([
            '</g>',
            '</svg>'
        ])

        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(svg_lines))

        return output_file

    def _calculate_bounds(self, doc: SchDoc) -> Tuple[int, int, int, int]:
        """Calculate bounding box of all schematic objects"""
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        # Check components
        for comp in doc.get_components():
            min_x = min(min_x, comp.location_x)
            min_y = min(min_y, comp.location_y)
            max_x = max(max_x, comp.location_x + 200)
            max_y = max(max_y, comp.location_y + 200)

        # Check wires
        for wire in doc.get_wires():
            for x, y in wire.points:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

        # Check labels
        for label in doc.get_net_labels():
            min_x = min(min_x, label.location_x)
            min_y = min(min_y, label.location_y)
            max_x = max(max_x, label.location_x + 100)
            max_y = max(max_y, label.location_y + 20)

        # Default bounds if no objects
        if min_x == float('inf'):
            return (0, 0, 1000, 1000)

        return (int(min_x), int(min_y), int(max_x), int(max_y))

    def _render_component_svg(self, comp: Component) -> List[str]:
        """Render a component as SVG elements"""
        svg = []
        x, y = comp.location_x, comp.location_y

        # Draw component body (rectangle)
        svg.append(f'<rect x="{x-50}" y="{y-50}" width="100" height="100" '
                  f'fill="none" stroke="black" stroke-width="2"/>')

        # Draw designator
        svg.append(f'<text x="{x}" y="{y-60}" text-anchor="middle" '
                  f'font-family="Arial" font-size="12" fill="black">{comp.designator}</text>')

        # Draw reference
        if comp.library_reference:
            svg.append(f'<text x="{x}" y="{y}" text-anchor="middle" '
                      f'font-family="Arial" font-size="10" fill="blue">{comp.library_reference}</text>')

        # Draw pins
        for child in comp.children:
            if isinstance(child, Pin):
                pin_x = x + child.location_x
                pin_y = y + child.location_y
                svg.append(f'<circle cx="{pin_x}" cy="{pin_y}" r="3" fill="red"/>')
                if child.designator:
                    svg.append(f'<text x="{pin_x+5}" y="{pin_y}" '
                              f'font-family="Arial" font-size="8" fill="black">{child.designator}</text>')

        return svg

    def _render_wire_svg(self, wire: Wire) -> List[str]:
        """Render a wire as SVG polyline"""
        if not wire.points or len(wire.points) < 2:
            return []

        points_str = ' '.join(f'{x},{y}' for x, y in wire.points)
        color = self._int_to_hex_color(wire.color)

        return [f'<polyline points="{points_str}" fill="none" '
                f'stroke="{color}" stroke-width="{wire.line_width}"/>']

    def _render_label_svg(self, label: NetLabel) -> List[str]:
        """Render a net label as SVG text"""
        return [
            f'<text x="{label.location_x}" y="{label.location_y}" '
            f'font-family="Arial" font-size="12" fill="green">{label.text}</text>'
        ]

    def _render_power_port_svg(self, port: PowerPort) -> List[str]:
        """Render a power port as SVG elements"""
        svg = []
        x, y = port.location_x, port.location_y

        # Draw power symbol (simple triangle for now)
        if 'GND' in port.text.upper():
            # Ground symbol
            svg.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+20}" stroke="black" stroke-width="2"/>')
            svg.append(f'<line x1="{x-15}" y1="{y+20}" x2="{x+15}" y2="{y+20}" stroke="black" stroke-width="2"/>')
            svg.append(f'<line x1="{x-10}" y1="{y+25}" x2="{x+10}" y2="{y+25}" stroke="black" stroke-width="2"/>')
            svg.append(f'<line x1="{x-5}" y1="{y+30}" x2="{x+5}" y2="{y+30}" stroke="black" stroke-width="2"/>')
        else:
            # Power symbol (arrow pointing up)
            svg.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-20}" stroke="red" stroke-width="2"/>')
            svg.append(f'<polygon points="{x},{y-20} {x-5},{y-15} {x+5},{y-15}" fill="red"/>')

        # Draw label
        svg.append(f'<text x="{x+10}" y="{y}" font-family="Arial" font-size="10" fill="red">{port.text}</text>')

        return svg

    def _int_to_hex_color(self, color_int: int) -> str:
        """Convert integer color to hex string"""
        r = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = color_int & 0xFF
        return f'#{r:02x}{g:02x}{b:02x}'

    def render_to_image(self, doc: SchDoc, output_file: str = "schematic.png",
                       format: str = "png") -> str:
        """
        Render schematic to image format (PNG, JPEG, etc.)

        Args:
            doc: SchDoc object to render
            output_file: Output image filename
            format: Image format ('png', 'jpg', 'jpeg')

        Returns:
            Path to generated image file
        """
        try:
            # First generate SVG
            svg_file = output_file.rsplit('.', 1)[0] + '.svg'
            self.render_to_svg(doc, svg_file)

            # Convert SVG to image using PIL/Pillow
            from PIL import Image
            import cairosvg
            import io

            # Convert SVG to PNG bytes
            png_bytes = cairosvg.svg2png(url=svg_file)

            # Open with PIL
            image = Image.open(io.BytesIO(png_bytes))

            # Save in requested format
            image.save(output_file, format=format.upper())

            return output_file

        except ImportError:
            print("Warning: cairosvg not available. Install with: pip install cairosvg")
            print("Falling back to SVG output only.")
            return self.render_to_svg(doc, output_file.rsplit('.', 1)[0] + '.svg')

        except Exception as e:
            print(f"Error rendering to image: {e}")
            return self.render_to_svg(doc, output_file.rsplit('.', 1)[0] + '.svg')

    def render_to_kicad(self, doc: SchDoc, output_file: str = "schematic.kicad_sch") -> str:
        """
        Export schematic to KiCad format

        Args:
            doc: SchDoc object to render
            output_file: Output KiCad schematic filename

        Returns:
            Path to generated KiCad file
        """
        try:
            # Convert to SKiDL circuit
            circuit = self.converter.convert_schematic(doc)

            # Generate KiCad netlist
            skidl.generate_netlist(file_=output_file.rsplit('.', 1)[0])

            print(f"KiCad netlist generated: {output_file.rsplit('.', 1)[0]}.net")
            return f"{output_file.rsplit('.', 1)[0]}.net"

        except Exception as e:
            print(f"Error generating KiCad schematic: {e}")
            return None

    def generate_preview(self, doc: SchDoc, max_size: Tuple[int, int] = (800, 600)) -> str:
        """
        Generate a preview image suitable for display

        Args:
            doc: SchDoc object to render
            max_size: Maximum size (width, height) in pixels

        Returns:
            Path to preview image
        """
        preview_file = "preview.png"
        return self.render_to_image(doc, preview_file, format='png')


def render_altium_schematic(schematic_file: str, output_format: str = "svg") -> str:
    """
    Convenience function to render an Altium schematic

    Args:
        schematic_file: Path to .SchDoc file
        output_format: Output format ('svg', 'png', 'jpg', 'kicad')

    Returns:
        Path to generated output file
    """
    from altium_parser import parse_schematic

    # Parse Altium file
    doc = parse_schematic(schematic_file)

    # Create renderer
    renderer = SchematicRenderer()

    # Generate output
    base_name = Path(schematic_file).stem
    output_file = f"{base_name}.{output_format}"

    if output_format.lower() == 'svg':
        return renderer.render_to_svg(doc, output_file)
    elif output_format.lower() in ['png', 'jpg', 'jpeg']:
        return renderer.render_to_image(doc, output_file, format=output_format)
    elif output_format.lower() == 'kicad':
        return renderer.render_to_kicad(doc, output_file)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python skidl_renderer.py <input.SchDoc> [format]")
        print("Formats: svg (default), png, jpg, kicad")
        sys.exit(1)

    input_file = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else "svg"

    print(f"Rendering {input_file} to {output_format}...")
    output = render_altium_schematic(input_file, output_format)
    print(f"Output written to: {output}")
