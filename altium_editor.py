"""
Altium SchDoc Editor - High-Level API
======================================
Provides LLM-friendly methods for modifying Altium schematics.

This module offers intuitive, high-level operations like:
- Adding components
- Connecting wires
- Adding labels and power ports
- Modifying component properties

Designed specifically for AI/LLM usage with clear, simple interfaces.
"""

from typing import List, Tuple, Optional, Dict
from altium_objects import *
from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer
import uuid
import random


class SchematicEditor:
    """
    High-level editor for Altium schematics.

    Usage:
        editor = SchematicEditor()
        editor.load("input.SchDoc")

        # Add components
        u1 = editor.add_component("LM358", x=1000, y=2000, designator="U1")

        # Add connections
        editor.add_wire([(1000, 2000), (1500, 2000)])

        # Save changes
        editor.save("output.SchDoc")
    """

    def __init__(self):
        self.doc: Optional[SchDoc] = None
        self.parser = AltiumParser()
        self.serializer = AltiumSerializer()
        self._next_index = 0

    # ========================================================================
    # File Operations
    # ========================================================================

    def load(self, filename: str):
        """
        Load a SchDoc file.

        Args:
            filename: Path to .SchDoc file
        """
        self.doc = self.parser.parse_file(filename)
        self._update_next_index()

    def save(self, filename: str):
        """
        Save the schematic to a file.

        Args:
            filename: Output file path
        """
        if not self.doc:
            raise ValueError("No document loaded")

        self.serializer.serialize_file(self.doc, filename)

    def new(self):
        """Create a new blank schematic"""
        self.doc = SchDoc()

        # Create header
        header = Header()
        header.version = "Protel for Windows - Schematic Capture Binary File Version 5.0"
        header.weight = 0
        header.minor_version = 13
        header.unique_id = self._generate_uid()
        header.index = 0
        self.doc.header = header
        self.doc.objects.append(header)

        # Create sheet
        sheet = Sheet()
        sheet.index = 1
        sheet.fonts = [
            {'size': 10, 'name': 'Times New Roman', 'bold': False, 'italic': False, 'underline': False},
            {'size': 10, 'name': 'Arial', 'bold': False, 'italic': False, 'underline': False},
        ]
        self.doc.sheet = sheet
        self.doc.objects.append(sheet)

        self._next_index = 2

    # ========================================================================
    # Component Operations
    # ========================================================================

    def add_component(
        self,
        library_reference: str,
        x: int,
        y: int,
        designator: str = "U?",
        orientation: Orientation = Orientation.RIGHT,
        description: str = "",
        **properties
    ) -> Component:
        """
        Add a component to the schematic.

        Args:
            library_reference: Component library reference (e.g., "LM358", "R")
            x: X coordinate (in 1/100 inch units)
            y: Y coordinate (in 1/100 inch units)
            designator: Component designator (e.g., "U1", "R1")
            orientation: Component orientation (0, 90, 180, 270 degrees)
            description: Component description
            **properties: Additional properties

        Returns:
            Created Component object

        Example:
            comp = editor.add_component("LM358", 1000, 2000, "U1", Orientation.RIGHT)
        """
        self._ensure_doc()

        comp = Component()
        comp.index = self._get_next_index()
        comp.library_reference = library_reference
        comp.location_x = x
        comp.location_y = y
        comp.orientation = orientation
        comp.component_description = description
        comp.unique_id = self._generate_uid()
        comp.owner_part_id = -1

        # Add designator parameter
        designator_param = Parameter()
        designator_param.index = self._get_next_index()
        designator_param.text = designator
        designator_param.name = "Designator"
        designator_param.location_x = x
        designator_param.location_y = y + 50  # Offset above component
        designator_param.owner_index = comp.index
        designator_param.unique_id = self._generate_uid()

        comp.children.append(designator_param)
        self.doc.objects.append(comp)
        self.doc.objects.append(designator_param)

        return comp

    def find_component(self, designator: str) -> Optional[Component]:
        """
        Find a component by designator.

        Args:
            designator: Component designator (e.g., "U1")

        Returns:
            Component if found, None otherwise
        """
        self._ensure_doc()

        for comp in self.doc.get_components():
            # Check children for designator parameter
            for child in comp.children:
                if isinstance(child, Parameter) and child.name == "Designator":
                    if child.text == designator:
                        return comp

        return None

    def remove_component(self, component: Component):
        """
        Remove a component from the schematic.

        Args:
            component: Component to remove
        """
        self._ensure_doc()

        # Remove component and its children
        if component in self.doc.objects:
            self.doc.objects.remove(component)

        for child in component.children:
            if child in self.doc.objects:
                self.doc.objects.remove(child)

    # ========================================================================
    # Wire and Connection Operations
    # ========================================================================

    def add_wire(
        self,
        points: List[Tuple[int, int]],
        color: int = 0x000000,
        line_width: int = 1
    ) -> Wire:
        """
        Add a wire to the schematic.

        Args:
            points: List of (x, y) coordinate tuples
            color: Wire color (RGB integer)
            line_width: Line width

        Returns:
            Created Wire object

        Example:
            wire = editor.add_wire([(1000, 2000), (1500, 2000), (1500, 2500)])
        """
        self._ensure_doc()

        wire = Wire()
        wire.index = self._get_next_index()
        wire.points = points
        wire.color = color
        wire.line_width = line_width
        wire.unique_id = self._generate_uid()
        wire.owner_part_id = -1

        self.doc.objects.append(wire)
        return wire

    def add_junction(self, x: int, y: int, color: int = 0x000000) -> Junction:
        """
        Add a junction (connection dot) at a wire intersection.

        Args:
            x: X coordinate
            y: Y coordinate
            color: Junction color

        Returns:
            Created Junction object

        Example:
            junction = editor.add_junction(1500, 2000)
        """
        self._ensure_doc()

        junction = Junction()
        junction.index = self._get_next_index()
        junction.location_x = x
        junction.location_y = y
        junction.color = color
        junction.unique_id = self._generate_uid()
        junction.owner_part_id = -1

        self.doc.objects.append(junction)
        return junction

    def add_net_label(
        self,
        x: int,
        y: int,
        text: str,
        orientation: Orientation = Orientation.RIGHT
    ) -> NetLabel:
        """
        Add a net label.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Label text
            orientation: Label orientation

        Returns:
            Created NetLabel object

        Example:
            label = editor.add_net_label(1500, 2000, "VCC")
        """
        self._ensure_doc()

        label = NetLabel()
        label.index = self._get_next_index()
        label.location_x = x
        label.location_y = y
        label.text = text
        label.orientation = orientation
        label.unique_id = self._generate_uid()
        label.owner_part_id = -1

        self.doc.objects.append(label)
        return label

    def add_power_port(
        self,
        x: int,
        y: int,
        text: str = "GND",
        style: PowerPortStyle = PowerPortStyle.POWER_GROUND,
        orientation: Orientation = Orientation.DOWN
    ) -> PowerPort:
        """
        Add a power port (e.g., VCC, GND).

        Args:
            x: X coordinate
            y: Y coordinate
            text: Port name (e.g., "VCC", "GND")
            style: Power port style
            orientation: Port orientation

        Returns:
            Created PowerPort object

        Example:
            gnd = editor.add_power_port(1000, 1000, "GND", PowerPortStyle.POWER_GROUND)
            vcc = editor.add_power_port(1000, 3000, "VCC", PowerPortStyle.ARROW)
        """
        self._ensure_doc()

        port = PowerPort()
        port.index = self._get_next_index()
        port.location_x = x
        port.location_y = y
        port.text = text
        port.style = style
        port.orientation = orientation
        port.unique_id = self._generate_uid()
        port.owner_part_id = -1

        self.doc.objects.append(port)
        return port

    # ========================================================================
    # Graphical Objects
    # ========================================================================

    def add_line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: int = 0x000000,
        line_width: int = 1
    ) -> Line:
        """
        Add a line.

        Args:
            x1, y1: Start point
            x2, y2: End point
            color: Line color
            line_width: Line width

        Returns:
            Created Line object
        """
        self._ensure_doc()

        line = Line()
        line.index = self._get_next_index()
        line.location_x = x1
        line.location_y = y1
        line.corner_x = x2
        line.corner_y = y2
        line.color = color
        line.line_width = line_width
        line.unique_id = self._generate_uid()
        line.owner_part_id = -1

        self.doc.objects.append(line)
        return line

    def add_rectangle(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: int = 0x000000,
        fill_color: Optional[int] = None,
        is_solid: bool = False,
        line_width: int = 1
    ) -> Rectangle:
        """
        Add a rectangle.

        Args:
            x1, y1: First corner
            x2, y2: Opposite corner
            color: Border color
            fill_color: Fill color (None for no fill)
            is_solid: Whether to fill the rectangle
            line_width: Border width

        Returns:
            Created Rectangle object
        """
        self._ensure_doc()

        rect = Rectangle()
        rect.index = self._get_next_index()
        rect.location_x = x1
        rect.location_y = y1
        rect.corner_x = x2
        rect.corner_y = y2
        rect.color = color
        rect.area_color = fill_color if fill_color is not None else 0xFFFFFF
        rect.is_solid = is_solid
        rect.line_width = line_width
        rect.unique_id = self._generate_uid()
        rect.owner_part_id = -1

        self.doc.objects.append(rect)
        return rect

    def add_label(
        self,
        x: int,
        y: int,
        text: str,
        orientation: Orientation = Orientation.RIGHT,
        color: int = 0x000000,
        font_id: int = 1
    ) -> Label:
        """
        Add a text label.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Label text
            orientation: Text orientation
            color: Text color
            font_id: Font ID (1-based index into sheet fonts)

        Returns:
            Created Label object
        """
        self._ensure_doc()

        label = Label()
        label.index = self._get_next_index()
        label.location_x = x
        label.location_y = y
        label.text = text
        label.orientation = orientation
        label.color = color
        label.font_id = font_id
        label.unique_id = self._generate_uid()
        label.owner_part_id = -1

        self.doc.objects.append(label)
        return label

    # ========================================================================
    # Query Operations
    # ========================================================================

    def get_components(self) -> List[Component]:
        """Get all components in the schematic"""
        self._ensure_doc()
        return self.doc.get_components()

    def get_wires(self) -> List[Wire]:
        """Get all wires in the schematic"""
        self._ensure_doc()
        return self.doc.get_wires()

    def get_net_labels(self) -> List[NetLabel]:
        """Get all net labels in the schematic"""
        self._ensure_doc()
        return self.doc.get_net_labels()

    def get_power_ports(self) -> List[PowerPort]:
        """Get all power ports in the schematic"""
        self._ensure_doc()
        return self.doc.get_power_ports()

    def get_component_by_designator(self, designator: str) -> Optional[Component]:
        """
        Get component by its designator.

        Args:
            designator: Component designator (e.g., "U1", "R1")

        Returns:
            Component if found, None otherwise
        """
        return self.find_component(designator)

    def get_nets(self) -> Dict[str, List[Tuple[int, int]]]:
        """
        Get all nets and their wire points.

        Returns:
            Dictionary mapping net names to lists of points

        Note: This is a simplified implementation that groups by net labels.
        """
        self._ensure_doc()

        nets = {}

        # Group wires by net labels
        for label in self.doc.get_net_labels():
            net_name = label.text
            if net_name not in nets:
                nets[net_name] = []

            # Find nearby wires (simple proximity check)
            for wire in self.doc.get_wires():
                for point in wire.points:
                    # Check if any wire point is close to the label
                    if abs(point[0] - label.location_x) < 50 and abs(point[1] - label.location_y) < 50:
                        nets[net_name].extend(wire.points)
                        break

        return nets

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _ensure_doc(self):
        """Ensure a document is loaded"""
        if not self.doc:
            raise ValueError("No document loaded. Use load() or new() first.")

    def _get_next_index(self) -> int:
        """Get next available object index"""
        idx = self._next_index
        self._next_index += 1
        return idx

    def _update_next_index(self):
        """Update next index based on existing objects"""
        if not self.doc or not self.doc.objects:
            self._next_index = 0
            return

        max_index = max(obj.index for obj in self.doc.objects)
        self._next_index = max_index + 1

    def _generate_uid(self) -> str:
        """Generate a unique ID in Altium format"""
        # Altium uses 8-character base32-like IDs
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(random.choice(chars) for _ in range(8))

    # ========================================================================
    # Convenience Methods for Common Operations
    # ========================================================================

    def connect_points(
        self,
        point1: Tuple[int, int],
        point2: Tuple[int, int],
        add_junction: bool = False
    ) -> Wire:
        """
        Connect two points with a wire.

        Args:
            point1: First point (x, y)
            point2: Second point (x, y)
            add_junction: Whether to add junctions at endpoints

        Returns:
            Created Wire object
        """
        wire = self.add_wire([point1, point2])

        if add_junction:
            self.add_junction(*point1)
            self.add_junction(*point2)

        return wire

    def add_resistor(
        self,
        x: int,
        y: int,
        value: str = "10k",
        designator: str = "R?",
        orientation: Orientation = Orientation.RIGHT
    ) -> Component:
        """
        Add a resistor component.

        Args:
            x, y: Location
            value: Resistance value (e.g., "10k", "1M")
            designator: Component designator
            orientation: Component orientation

        Returns:
            Created Component object
        """
        comp = self.add_component("RES", x, y, designator, orientation)

        # Add value parameter
        value_param = Parameter()
        value_param.index = self._get_next_index()
        value_param.text = value
        value_param.name = "Value"
        value_param.location_x = x
        value_param.location_y = y - 50  # Offset below component
        value_param.owner_index = comp.index
        value_param.unique_id = self._generate_uid()

        comp.children.append(value_param)
        self.doc.objects.append(value_param)

        return comp

    def add_capacitor(
        self,
        x: int,
        y: int,
        value: str = "10uF",
        designator: str = "C?",
        orientation: Orientation = Orientation.RIGHT
    ) -> Component:
        """
        Add a capacitor component.

        Args:
            x, y: Location
            value: Capacitance value (e.g., "10uF", "100nF")
            designator: Component designator
            orientation: Component orientation

        Returns:
            Created Component object
        """
        comp = self.add_component("CAP", x, y, designator, orientation)

        # Add value parameter
        value_param = Parameter()
        value_param.index = self._get_next_index()
        value_param.text = value
        value_param.name = "Value"
        value_param.location_x = x
        value_param.location_y = y - 50
        value_param.owner_index = comp.index
        value_param.unique_id = self._generate_uid()

        comp.children.append(value_param)
        self.doc.objects.append(value_param)

        return comp

    def print_summary(self):
        """Print a summary of the schematic contents"""
        self._ensure_doc()

        print("Schematic Summary:")
        print(f"  Components: {len(self.doc.get_components())}")
        print(f"  Wires: {len(self.doc.get_wires())}")
        print(f"  Net Labels: {len(self.doc.get_net_labels())}")
        print(f"  Power Ports: {len(self.doc.get_power_ports())}")
        print(f"  Junctions: {len(self.doc.get_junctions())}")
        print(f"  Total Objects: {len(self.doc.objects)}")

        if self.doc.get_components():
            print("\nComponents:")
            for comp in self.doc.get_components():
                designator = "?"
                for child in comp.children:
                    if isinstance(child, Parameter) and child.name == "Designator":
                        designator = child.text
                        break
                print(f"  {designator}: {comp.library_reference} at ({comp.location_x}, {comp.location_y})")

    # ========================================================================
    # SKiDL Integration
    # ========================================================================

    def to_skidl(self):
        """
        Convert the current schematic to a SKiDL circuit

        Returns:
            AltiumToSKiDL converter instance with converted circuit
        """
        from skidl_converter import AltiumToSKiDL

        self._ensure_doc()

        converter = AltiumToSKiDL()
        converter.convert_schematic(self.doc)

        return converter

    def from_skidl(self, parts=None, nets=None):
        """
        Generate schematic from SKiDL circuit

        Args:
            parts: List of SKiDL Part objects (if None, uses default_circuit)
            nets: List of SKiDL Net objects (if None, uses default_circuit)

        Returns:
            Self for method chaining
        """
        from skidl_generator import SKiDLToAltium

        generator = SKiDLToAltium()
        self.doc = generator.generate_schematic(parts=parts, nets=nets)

        return self

    def render_svg(self, output_file: str = "schematic.svg") -> str:
        """
        Render schematic to SVG format

        Args:
            output_file: Output SVG filename

        Returns:
            Path to generated SVG file
        """
        from skidl_renderer import SchematicRenderer

        self._ensure_doc()

        renderer = SchematicRenderer()
        return renderer.render_to_svg(self.doc, output_file)

    def render_image(self, output_file: str = "schematic.png",
                    format: str = "png") -> str:
        """
        Render schematic to image format (PNG, JPEG, etc.)

        Args:
            output_file: Output image filename
            format: Image format ('png', 'jpg', 'jpeg')

        Returns:
            Path to generated image file
        """
        from skidl_renderer import SchematicRenderer

        self._ensure_doc()

        renderer = SchematicRenderer()
        return renderer.render_to_image(self.doc, output_file, format)

    def export_kicad(self, output_file: str = "schematic.kicad_sch") -> str:
        """
        Export schematic to KiCad format

        Args:
            output_file: Output KiCad schematic filename

        Returns:
            Path to generated KiCad file
        """
        from skidl_renderer import SchematicRenderer

        self._ensure_doc()

        renderer = SchematicRenderer()
        return renderer.render_to_kicad(self.doc, output_file)

    def generate_netlist(self, output_file: Optional[str] = None) -> str:
        """
        Generate netlist from schematic using SKiDL

        Args:
            output_file: Optional output filename (without extension)

        Returns:
            Netlist as string or confirmation message
        """
        converter = self.to_skidl()
        return converter.generate_netlist(output_file)

    def print_skidl_summary(self):
        """
        Print SKiDL circuit summary
        """
        converter = self.to_skidl()
        converter.print_circuit_summary()
