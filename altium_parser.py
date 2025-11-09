"""
Altium SchDoc Parser
====================
Parses Altium SchDoc files into LLM-friendly Python objects.

This parser:
1. Reads OLE compound documents
2. Extracts records from FileHeader stream
3. Converts records into typed Python objects
4. Preserves all properties for round-trip integrity

Based on research from:
- https://github.com/gsuberland/altium_js
- https://github.com/vadmium/python-altium
"""

import struct
import olefile
from typing import Dict, List, Tuple, Optional, Any, Type
from altium_objects import *


class PropertyParser:
    """
    Parses pipe-delimited Altium properties.

    Format: |NAME=value|NAME=value|NAME=value|
    """

    @staticmethod
    def parse(data: bytes) -> Dict[str, str]:
        """
        Parse property data into a dictionary.

        Args:
            data: Raw property bytes (pipe-delimited)

        Returns:
            Dictionary of property name -> value
        """
        # Decode as ASCII/UTF-8, replacing errors
        try:
            text = data.decode('utf-8', errors='replace')
        except:
            text = data.decode('latin-1', errors='replace')

        # Remove null terminator if present
        if text.endswith('\x00'):
            text = text[:-1]

        properties = {}

        # Split by pipe character
        parts = text.split('|')

        for part in parts:
            if not part or '=' not in part:
                continue

            # Split on first equals sign only
            name, value = part.split('=', 1)
            properties[name.upper()] = value

        return properties

    @staticmethod
    def get_int(props: Dict[str, str], name: str, default: int = 0) -> int:
        """Get integer property value"""
        value = props.get(name.upper())
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    @staticmethod
    def get_bool(props: Dict[str, str], name: str, default: bool = False) -> bool:
        """Get boolean property value (T/F)"""
        value = props.get(name.upper())
        if value is None:
            return default
        return value.upper() == 'T'

    @staticmethod
    def get_float(props: Dict[str, str], name: str, default: float = 0.0) -> float:
        """Get float property value"""
        value = props.get(name.upper())
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @staticmethod
    def get_str(props: Dict[str, str], name: str, default: str = "") -> str:
        """Get string property value"""
        return props.get(name.upper(), default)


class RecordReader:
    """
    Reads binary records from Altium file streams.

    Record format:
    - 2 bytes: length (little-endian unsigned short)
    - 1 byte: zero (separator)
    - 1 byte: record type
    - N bytes: record data
    """

    @staticmethod
    def read_records(data: bytes) -> List[Tuple[int, bytes, Dict[str, str]]]:
        """
        Read all records from a data stream.

        Args:
            data: Raw stream data

        Returns:
            List of (record_type, raw_data, properties)
        """
        records = []
        pos = 0

        while pos + 4 <= len(data):
            # Read record header
            length = struct.unpack('<H', data[pos:pos+2])[0]
            zero_byte = data[pos+2]
            record_type = data[pos+3]

            # Validate zero byte
            if zero_byte != 0:
                # Try to recover by searching for next valid record
                pos += 1
                continue

            # Extract record data
            data_start = pos + 4
            data_end = data_start + length

            if data_end > len(data):
                break

            record_data = data[data_start:data_end]

            # Parse properties (most records have type 0 which is property list)
            properties = {}
            if record_type == 0:
                properties = PropertyParser.parse(record_data)

            records.append((record_type, record_data, properties))

            pos = data_end

        return records


class AltiumParser:
    """
    Main parser for Altium SchDoc files.

    Usage:
        parser = AltiumParser()
        doc = parser.parse_file("schematic.SchDoc")
    """

    def __init__(self):
        self.objects_by_index: Dict[int, AltiumObject] = {}

    def parse_file(self, filename: str) -> SchDoc:
        """
        Parse an Altium SchDoc file.

        Args:
            filename: Path to .SchDoc file

        Returns:
            SchDoc object containing all schematic data
        """
        ole = olefile.OleFileIO(filename)

        # Read main FileHeader stream
        if not ole.exists('FileHeader'):
            raise ValueError("Not a valid SchDoc file: missing FileHeader stream")

        file_header_data = ole.openstream('FileHeader').read()

        # Read Additional stream if present
        additional_data = None
        if ole.exists('Additional'):
            additional_data = ole.openstream('Additional').read()

        ole.close()

        # Parse records
        records = RecordReader.read_records(file_header_data)

        if additional_data:
            additional_records = RecordReader.read_records(additional_data)
            records.extend(additional_records)

        # Convert records to objects
        doc = self._build_document(records)

        return doc

    def _build_document(self, records: List[Tuple[int, bytes, Dict[str, str]]]) -> SchDoc:
        """
        Build a SchDoc object from parsed records.

        Args:
            records: List of (type, data, properties) tuples

        Returns:
            Complete SchDoc object
        """
        doc = SchDoc()
        self.objects_by_index = {}

        # First pass: create objects
        for idx, (record_type, raw_data, properties) in enumerate(records):
            obj = self._create_object(record_type, properties, idx)
            if obj:
                obj.properties = properties  # Store for round-trip
                self.objects_by_index[idx] = obj

        # Second pass: build hierarchy
        for idx, obj in self.objects_by_index.items():
            owner_index = PropertyParser.get_int(obj.properties, 'OWNERINDEX', -1)

            if owner_index >= 0 and owner_index in self.objects_by_index:
                parent = self.objects_by_index[owner_index]

                # Add to parent's children list if it has one
                if hasattr(parent, 'children'):
                    parent.children.append(obj)

        # Extract header and sheet
        if 0 in self.objects_by_index:
            doc.header = self.objects_by_index[0]

        # Find sheet (usually index 1, or first RECORD=31)
        for obj in self.objects_by_index.values():
            if isinstance(obj, Sheet):
                doc.sheet = obj
                break

        # Add all objects to document
        doc.objects = list(self.objects_by_index.values())

        return doc

    def _create_object(self, record_type: int, props: Dict[str, str], index: int) -> Optional[AltiumObject]:
        """
        Create an object from record properties.

        Args:
            record_type: Binary record type (usually 0)
            props: Parsed properties
            index: Record index in file

        Returns:
            Appropriate AltiumObject subclass or None
        """
        # Get RECORD property which indicates actual object type
        record_id = PropertyParser.get_int(props, 'RECORD', -1)

        if record_id == -1:
            # This is the file header (record 0, no RECORD property)
            if index == 0:
                return self._parse_header(props, index)
            return None

        # Map RECORD value to object type
        parsers = {
            RecordType.SHEET: self._parse_sheet,
            RecordType.COMPONENT: self._parse_component,
            RecordType.PIN: self._parse_pin,
            RecordType.WIRE: self._parse_wire,
            RecordType.NET_LABEL: self._parse_net_label,
            RecordType.POWER_PORT: self._parse_power_port,
            RecordType.JUNCTION: self._parse_junction,
            RecordType.PARAMETER: self._parse_parameter,
            RecordType.BUS: self._parse_bus,
            RecordType.BUS_ENTRY: self._parse_bus_entry,
            RecordType.LINE: self._parse_line,
            RecordType.RECTANGLE: self._parse_rectangle,
            RecordType.POLYLINE: self._parse_polyline,
            RecordType.POLYGON: self._parse_polygon,
            RecordType.ARC: self._parse_arc,
            RecordType.ELLIPSE: self._parse_ellipse,
            RecordType.LABEL: self._parse_label,
            RecordType.IMPLEMENTATION: self._parse_implementation,
            RecordType.IMPLEMENTATION_LIST: self._parse_implementation_list,
        }

        parser = parsers.get(record_id)
        if parser:
            return parser(props, index)

        # Unknown record type - create generic object
        obj = AltiumObject(record_type=RecordType(record_id) if record_id < 49 else RecordType.HEADER, index=index)
        return obj

    # ========================================================================
    # Individual Object Parsers
    # ========================================================================

    def _parse_header(self, props: Dict[str, str], index: int) -> Header:
        """Parse file header"""
        obj = Header()
        obj.index = index
        obj.version = PropertyParser.get_str(props, 'HEADER', obj.version)
        obj.weight = PropertyParser.get_int(props, 'WEIGHT', obj.weight)
        obj.minor_version = PropertyParser.get_int(props, 'MINORVERSION', obj.minor_version)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)
        return obj

    def _parse_sheet(self, props: Dict[str, str], index: int) -> Sheet:
        """Parse sheet properties"""
        obj = Sheet()
        obj.index = index

        # Parse fonts
        font_count = PropertyParser.get_int(props, 'FONTIDCOUNT', 0)
        for i in range(1, font_count + 1):
            font = {
                'size': PropertyParser.get_int(props, f'SIZE{i}', 10),
                'name': PropertyParser.get_str(props, f'FONTNAME{i}', 'Arial'),
                'bold': PropertyParser.get_bool(props, f'BOLD{i}', False),
                'italic': PropertyParser.get_bool(props, f'ITALIC{i}', False),
                'underline': PropertyParser.get_bool(props, f'UNDERLINE{i}', False),
            }
            obj.fonts.append(font)

        # Sheet size
        obj.use_custom_sheet = PropertyParser.get_bool(props, 'USECUSTOMSHEET', obj.use_custom_sheet)
        obj.custom_x = PropertyParser.get_int(props, 'CUSTOMX', obj.custom_x)
        obj.custom_y = PropertyParser.get_int(props, 'CUSTOMY', obj.custom_y)
        obj.custom_x_zones = PropertyParser.get_int(props, 'CUSTOMXZONES', obj.custom_x_zones)
        obj.custom_y_zones = PropertyParser.get_int(props, 'CUSTOMYZONES', obj.custom_y_zones)
        obj.custom_margin_width = PropertyParser.get_int(props, 'CUSTOMMARGINWIDTH', obj.custom_margin_width)

        # Grid and display
        obj.snap_grid_on = PropertyParser.get_bool(props, 'SNAPGRIDON', obj.snap_grid_on)
        obj.snap_grid_size = PropertyParser.get_int(props, 'SNAPGRIDSIZE', obj.snap_grid_size)
        obj.visible_grid_on = PropertyParser.get_bool(props, 'VISIBLEGRIDON', obj.visible_grid_on)
        obj.visible_grid_size = PropertyParser.get_int(props, 'VISIBLEGRIDSIZE', obj.visible_grid_size)

        obj.area_color = PropertyParser.get_int(props, 'AREACOLOR', obj.area_color)
        obj.display_unit = PropertyParser.get_int(props, 'DISPLAY_UNIT', obj.display_unit)

        return obj

    def _parse_component(self, props: Dict[str, str], index: int) -> Component:
        """Parse component"""
        obj = Component()
        obj.index = index

        obj.library_reference = PropertyParser.get_str(props, 'LIBREFERENCE', obj.library_reference)
        obj.component_description = PropertyParser.get_str(props, 'COMPONENTDESCRIPTION', obj.component_description)

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        orientation = PropertyParser.get_int(props, 'ORIENTATION', 0)
        obj.orientation = Orientation(orientation) if orientation in [0, 90, 180, 270] else Orientation.RIGHT

        obj.current_part_id = PropertyParser.get_int(props, 'CURRENTPARTID', obj.current_part_id)
        obj.part_count = PropertyParser.get_int(props, 'PARTCOUNT', obj.part_count)
        obj.display_mode_count = PropertyParser.get_int(props, 'DISPLAYMODECOUNT', obj.display_mode_count)
        obj.display_mode = PropertyParser.get_int(props, 'DISPLAYMODE', obj.display_mode)

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.area_color = PropertyParser.get_int(props, 'AREACOLOR', obj.area_color)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)

        obj.source_library_name = PropertyParser.get_str(props, 'SOURCELIBRARYNAME', obj.source_library_name)
        obj.sheet_part_filename = PropertyParser.get_str(props, 'SHEETPARTFILENAME', obj.sheet_part_filename)
        obj.target_filename = PropertyParser.get_str(props, 'TARGETFILENAME', obj.target_filename)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_pin(self, props: Dict[str, str], index: int) -> Pin:
        """Parse pin"""
        obj = Pin()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        electrical = PropertyParser.get_int(props, 'ELECTRICAL', 0)
        obj.electrical = PinElectrical(electrical) if electrical < 8 else PinElectrical.PASSIVE

        obj.pin_conglomerate = PropertyParser.get_int(props, 'PINCONGLOMERATE', obj.pin_conglomerate)

        obj.name = PropertyParser.get_str(props, 'NAME', obj.name)
        obj.designator = PropertyParser.get_str(props, 'DESIGNATOR', obj.designator)

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.name_color = PropertyParser.get_int(props, 'PINNAME_POSITIONCONGLOMERATE', obj.name_color)
        obj.designator_color = PropertyParser.get_int(props, 'PINDESIGNATOR_POSITIONCONGLOMERATE', obj.designator_color)

        obj.symbol_inner = PropertyParser.get_int(props, 'SYMBOL_INNER', obj.symbol_inner)
        obj.symbol_outer = PropertyParser.get_int(props, 'SYMBOL_OUTER', obj.symbol_outer)
        obj.symbol_inner_edge = PropertyParser.get_int(props, 'SYMBOL_INNEREDGE', obj.symbol_inner_edge)
        obj.symbol_outer_edge = PropertyParser.get_int(props, 'SYMBOL_OUTEREDGE', obj.symbol_outer_edge)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)

        obj.show_name = not PropertyParser.get_bool(props, 'ISHIDDEN', False)
        obj.show_designator = not PropertyParser.get_bool(props, 'ISHIDDEN', False)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_wire(self, props: Dict[str, str], index: int) -> Wire:
        """Parse wire"""
        obj = Wire()
        obj.index = index

        obj.points = self._parse_line_points(props)
        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_net_label(self, props: Dict[str, str], index: int) -> NetLabel:
        """Parse net label"""
        obj = NetLabel()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        obj.text = PropertyParser.get_str(props, 'TEXT', obj.text)

        orientation = PropertyParser.get_int(props, 'ORIENTATION', 0)
        obj.orientation = Orientation(orientation) if orientation in [0, 90, 180, 270] else Orientation.RIGHT

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.font_id = PropertyParser.get_int(props, 'FONTID', obj.font_id)

        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_power_port(self, props: Dict[str, str], index: int) -> PowerPort:
        """Parse power port"""
        obj = PowerPort()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        obj.text = PropertyParser.get_str(props, 'TEXT', obj.text)

        style = PropertyParser.get_int(props, 'STYLE', 0)
        obj.style = PowerPortStyle(style) if style < 10 else PowerPortStyle.POWER_GROUND

        orientation = PropertyParser.get_int(props, 'ORIENTATION', 0)
        obj.orientation = Orientation(orientation) if orientation in [0, 90, 180, 270] else Orientation.DOWN

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.font_id = PropertyParser.get_int(props, 'FONTID', obj.font_id)
        obj.show_net_name = PropertyParser.get_bool(props, 'SHOWNETNAME', obj.show_net_name)

        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_junction(self, props: Dict[str, str], index: int) -> Junction:
        """Parse junction"""
        obj = Junction()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_parameter(self, props: Dict[str, str], index: int) -> Parameter:
        """Parse parameter"""
        obj = Parameter()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        obj.text = PropertyParser.get_str(props, 'TEXT', obj.text)
        obj.name = PropertyParser.get_str(props, 'NAME', obj.name)

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.font_id = PropertyParser.get_int(props, 'FONTID', obj.font_id)

        obj.is_hidden = PropertyParser.get_bool(props, 'ISHIDDEN', obj.is_hidden)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)
        obj.is_mirrored = PropertyParser.get_bool(props, 'ISMIRRORED', obj.is_mirrored)

        orientation = PropertyParser.get_int(props, 'ORIENTATION', 0)
        obj.orientation = Orientation(orientation) if orientation in [0, 90, 180, 270] else Orientation.RIGHT

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)

        obj.read_only_state = PropertyParser.get_int(props, 'READONLYSTATE', obj.read_only_state)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_bus(self, props: Dict[str, str], index: int) -> Bus:
        """Parse bus"""
        obj = Bus()
        obj.index = index

        obj.points = self._parse_line_points(props)
        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_bus_entry(self, props: Dict[str, str], index: int) -> BusEntry:
        """Parse bus entry"""
        obj = BusEntry()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')
        obj.corner_x = self._parse_location(props, 'CORNERX')
        obj.corner_y = self._parse_location(props, 'CORNERY')

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_line(self, props: Dict[str, str], index: int) -> Line:
        """Parse line"""
        obj = Line()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')
        obj.corner_x = self._parse_location(props, 'CORNERX')
        obj.corner_y = self._parse_location(props, 'CORNERY')

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_rectangle(self, props: Dict[str, str], index: int) -> Rectangle:
        """Parse rectangle"""
        obj = Rectangle()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')
        obj.corner_x = self._parse_location(props, 'CORNERX')
        obj.corner_y = self._parse_location(props, 'CORNERY')

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.area_color = PropertyParser.get_int(props, 'AREACOLOR', obj.area_color)
        obj.is_solid = PropertyParser.get_bool(props, 'ISSOLID', obj.is_solid)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)
        obj.transparent = PropertyParser.get_bool(props, 'TRANSPARENT', obj.transparent)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_polyline(self, props: Dict[str, str], index: int) -> Polyline:
        """Parse polyline"""
        obj = Polyline()
        obj.index = index

        obj.points = self._parse_line_points(props)
        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)
        obj.line_shape = PropertyParser.get_int(props, 'LINESHAPE', obj.line_shape)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_polygon(self, props: Dict[str, str], index: int) -> Polygon:
        """Parse polygon"""
        obj = Polygon()
        obj.index = index

        obj.points = self._parse_line_points(props)
        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.area_color = PropertyParser.get_int(props, 'AREACOLOR', obj.area_color)
        obj.is_solid = PropertyParser.get_bool(props, 'ISSOLID', obj.is_solid)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)
        obj.transparent = PropertyParser.get_bool(props, 'TRANSPARENT', obj.transparent)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_arc(self, props: Dict[str, str], index: int) -> Arc:
        """Parse arc"""
        obj = Arc()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')
        obj.radius = PropertyParser.get_int(props, 'RADIUS', obj.radius)

        obj.start_angle = PropertyParser.get_float(props, 'STARTANGLE', obj.start_angle)
        obj.end_angle = PropertyParser.get_float(props, 'ENDANGLE', obj.end_angle)

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_ellipse(self, props: Dict[str, str], index: int) -> Ellipse:
        """Parse ellipse"""
        obj = Ellipse()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')
        obj.radius = PropertyParser.get_int(props, 'RADIUS', obj.radius)
        obj.secondary_radius = PropertyParser.get_int(props, 'SECONDARYRADIUS', obj.secondary_radius)

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.area_color = PropertyParser.get_int(props, 'AREACOLOR', obj.area_color)
        obj.is_solid = PropertyParser.get_bool(props, 'ISSOLID', obj.is_solid)
        obj.line_width = PropertyParser.get_int(props, 'LINEWIDTH', obj.line_width)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)
        obj.transparent = PropertyParser.get_bool(props, 'TRANSPARENT', obj.transparent)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_label(self, props: Dict[str, str], index: int) -> Label:
        """Parse label"""
        obj = Label()
        obj.index = index

        obj.location_x = self._parse_location(props, 'X')
        obj.location_y = self._parse_location(props, 'Y')

        obj.text = PropertyParser.get_str(props, 'TEXT', obj.text)

        orientation = PropertyParser.get_int(props, 'ORIENTATION', 0)
        obj.orientation = Orientation(orientation) if orientation in [0, 90, 180, 270] else Orientation.RIGHT

        obj.color = PropertyParser.get_int(props, 'COLOR', obj.color)
        obj.font_id = PropertyParser.get_int(props, 'FONTID', obj.font_id)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.owner_part_id = PropertyParser.get_int(props, 'OWNERPARTID', obj.owner_part_id)
        obj.is_not_accessible = PropertyParser.get_bool(props, 'ISNOTACCESIBLE', obj.is_not_accessible)
        obj.is_mirrored = PropertyParser.get_bool(props, 'ISMIRRORED', obj.is_mirrored)

        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_implementation(self, props: Dict[str, str], index: int) -> Implementation:
        """Parse implementation"""
        obj = Implementation()
        obj.index = index

        obj.model_name = PropertyParser.get_str(props, 'MODELNAME', obj.model_name)
        obj.model_type = PropertyParser.get_str(props, 'MODELTYPE', obj.model_type)
        obj.datafile_count = PropertyParser.get_int(props, 'DATAFILECOUNT', obj.datafile_count)
        obj.model_datafile_entity = PropertyParser.get_str(props, 'MODELDATAFILEENTITY', obj.model_datafile_entity)
        obj.model_datafile_kind = PropertyParser.get_str(props, 'MODELDATAFILEKIND', obj.model_datafile_kind)
        obj.is_current = PropertyParser.get_bool(props, 'ISCURRENT', obj.is_current)
        obj.database_model = PropertyParser.get_bool(props, 'DATABASEMODEL', obj.database_model)

        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        obj.unique_id = PropertyParser.get_str(props, 'UNIQUEID', obj.unique_id)

        return obj

    def _parse_implementation_list(self, props: Dict[str, str], index: int) -> ImplementationList:
        """Parse implementation list"""
        obj = ImplementationList()
        obj.index = index
        obj.owner_index = PropertyParser.get_int(props, 'OWNERINDEX', obj.owner_index)
        return obj

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _parse_location(self, props: Dict[str, str], prefix: str) -> int:
        """
        Parse location with fractional component.

        Altium stores coordinates as:
        - Main value: LOCATION.X or X
        - Fractional: LOCATION.X_FRAC (1/100,000 units)
        """
        # Try LOCATION.X format first
        value = PropertyParser.get_int(props, f'LOCATION.{prefix}', None)
        frac = PropertyParser.get_int(props, f'LOCATION.{prefix}_FRAC', 0)

        # If not found, try just X
        if value is None:
            value = PropertyParser.get_int(props, prefix, 0)
            frac = PropertyParser.get_int(props, f'{prefix}_FRAC', 0)

        # Combine main and fractional parts
        # Fractional part is in 1/100,000 units, main is in 1/100 inch
        # We'll ignore fractional for simplicity (usually very small)
        return value

    def _parse_line_points(self, props: Dict[str, str]) -> List[Tuple[int, int]]:
        """
        Parse polyline/polygon/wire points.

        Format: LOCATIONCOUNT=n, X1=, Y1=, X2=, Y2=, ...
        """
        points = []
        count = PropertyParser.get_int(props, 'LOCATIONCOUNT', 0)

        for i in range(1, count + 1):
            x = self._parse_location(props, f'X{i}')
            y = self._parse_location(props, f'Y{i}')
            points.append((x, y))

        return points
