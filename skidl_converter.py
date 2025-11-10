"""
SKiDL Converter for Altium Schematics
======================================
Converts Altium .SchDoc objects to SKiDL circuit representations.

This module enables:
- Converting Altium schematics to SKiDL circuits
- Extracting net connectivity
- Generating netlists and visual representations
"""

from typing import Dict, List, Tuple, Optional, Set
from skidl import Part, Net, Circuit, generate_netlist, generate_svg, SKIDL, TEMPLATE
import skidl
from altium_objects import (
    SchDoc, Component, Pin, Wire, NetLabel, PowerPort, Junction,
    PinElectrical
)


class AltiumToSKiDL:
    """
    Converter from Altium schematic objects to SKiDL circuit
    """

    def __init__(self):
        self.circuit = None
        self.nets: Dict[str, Net] = {}
        self.parts: Dict[str, Part] = {}
        self.wire_segments: List[List[Tuple[int, int]]] = []
        self.net_names: Dict[Tuple[int, int], str] = {}  # Position -> net name

    def convert_schematic(self, doc: SchDoc) -> Circuit:
        """
        Convert an Altium schematic document to a SKiDL circuit

        Args:
            doc: SchDoc object from altium_parser

        Returns:
            SKiDL Circuit object
        """
        # Reset state
        self.circuit = Circuit()
        self.nets = {}
        self.parts = {}
        self.wire_segments = []
        self.net_names = {}

        # Step 1: Extract net information from labels and power ports
        self._extract_net_names(doc)

        # Step 2: Build wire connectivity graph
        self._extract_wire_segments(doc)

        # Step 3: Convert components to SKiDL parts
        self._convert_components(doc)

        # Step 4: Connect pins based on wire connectivity
        self._connect_nets(doc)

        return self.circuit

    def _extract_net_names(self, doc: SchDoc):
        """Extract net names from NetLabel and PowerPort objects"""
        # Net labels
        for label in doc.get_net_labels():
            pos = (label.location_x, label.location_y)
            self.net_names[pos] = label.text

        # Power ports
        for port in doc.get_power_ports():
            pos = (port.location_x, port.location_y)
            self.net_names[pos] = port.text
            # Create global nets for power
            if port.text not in self.nets:
                self.nets[port.text] = Net(port.text)

    def _extract_wire_segments(self, doc: SchDoc):
        """Extract wire segments as lists of connected points"""
        for wire in doc.get_wires():
            if wire.points and len(wire.points) >= 2:
                self.wire_segments.append(list(wire.points))

    def _find_net_at_position(self, x: int, y: int, tolerance: int = 5) -> Optional[str]:
        """
        Find net name at or near a given position

        Args:
            x, y: Position to check
            tolerance: Distance tolerance for matching (in 1/100 inch)

        Returns:
            Net name if found, None otherwise
        """
        # Check exact match first
        if (x, y) in self.net_names:
            return self.net_names[(x, y)]

        # Check nearby positions
        for (nx, ny), name in self.net_names.items():
            dist = ((x - nx)**2 + (y - ny)**2)**0.5
            if dist <= tolerance:
                return name

        # Check if position is on a wire segment
        for segment in self.wire_segments:
            for i in range(len(segment) - 1):
                x1, y1 = segment[i]
                x2, y2 = segment[i + 1]

                # Check if point is on the line segment
                if self._point_on_segment(x, y, x1, y1, x2, y2, tolerance):
                    # Find if this segment has a label
                    for point in segment:
                        if point in self.net_names:
                            return self.net_names[point]
                    # Return a generic net name based on wire position
                    return f"Net_{min(segment[0][0], segment[0][1])}"

        return None

    def _point_on_segment(self, px: int, py: int, x1: int, y1: int,
                         x2: int, y2: int, tolerance: int) -> bool:
        """Check if point (px, py) is on line segment from (x1,y1) to (x2,y2)"""
        # Calculate distance from point to line segment
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            # Degenerate segment
            return ((px - x1)**2 + (py - y1)**2)**0.5 <= tolerance

        # Parameter t of closest point on infinite line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        # Closest point on segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance from point to closest point
        dist = ((px - closest_x)**2 + (py - closest_y)**2)**0.5

        return dist <= tolerance

    def _convert_components(self, doc: SchDoc):
        """Convert Altium components to SKiDL parts"""
        for comp in doc.get_components():
            # Create a generic part (since we don't have library information)
            # In a full implementation, this would map to actual component libraries
            try:
                # Try to create a part with the library reference
                part_name = comp.library_reference or "R"

                # Create a template part
                part = Part(
                    lib='Device',
                    name=part_name,
                    dest=SKIDL,
                    tool=SKIDL,
                    ref=comp.designator or 'U?'
                )

                # Store for later connection
                self.parts[comp.designator] = part

                # Add description if available
                if comp.component_description:
                    part.description = comp.component_description

            except Exception as e:
                # If part creation fails, create a generic part
                print(f"Warning: Could not create part for {comp.designator}: {e}")
                # Create a generic resistor-like part as fallback
                part = Part(
                    lib='Device',
                    name='R',
                    dest=SKIDL,
                    tool=SKIDL,
                    ref=comp.designator or 'U?'
                )
                self.parts[comp.designator] = part

    def _connect_nets(self, doc: SchDoc):
        """Connect component pins based on wire connectivity"""
        # Build connectivity map: position -> list of pins at that position
        pin_positions: Dict[Tuple[int, int], List[Tuple[Component, Pin]]] = {}

        for comp in doc.get_components():
            for child in comp.children:
                if isinstance(child, Pin):
                    # Calculate absolute pin position
                    pin_x = comp.location_x + child.location_x
                    pin_y = comp.location_y + child.location_y

                    pos = (pin_x, pin_y)
                    if pos not in pin_positions:
                        pin_positions[pos] = []
                    pin_positions[pos].append((comp, child))

        # Connect pins at each wire endpoint
        for wire in doc.get_wires():
            if not wire.points or len(wire.points) < 2:
                continue

            # Check all points on the wire
            for point in wire.points:
                x, y = point

                # Find net name for this position
                net_name = self._find_net_at_position(x, y)

                if not net_name:
                    # Generate a net name based on position
                    net_name = f"N${x}_{y}"

                # Create net if it doesn't exist
                if net_name not in self.nets:
                    self.nets[net_name] = Net(net_name)

                net = self.nets[net_name]

                # Connect all pins at or near this position
                for pos, pins in pin_positions.items():
                    if self._point_on_segment(pos[0], pos[1], x, y, x, y, tolerance=10):
                        for comp, pin in pins:
                            if comp.designator in self.parts:
                                part = self.parts[comp.designator]

                                # Try to connect pin by number or name
                                try:
                                    pin_ref = pin.designator or pin.name or "1"
                                    if hasattr(part, f'p{pin_ref}'):
                                        getattr(part, f'p{pin_ref}') += net
                                    elif len(part.pins) > 0:
                                        # Connect to first available pin
                                        part.pins[0] += net
                                except Exception as e:
                                    print(f"Warning: Could not connect pin {pin.designator} of {comp.designator}: {e}")

    def generate_netlist(self, filename: Optional[str] = None) -> str:
        """
        Generate a netlist from the converted circuit

        Args:
            filename: Optional output filename (without extension)

        Returns:
            Netlist as string
        """
        if not self.circuit:
            raise ValueError("No circuit to generate netlist from. Call convert_schematic() first.")

        if filename:
            generate_netlist(file_=filename)
            return f"Netlist written to {filename}.net"
        else:
            # Generate to string
            return generate_netlist()

    def generate_svg(self, filename: str = "schematic.svg") -> str:
        """
        Generate an SVG schematic drawing

        Args:
            filename: Output SVG filename

        Returns:
            Path to generated SVG file
        """
        if not self.circuit:
            raise ValueError("No circuit to generate SVG from. Call convert_schematic() first.")

        try:
            generate_svg(filename=filename)
            return filename
        except Exception as e:
            return f"Error generating SVG: {e}"

    def print_circuit_summary(self):
        """Print a summary of the converted circuit"""
        print(f"\n=== SKiDL Circuit Summary ===")
        print(f"Parts: {len(self.parts)}")
        for ref, part in self.parts.items():
            print(f"  - {ref}: {part.name}")

        print(f"\nNets: {len(self.nets)}")
        for name, net in self.nets.items():
            connections = len(net.pins) if hasattr(net, 'pins') else 0
            print(f"  - {name}: {connections} connections")


def convert_altium_to_skidl(schematic_file: str) -> AltiumToSKiDL:
    """
    Convenience function to convert an Altium schematic file to SKiDL

    Args:
        schematic_file: Path to .SchDoc file

    Returns:
        AltiumToSKiDL converter instance with converted circuit
    """
    from altium_parser import parse_schematic

    # Parse Altium file
    doc = parse_schematic(schematic_file)

    # Convert to SKiDL
    converter = AltiumToSKiDL()
    converter.convert_schematic(doc)

    return converter


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python skidl_converter.py <input.SchDoc> [output_netlist]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Converting {input_file} to SKiDL...")
    converter = convert_altium_to_skidl(input_file)

    converter.print_circuit_summary()

    if output_file:
        converter.generate_netlist(output_file)
        print(f"\nNetlist written to {output_file}.net")
