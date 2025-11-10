"""
SKiDL to Altium Generator
==========================
Generates Altium .SchDoc schematics from SKiDL circuit definitions.

This module enables:
- Creating Altium schematics from SKiDL code
- Automatic component placement
- Wire routing between connected pins
- Visual schematic generation
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import replace
import math
from skidl import Part, Net, Pin as SKiDLPin
from altium_objects import (
    SchDoc, Component, Pin, Wire, NetLabel, PowerPort, Junction,
    Header, Sheet, Designator, Parameter, Implementation, ImplementationList,
    PinElectrical, Orientation, PowerPortStyle, RecordType
)
from altium_serializer import serialize_schematic


class SKiDLToAltium:
    """
    Generates Altium schematic documents from SKiDL circuits
    """

    def __init__(self):
        self.doc = SchDoc()
        self.components: Dict[str, Component] = {}
        self.nets: Dict[str, List[Tuple[Component, Pin]]] = {}
        self.layout_grid = 1000  # Grid spacing in 1/100 inch (10 inches)
        self.component_spacing = 500  # Space between components

    def generate_schematic(self, parts: List[Part] = None,
                          nets: List[Net] = None) -> SchDoc:
        """
        Generate an Altium schematic from SKiDL parts and nets

        Args:
            parts: List of SKiDL Part objects (if None, uses default_circuit)
            nets: List of SKiDL Net objects (if None, uses default_circuit)

        Returns:
            SchDoc object ready for serialization
        """
        # Get parts and nets from SKiDL's default circuit if not provided
        if parts is None:
            from skidl import default_circuit
            parts = default_circuit.parts if default_circuit else []

        if nets is None:
            from skidl import default_circuit
            nets = default_circuit.nets if default_circuit else []

        # Initialize document
        self._initialize_document()

        # Convert parts to components
        self._convert_parts_to_components(parts)

        # Layout components on schematic
        self._layout_components()

        # Extract net connectivity
        self._extract_net_connectivity(parts, nets)

        # Create wires and labels
        self._create_wires_and_labels()

        return self.doc

    def _initialize_document(self):
        """Initialize a new SchDoc with header and sheet"""
        # Create header
        self.doc.header = Header(
            version="Protel for Windows - Schematic Capture Binary File Version 5.0",
            weight=0,
            minor_version=13,
            unique_id="SKIDL_GENERATED"
        )

        # Create sheet with default settings
        self.doc.sheet = Sheet(
            system_font=1,
            area_color=0xFFFFFF,
            snap_grid_on=True,
            snap_grid_size=10,
            visible_grid_on=True,
            visible_grid_size=10,
            show_border=True
        )

        self.doc.objects = []

    def _convert_parts_to_components(self, parts: List[Part]):
        """Convert SKiDL parts to Altium components"""
        for part in parts:
            if not hasattr(part, 'ref') or part.ref is None:
                continue

            # Create component
            comp = Component(
                library_reference=part.name,
                component_description=getattr(part, 'description', ''),
                designator=part.ref,
                location_x=0,  # Will be set by layout algorithm
                location_y=0,
                orientation=Orientation.RIGHT,
                current_part_id=1,
                part_count=1,
                unique_id=f"COMP_{part.ref}"
            )

            # Create designator child
            designator = Designator(
                location_x=0,
                location_y=50,  # Above component
                text=part.ref,
                color=0x000000,
                font_id=1,
                owner_index=len(self.doc.objects)
            )

            # Create pins
            if hasattr(part, 'pins'):
                for i, pin in enumerate(part.pins):
                    # Determine pin electrical type
                    electrical = self._infer_pin_electrical_type(pin)

                    # Create pin
                    altium_pin = Pin(
                        location_x=0,
                        location_y=i * 100,  # Stack pins vertically
                        electrical=electrical,
                        name=pin.name if hasattr(pin, 'name') else f"Pin{i+1}",
                        designator=str(pin.num) if hasattr(pin, 'num') else str(i+1),
                        owner_index=len(self.doc.objects),
                        unique_id=f"PIN_{part.ref}_{i}"
                    )
                    comp.children.append(altium_pin)

            # Add designator as child
            comp.children.append(designator)

            # Store component
            self.components[part.ref] = comp
            self.doc.add_object(comp)

    def _infer_pin_electrical_type(self, pin: SKiDLPin) -> PinElectrical:
        """Infer Altium pin electrical type from SKiDL pin"""
        if not hasattr(pin, 'func') or pin.func is None:
            return PinElectrical.PASSIVE

        func_str = str(pin.func).upper()

        if 'INPUT' in func_str or 'IN' in func_str:
            return PinElectrical.INPUT
        elif 'OUTPUT' in func_str or 'OUT' in func_str:
            return PinElectrical.OUTPUT
        elif 'BIDIR' in func_str or 'IO' in func_str:
            return PinElectrical.IO
        elif 'POWER' in func_str or 'PWR' in func_str:
            return PinElectrical.POWER
        else:
            return PinElectrical.PASSIVE

    def _layout_components(self):
        """Arrange components in a grid layout"""
        cols = math.ceil(math.sqrt(len(self.components)))
        row = 0
        col = 0

        for ref, comp in self.components.items():
            # Calculate position
            x = col * self.layout_grid
            y = row * self.layout_grid

            # Update component position
            comp.location_x = x
            comp.location_y = y

            # Update designator position (relative to component)
            for child in comp.children:
                if isinstance(child, Designator):
                    child.location_x = 0
                    child.location_y = 100

            # Move to next grid position
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _extract_net_connectivity(self, parts: List[Part], nets: List[Net]):
        """Extract net connectivity from SKiDL parts and nets"""
        self.nets = {}

        # Build net connectivity map
        for net in nets:
            if not hasattr(net, 'name') or net.name is None:
                continue

            net_name = net.name
            if net_name not in self.nets:
                self.nets[net_name] = []

            # Get pins connected to this net
            if hasattr(net, 'pins'):
                for pin in net.pins:
                    if hasattr(pin, 'part') and hasattr(pin.part, 'ref'):
                        part_ref = pin.part.ref
                        if part_ref in self.components:
                            comp = self.components[part_ref]

                            # Find corresponding Altium pin
                            pin_num = str(pin.num) if hasattr(pin, 'num') else "1"
                            for altium_pin in comp.children:
                                if isinstance(altium_pin, Pin):
                                    if altium_pin.designator == pin_num:
                                        self.nets[net_name].append((comp, altium_pin))
                                        break

    def _create_wires_and_labels(self):
        """Create wires and net labels to connect pins"""
        # Process each net
        for net_name, connections in self.nets.items():
            if len(connections) < 2:
                continue

            # Check if this is a power net
            is_power_net = self._is_power_net(net_name)

            if is_power_net:
                # Create power ports instead of wires
                self._create_power_connections(net_name, connections)
            else:
                # Create wires connecting pins
                self._create_wire_connections(net_name, connections)

    def _is_power_net(self, net_name: str) -> bool:
        """Check if a net is a power/ground net"""
        power_keywords = ['VCC', 'VDD', 'VEE', 'VSS', 'GND', 'AGND', 'DGND',
                         'POWER', '+', '-', 'V+', 'V-']
        net_upper = net_name.upper()
        return any(keyword in net_upper for keyword in power_keywords)

    def _create_power_connections(self, net_name: str,
                                  connections: List[Tuple[Component, Pin]]):
        """Create power port connections for power/ground nets"""
        for comp, pin in connections:
            # Calculate absolute pin position
            pin_x = comp.location_x + pin.location_x
            pin_y = comp.location_y + pin.location_y

            # Determine power port style
            style = PowerPortStyle.POWER_GROUND if 'GND' in net_name.upper() else PowerPortStyle.ARROW

            # Create power port
            power_port = PowerPort(
                location_x=pin_x,
                location_y=pin_y,
                text=net_name,
                style=style,
                orientation=Orientation.DOWN,
                unique_id=f"PWR_{net_name}_{comp.designator}_{pin.designator}"
            )

            self.doc.add_object(power_port)

    def _create_wire_connections(self, net_name: str,
                                 connections: List[Tuple[Component, Pin]]):
        """Create wires to connect pins in a net"""
        if len(connections) < 2:
            return

        # Get absolute positions of all pins
        positions = []
        for comp, pin in connections:
            pin_x = comp.location_x + pin.location_x
            pin_y = comp.location_y + pin.location_y
            positions.append((pin_x, pin_y))

        # Create a simple star topology: connect all pins to the centroid
        center_x = sum(x for x, y in positions) // len(positions)
        center_y = sum(y for x, y in positions) // len(positions)

        # Add junction at center if more than 2 connections
        if len(connections) > 2:
            junction = Junction(
                location_x=center_x,
                location_y=center_y,
                unique_id=f"JCT_{net_name}"
            )
            self.doc.add_object(junction)

        # Create wires from each pin to center
        for pin_x, pin_y in positions:
            wire = Wire(
                points=[(pin_x, pin_y), (center_x, center_y)],
                unique_id=f"WIRE_{net_name}_{pin_x}_{pin_y}"
            )
            self.doc.add_object(wire)

        # Add net label at center
        label = NetLabel(
            location_x=center_x + 20,
            location_y=center_y + 20,
            text=net_name,
            unique_id=f"LABEL_{net_name}"
        )
        self.doc.add_object(label)

    def save_schematic(self, filename: str):
        """
        Save the generated schematic to an Altium .SchDoc file

        Args:
            filename: Output filename (should end with .SchDoc)
        """
        if not filename.endswith('.SchDoc'):
            filename += '.SchDoc'

        serialize_schematic(self.doc, filename)
        return filename


def generate_altium_from_skidl(output_file: str,
                               parts: List[Part] = None,
                               nets: List[Net] = None) -> str:
    """
    Convenience function to generate Altium schematic from SKiDL circuit

    Args:
        output_file: Output .SchDoc filename
        parts: List of SKiDL parts (if None, uses default_circuit)
        nets: List of SKiDL nets (if None, uses default_circuit)

    Returns:
        Path to generated file
    """
    generator = SKiDLToAltium()
    generator.generate_schematic(parts=parts, nets=nets)
    return generator.save_schematic(output_file)


if __name__ == "__main__":
    import sys
    from skidl import *

    # Example: Create a simple circuit
    print("Creating example SKiDL circuit...")

    # Define a simple voltage divider
    vcc = Net('VCC')
    gnd = Net('GND')
    out = Net('OUT')

    r1 = Part('Device', 'R', value='10k', ref='R1')
    r2 = Part('Device', 'R', value='10k', ref='R2')

    r1[1] += vcc
    r1[2] += out
    r2[1] += out
    r2[2] += gnd

    # Generate Altium schematic
    output_file = sys.argv[1] if len(sys.argv) > 1 else "skidl_generated.SchDoc"

    print(f"Generating Altium schematic: {output_file}")
    generate_altium_from_skidl(output_file)
    print(f"Schematic saved to {output_file}")
