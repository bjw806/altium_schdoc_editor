"""
Altium SchDoc Object Definitions
=================================
This module defines LLM-friendly data structures for all Altium schematic objects.
Each class is designed to be easily inspectable and modifiable.

Design Philosophy:
- Use simple, descriptive property names
- All coordinates in 1/100 inch units (can be converted to mm: value * 0.254)
- Colors as RGB integers (use color_to_rgb() and rgb_to_color() helpers)
- Clear type hints for all fields
- Preserve unknown properties for round-trip integrity
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import IntEnum


# ============================================================================
# Enumerations
# ============================================================================

class RecordType(IntEnum):
    """Altium record type identifiers"""
    HEADER = 0
    COMPONENT = 1
    PIN = 2
    IEEE_SYMBOL = 3
    LABEL = 4
    BEZIER = 5
    POLYLINE = 6
    POLYGON = 7
    ELLIPSE = 8
    PIECHART = 9
    ROUND_RECTANGLE = 10
    ELLIPTICAL_ARC = 11
    ARC = 12
    LINE = 13
    RECTANGLE = 14
    SHEET_SYMBOL = 15
    SHEET_ENTRY = 16
    POWER_PORT = 17
    PORT = 18
    NO_ERC = 22
    NET_LABEL = 25
    BUS = 26
    WIRE = 27
    TEXT_FRAME = 28
    JUNCTION = 29
    IMAGE = 30
    SHEET = 31
    SHEET_NAME = 32
    SHEET_FILE_NAME = 33
    DESIGNATOR = 34
    BUS_ENTRY = 37
    TEMPLATE = 39
    PARAMETER = 41
    WARNING_SIGN = 43
    IMPLEMENTATION_LIST = 44
    IMPLEMENTATION = 45
    RECORD_46 = 46
    RECORD_47 = 47
    RECORD_48 = 48
    # Hierarchical sheet entry objects (stored in Additional stream)
    SHEET_ENTRY_CONNECTION = 215
    SHEET_ENTRY_PORT = 216
    SHEET_ENTRY_LABEL = 217
    SHEET_ENTRY_LINE = 218


class PinElectrical(IntEnum):
    """Pin electrical types"""
    INPUT = 0
    IO = 1
    OUTPUT = 2
    OPEN_COLLECTOR = 3
    PASSIVE = 4
    HI_Z = 5
    OPEN_EMITTER = 6
    POWER = 7


class Orientation(IntEnum):
    """Object orientation in degrees"""
    RIGHT = 0      # 0°
    UP = 90        # 90°
    LEFT = 180     # 180°
    DOWN = 270     # 270°


class PowerPortStyle(IntEnum):
    """Power port symbol styles"""
    ARROW = 0
    BAR = 1
    WAVE = 2
    POWER_GROUND = 3
    SIGNAL_GROUND = 4
    EARTH = 5
    GOST_ARROW = 6
    GOST_POWER_GROUND = 7
    GOST_EARTH = 8
    GOST_BAR = 9


# ============================================================================
# Helper Functions
# ============================================================================

def color_to_rgb(color: int) -> Tuple[int, int, int]:
    """Convert Altium color integer to RGB tuple"""
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    return (r, g, b)


def rgb_to_color(r: int, g: int, b: int) -> int:
    """Convert RGB tuple to Altium color integer"""
    return r | (g << 8) | (b << 16)


def mils_to_mm(mils: float) -> float:
    """Convert 1/100 inch (mils/100) to millimeters"""
    return mils * 0.254


def mm_to_mils(mm: float) -> float:
    """Convert millimeters to 1/100 inch"""
    return mm / 0.254


# ============================================================================
# Base Classes
# ============================================================================

@dataclass
class AltiumObject:
    """
    Base class for all Altium schematic objects.

    All objects have:
    - record_type: The type of record
    - index: Position in the file (for parent/child relationships)
    - properties: Dictionary of all properties (for round-trip)
    """
    record_type: RecordType = RecordType.HEADER
    index: int = 0
    properties: Dict[str, str] = field(default_factory=dict)

    def get_property(self, name: str, default: Any = None) -> Any:
        """Get a property value with optional default"""
        return self.properties.get(name, default)

    def set_property(self, name: str, value: Any):
        """Set a property value"""
        self.properties[name] = str(value)


# ============================================================================
# Schematic Objects
# ============================================================================

@dataclass
class Header(AltiumObject):
    """
    File header record (always record 0)
    """
    version: str = "Protel for Windows - Schematic Capture Binary File Version 5.0"
    weight: int = 0
    minor_version: int = 13
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.HEADER


@dataclass
class Sheet(AltiumObject):
    """
    Schematic sheet properties (RECORD=31)
    Contains global settings like fonts, grid, paper size
    """
    # Font definitions
    fonts: List[Dict[str, Any]] = field(default_factory=list)

    # Sheet size and appearance
    use_custom_sheet: bool = False
    custom_x: int = 0  # in 1/100 inch
    custom_y: int = 0
    custom_x_zones: int = 0
    custom_y_zones: int = 0
    custom_margin_width: int = 0

    # System fonts
    system_font: int = 1
    area_color: int = 0xFFFFFF  # White
    snap_grid_on: bool = True
    snap_grid_size: int = 10
    visible_grid_on: bool = True
    visible_grid_size: int = 10

    # Border and title block
    display_unit: int = 4  # Imperial
    reference_zones_on: bool = True
    show_border: bool = True

    # Workspace settings
    workspace_orientation: int = 0
    hot_spot_grid_on: bool = True
    hot_spot_grid_size: int = 10

    def __post_init__(self):
        self.record_type = RecordType.SHEET


@dataclass
class Component(AltiumObject):
    """
    Schematic component (RECORD=1)
    Represents a symbol instance on the schematic
    """
    # Library reference
    library_reference: str = ""
    component_description: str = ""

    # Component designator (e.g., "R1", "U1", "C2")
    # Automatically extracted from RECORD=34 Designator child
    designator: str = ""

    # Position and orientation
    location_x: int = 0
    location_y: int = 0
    orientation: Orientation = Orientation.RIGHT

    # Multi-part component info
    current_part_id: int = 1
    part_count: int = 1
    display_mode_count: int = 1
    display_mode: int = 0

    # Appearance
    color: int = 0x000000  # Black

    # Ownership
    owner_index: int = -1
    owner_part_id: int = -1

    # Library path
    source_library_name: str = ""
    sheet_part_filename: str = ""
    target_filename: str = ""

    # Unique identifier
    unique_id: str = ""
    area_color: int = 0xFFFFFF

    # Child objects (pins, designators, etc.)
    children: List[AltiumObject] = field(default_factory=list)

    def __post_init__(self):
        self.record_type = RecordType.COMPONENT


@dataclass
class Pin(AltiumObject):
    """
    Component pin (RECORD=2)
    """
    # Position relative to component
    location_x: int = 0
    location_y: int = 0

    # Electrical properties
    electrical: PinElectrical = PinElectrical.PASSIVE
    pin_conglomerate: int = 0  # Bitfield for orientation and length

    # Pin name and number
    name: str = ""
    designator: str = ""

    # Appearance
    color: int = 0x000000
    name_color: int = 0x000000
    designator_color: int = 0x000000
    symbol_inner: int = 0
    symbol_outer: int = 0
    symbol_inner_edge: int = 0
    symbol_outer_edge: int = 0

    # Ownership
    owner_index: int = 0
    owner_part_id: int = -1

    # Display options
    show_name: bool = True
    show_designator: bool = True

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.PIN

    @property
    def orientation(self) -> Orientation:
        """Extract orientation from pin_conglomerate bitfield"""
        return Orientation((self.pin_conglomerate >> 2) & 0x3)

    @orientation.setter
    def orientation(self, value: Orientation):
        """Set orientation in pin_conglomerate bitfield"""
        self.pin_conglomerate = (self.pin_conglomerate & ~0xC) | ((value & 0x3) << 2)

    @property
    def length(self) -> int:
        """Extract length from pin_conglomerate bitfield"""
        return (self.pin_conglomerate >> 8) & 0xFF

    @length.setter
    def length(self, value: int):
        """Set length in pin_conglomerate bitfield"""
        self.pin_conglomerate = (self.pin_conglomerate & ~0xFF00) | ((value & 0xFF) << 8)


@dataclass
class Wire(AltiumObject):
    """
    Wire connection (RECORD=27)
    Represented as a polyline
    """
    points: List[Tuple[int, int]] = field(default_factory=list)  # List of (x, y) coordinates

    color: int = 0x000000
    line_width: int = 1

    owner_part_id: int = -1
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.WIRE


@dataclass
class NetLabel(AltiumObject):
    """
    Net label (RECORD=25)
    Text label attached to a net
    """
    location_x: int = 0
    location_y: int = 0

    text: str = ""
    orientation: Orientation = Orientation.RIGHT

    color: int = 0x000000
    font_id: int = 1

    owner_part_id: int = -1
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.NET_LABEL


@dataclass
class PowerPort(AltiumObject):
    """
    Power port symbol (RECORD=17)
    """
    location_x: int = 0
    location_y: int = 0

    text: str = "GND"
    style: PowerPortStyle = PowerPortStyle.POWER_GROUND
    orientation: Orientation = Orientation.DOWN

    color: int = 0x000000
    font_id: int = 1
    show_net_name: bool = True

    owner_part_id: int = -1
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.POWER_PORT


@dataclass
class Junction(AltiumObject):
    """
    Junction dot (RECORD=29)
    Indicates connection point where wires meet
    """
    location_x: int = 0
    location_y: int = 0

    color: int = 0x000000

    owner_part_id: int = -1
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.JUNCTION


@dataclass
class Parameter(AltiumObject):
    """
    Parameter/text label (RECORD=41)
    Can be component designator, value, or custom parameter
    """
    location_x: int = 0
    location_y: int = 0

    text: str = ""
    name: str = ""  # Parameter name (e.g., "Designator", "Value", "Comment")

    color: int = 0x000000
    font_id: int = 1

    is_hidden: bool = False
    is_not_accessible: bool = False
    is_mirrored: bool = False
    orientation: Orientation = Orientation.RIGHT

    owner_index: int = 0
    owner_part_id: int = -1

    read_only_state: int = 0
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.PARAMETER


@dataclass
class Bus(AltiumObject):
    """
    Bus connection (RECORD=26)
    Thicker line for bus connections
    """
    points: List[Tuple[int, int]] = field(default_factory=list)

    color: int = 0x000080  # Navy blue
    line_width: int = 3

    owner_part_id: int = -1
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.BUS


@dataclass
class BusEntry(AltiumObject):
    """
    Bus entry (RECORD=37)
    Connection between wire and bus
    """
    location_x: int = 0
    location_y: int = 0
    corner_x: int = 0
    corner_y: int = 0

    color: int = 0x000000

    owner_part_id: int = -1
    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.BUS_ENTRY


# ============================================================================
# Graphical Objects
# ============================================================================

@dataclass
class Line(AltiumObject):
    """
    Line shape (RECORD=13)
    """
    location_x: int = 0
    location_y: int = 0
    corner_x: int = 0
    corner_y: int = 0

    color: int = 0x000000
    line_width: int = 1

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.LINE


@dataclass
class Rectangle(AltiumObject):
    """
    Rectangle shape (RECORD=14)
    """
    location_x: int = 0
    location_y: int = 0
    corner_x: int = 0
    corner_y: int = 0

    color: int = 0x000000
    area_color: int = 0xFFFFFF
    is_solid: bool = False
    line_width: int = 1

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False
    transparent: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.RECTANGLE


@dataclass
class Polyline(AltiumObject):
    """
    Polyline shape (RECORD=6)
    """
    points: List[Tuple[int, int]] = field(default_factory=list)

    color: int = 0x000000
    line_width: int = 1
    line_shape: int = 0

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.POLYLINE


@dataclass
class Polygon(AltiumObject):
    """
    Polygon shape (RECORD=7)
    """
    points: List[Tuple[int, int]] = field(default_factory=list)

    color: int = 0x000000
    area_color: int = 0xFFFFFF
    is_solid: bool = False
    line_width: int = 1

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False
    transparent: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.POLYGON


@dataclass
class Arc(AltiumObject):
    """
    Arc shape (RECORD=12)
    """
    location_x: int = 0
    location_y: int = 0
    radius: int = 100

    start_angle: float = 0.0  # In degrees
    end_angle: float = 90.0

    color: int = 0x000000
    line_width: int = 1

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.ARC


@dataclass
class Ellipse(AltiumObject):
    """
    Ellipse shape (RECORD=8)
    """
    location_x: int = 0
    location_y: int = 0
    radius: int = 100
    secondary_radius: int = 100

    color: int = 0x000000
    area_color: int = 0xFFFFFF
    is_solid: bool = False
    line_width: int = 1

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False
    transparent: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.ELLIPSE


@dataclass
class Label(AltiumObject):
    """
    Text label (RECORD=4)
    """
    location_x: int = 0
    location_y: int = 0

    text: str = ""
    orientation: Orientation = Orientation.RIGHT

    color: int = 0x000000
    font_id: int = 1

    owner_index: int = 0
    owner_part_id: int = -1
    is_not_accessible: bool = False
    is_mirrored: bool = False

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.LABEL


# ============================================================================
# Special Records
# ============================================================================

@dataclass
class Implementation(AltiumObject):
    """
    Implementation record (RECORD=45)
    Links to footprints, simulation models, etc.
    """
    model_name: str = ""
    model_type: str = ""
    datafile_count: int = 0
    model_datafile_entity: str = ""
    model_datafile_kind: str = ""
    is_current: bool = False
    database_model: bool = False

    owner_index: int = 0

    unique_id: str = ""

    def __post_init__(self):
        self.record_type = RecordType.IMPLEMENTATION


@dataclass
class ImplementationList(AltiumObject):
    """
    Implementation list (RECORD=44)
    Container for implementation records
    """
    owner_index: int = 0

    children: List[Implementation] = field(default_factory=list)

    def __post_init__(self):
        self.record_type = RecordType.IMPLEMENTATION_LIST


@dataclass
class Port(AltiumObject):
    """
    Port object (RECORD=18)
    Hierarchical sheet port for connecting to other sheets
    """
    name: str = ""
    location_x: int = 0
    location_y: int = 0
    width: int = 0
    height: int = 0

    # Port styling
    color: int = 0
    area_color: int = 0
    font_id: int = 0

    # Port type
    harness_type: str = ""  # e.g., "I2C"

    owner_index: int = -1

    def __post_init__(self):
        self.record_type = RecordType.PORT


@dataclass
class NoERC(AltiumObject):
    """
    No ERC marker (RECORD=22)
    Marks location where electrical rule check should be suppressed
    """
    location_x: int = 0
    location_y: int = 0
    orientation: Orientation = Orientation.RIGHT

    is_active: bool = True
    color: int = 0

    owner_index: int = -1

    def __post_init__(self):
        self.record_type = RecordType.NO_ERC


@dataclass
class Designator(AltiumObject):
    """
    Designator text (RECORD=34)
    Visible component designator (e.g., R1, U1, C2)
    """
    name: str = "Designator"
    text: str = ""  # e.g., "R1", "U1"

    location_x: int = 0
    location_y: int = 0

    # Text styling
    color: int = 0
    font_id: int = 0

    owner_index: int = -1

    def __post_init__(self):
        self.record_type = RecordType.DESIGNATOR


@dataclass
class SheetEntryConnection(AltiumObject):
    """
    Sheet Entry Connection (RECORD=215)
    Connection point on hierarchical sheet symbol
    """
    location_x: int = 0
    location_y: int = 0

    x_size: int = 0
    y_size: int = 0

    color: int = 0
    area_color: int = 0
    line_width: int = 1

    primary_connection_position: int = 0

    def __post_init__(self):
        self.record_type = RecordType.SHEET_ENTRY_CONNECTION


@dataclass
class SheetEntryPort(AltiumObject):
    """
    Sheet Entry Port (RECORD=216)
    Named port on sheet entry (e.g., SCL, SDA)
    """
    name: str = ""

    # Port styling
    color: int = 0
    area_color: int = 0
    text_color: int = 0
    font_id: int = 0
    text_style: str = ""

    # Positioning
    side: int = 0  # Which side of sheet entry
    distance_from_top: int = 0
    distance_from_top_frac: float = 0.0

    def __post_init__(self):
        self.record_type = RecordType.SHEET_ENTRY_PORT


@dataclass
class SheetEntryLabel(AltiumObject):
    """
    Sheet Entry Label (RECORD=217)
    Text label on sheet entry (e.g., "I2C")
    """
    text: str = ""

    location_x: int = 0
    location_y: int = 0

    # Text styling
    color: int = 0
    font_id: int = 0
    justification: int = 0
    is_mirrored: bool = False

    not_auto_position: bool = False

    def __post_init__(self):
        self.record_type = RecordType.SHEET_ENTRY_LABEL


@dataclass
class SheetEntryLine(AltiumObject):
    """
    Sheet Entry Line (RECORD=218)
    Line segment on sheet entry border
    """
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0

    color: int = 0
    line_width: int = 1
    location_count: int = 2

    def __post_init__(self):
        self.record_type = RecordType.SHEET_ENTRY_LINE


# ============================================================================
# Document Container
# ============================================================================

@dataclass
class SchDoc:
    """
    Complete schematic document
    Contains all objects and provides high-level access
    """
    header: Optional[Header] = None
    sheet: Optional[Sheet] = None
    objects: List[AltiumObject] = field(default_factory=list)

    def get_components(self) -> List[Component]:
        """Get all components in the schematic"""
        return [obj for obj in self.objects if isinstance(obj, Component)]

    def get_wires(self) -> List[Wire]:
        """Get all wires in the schematic"""
        return [obj for obj in self.objects if isinstance(obj, Wire)]

    def get_net_labels(self) -> List[NetLabel]:
        """Get all net labels in the schematic"""
        return [obj for obj in self.objects if isinstance(obj, NetLabel)]

    def get_power_ports(self) -> List[PowerPort]:
        """Get all power ports in the schematic"""
        return [obj for obj in self.objects if isinstance(obj, PowerPort)]

    def get_junctions(self) -> List[Junction]:
        """Get all junctions in the schematic"""
        return [obj for obj in self.objects if isinstance(obj, Junction)]

    def get_parameters(self) -> List[Parameter]:
        """Get all parameters in the schematic"""
        return [obj for obj in self.objects if isinstance(obj, Parameter)]

    def add_object(self, obj: AltiumObject):
        """Add an object to the schematic"""
        self.objects.append(obj)

    def remove_object(self, obj: AltiumObject):
        """Remove an object from the schematic"""
        if obj in self.objects:
            self.objects.remove(obj)
