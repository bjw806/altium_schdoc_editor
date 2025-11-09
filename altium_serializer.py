"""
Altium SchDoc Serializer
=========================
Converts Python objects back to Altium SchDoc binary format.

This implements the complete reverse direction of the parser,
enabling round-trip integrity: parse → modify → serialize → parse

Based on the same format specification as the parser.
"""

import struct
import olefile
import shutil
import tempfile
import os
from typing import Dict, List, Tuple, Any
from altium_objects import *
import io


class PropertySerializer:
    """
    Serializes Python objects to pipe-delimited Altium properties.

    Format: |NAME=value|NAME=value|NAME=value|
    """

    @staticmethod
    def serialize(props: Dict[str, str]) -> bytes:
        """
        Serialize properties dictionary to pipe-delimited format.

        Args:
            props: Dictionary of property name -> value

        Returns:
            Bytes in Altium property format
        """
        parts = []

        for name, value in props.items():
            # Convert value to string
            value_str = str(value)
            parts.append(f"{name}={value_str}")

        # Join with pipes
        result = "|" + "|".join(parts) + "|"

        # Encode to bytes and add null terminator
        return result.encode('utf-8', errors='replace') + b'\x00'

    @staticmethod
    def build_props(base_props: Dict[str, str], **kwargs) -> Dict[str, str]:
        """
        Build properties dictionary, merging base props with updates.

        Args:
            base_props: Base properties (from original parse)
            **kwargs: Properties to add/update

        Returns:
            Merged properties dictionary
        """
        props = base_props.copy()

        for key, value in kwargs.items():
            if value is None:
                continue

            # Convert key to uppercase
            key = key.upper()

            # Convert value to string
            if isinstance(value, bool):
                value = 'T' if value else 'F'
            elif isinstance(value, (int, float)):
                value = str(value)
            elif isinstance(value, str):
                value = value
            else:
                value = str(value)

            props[key] = value

        return props


class RecordWriter:
    """
    Writes binary records in Altium format.

    Record format:
    - 2 bytes: length (little-endian unsigned short)
    - 1 byte: zero (separator)
    - 1 byte: record type (always 0 for property lists)
    - N bytes: record data
    """

    @staticmethod
    def write_record(record_data: bytes) -> bytes:
        """
        Write a single record with header.

        Args:
            record_data: Property data bytes

        Returns:
            Complete record with header
        """
        length = len(record_data)
        header = struct.pack('<H', length)  # 2-byte length
        header += b'\x00'  # Zero byte
        header += b'\x00'  # Record type (0 for property list)

        return header + record_data


class AltiumSerializer:
    """
    Main serializer for Altium SchDoc files.

    Usage:
        serializer = AltiumSerializer()
        serializer.serialize_file(doc, "output.SchDoc")
    """

    def __init__(self):
        self.index_map: Dict[int, int] = {}  # Old index -> new index

    def serialize_file(self, doc: SchDoc, filename: str, template_file: str = None):
        """
        Serialize a SchDoc object to file.

        Args:
            doc: SchDoc object to serialize
            filename: Output file path
            template_file: Optional template file to use for OLE structure (defaults to DI.SchDoc)
        """
        # Build records
        records = self._build_records(doc)
        file_header_data = b''.join(records)

        # Use template file or DI.SchDoc as template
        if template_file is None:
            template_file = 'DI.SchDoc'

        # Check if template exists
        if not os.path.exists(template_file):
            # Create minimal OLE file manually
            self._create_minimal_ole(filename, file_header_data)
            return

        # Copy template and modify streams
        try:
            # Copy template to output
            shutil.copy2(template_file, filename)

            # Open output file in write mode
            ole = olefile.OleFileIO(filename)

            # Replace FileHeader stream
            # Note: olefile can only replace with same-size data, so we need to work around this
            ole.close()

            # Use lower-level approach: read template, modify, write
            self._modify_ole_file(filename, file_header_data)

        except Exception as e:
            # Fallback to minimal OLE creation
            print(f"Warning: Could not use template, creating minimal OLE: {e}")
            self._create_minimal_ole(filename, file_header_data)

    def _modify_ole_file(self, filename: str, new_fileheader_data: bytes):
        """
        Modify an existing OLE file by replacing the FileHeader stream.

        This uses a simple approach: read sectors, find FileHeader, replace data.
        """
        from ole_patcher import OLEPatcher

        try:
            patcher = OLEPatcher(filename)
            patcher.replace_stream('FileHeader', new_fileheader_data)
            patcher.save(filename)
        except Exception as e:
            # If patching fails (e.g., size mismatch), fall back to creating new file
            print(f"Warning: Could not patch OLE file ({e}), creating new file")
            self._create_minimal_ole(filename, new_fileheader_data)

    def _create_minimal_ole(self, filename: str, fileheader_data: bytes):
        """
        Create a minimal OLE file with FileHeader and Storage streams.

        This creates a valid OLE compound document from scratch.
        """
        from ole_writer import OLEWriter

        ole = OLEWriter()
        ole.add_stream('FileHeader', fileheader_data)

        # Minimal Storage stream
        storage_data = b'\xd0\x00\x00\x00\x00\x00'
        ole.add_stream('Storage', storage_data)

        ole.save(filename)

    def _build_records(self, doc: SchDoc) -> List[bytes]:
        """
        Build all records from document.

        Args:
            doc: SchDoc object

        Returns:
            List of record bytes
        """
        records = []

        # Build index map
        self._build_index_map(doc)

        # Serialize header (must be first)
        if doc.header:
            records.append(self._serialize_header(doc.header))

        # Serialize sheet (usually second)
        if doc.sheet:
            records.append(self._serialize_sheet(doc.sheet))

        # Serialize all other objects in order
        for obj in doc.objects:
            if obj == doc.header or obj == doc.sheet:
                continue  # Already handled

            record = self._serialize_object(obj)
            if record:
                records.append(record)

        return records

    def _build_index_map(self, doc: SchDoc):
        """Build mapping of object indices for parent/child relationships"""
        self.index_map = {}

        # Assign new indices
        new_index = 0

        if doc.header:
            self.index_map[doc.header.index] = new_index
            doc.header.index = new_index
            new_index += 1

        if doc.sheet:
            self.index_map[doc.sheet.index] = new_index
            doc.sheet.index = new_index
            new_index += 1

        for obj in doc.objects:
            if obj == doc.header or obj == doc.sheet:
                continue

            self.index_map[obj.index] = new_index
            obj.index = new_index
            new_index += 1

    def _serialize_object(self, obj: AltiumObject) -> bytes:
        """
        Serialize any AltiumObject to binary record.

        Args:
            obj: Object to serialize

        Returns:
            Binary record data
        """
        serializers = {
            Header: self._serialize_header,
            Sheet: self._serialize_sheet,
            Component: self._serialize_component,
            Pin: self._serialize_pin,
            Wire: self._serialize_wire,
            NetLabel: self._serialize_net_label,
            PowerPort: self._serialize_power_port,
            Junction: self._serialize_junction,
            Parameter: self._serialize_parameter,
            Bus: self._serialize_bus,
            BusEntry: self._serialize_bus_entry,
            Line: self._serialize_line,
            Rectangle: self._serialize_rectangle,
            Polyline: self._serialize_polyline,
            Polygon: self._serialize_polygon,
            Arc: self._serialize_arc,
            Ellipse: self._serialize_ellipse,
            Label: self._serialize_label,
            Implementation: self._serialize_implementation,
            ImplementationList: self._serialize_implementation_list,
        }

        serializer = serializers.get(type(obj))
        if serializer:
            return serializer(obj)

        # Fallback: use stored properties
        if obj.properties:
            data = PropertySerializer.serialize(obj.properties)
            return RecordWriter.write_record(data)

        return b''

    # ========================================================================
    # Individual Object Serializers
    # ========================================================================

    def _serialize_header(self, obj: Header) -> bytes:
        """Serialize file header"""
        props = PropertySerializer.build_props(
            obj.properties,
            HEADER=obj.version,
            WEIGHT=obj.weight,
            MINORVERSION=obj.minor_version,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        # Remove RECORD property (header doesn't have it)
        props.pop('RECORD', None)

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_sheet(self, obj: Sheet) -> bytes:
        """Serialize sheet properties"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=31,
            FONTIDCOUNT=len(obj.fonts),
            USECUSTOMSHEET='T' if obj.use_custom_sheet else None,
            CUSTOMX=obj.custom_x if obj.use_custom_sheet else None,
            CUSTOMY=obj.custom_y if obj.use_custom_sheet else None,
            CUSTOMXZONES=obj.custom_x_zones if obj.use_custom_sheet else None,
            CUSTOMYZONES=obj.custom_y_zones if obj.use_custom_sheet else None,
            CUSTOMMARGINWIDTH=obj.custom_margin_width if obj.use_custom_sheet else None,
            SYSTEMFONT=obj.system_font,
            AREACOLOR=obj.area_color,
            SNAPGRIDON='T' if obj.snap_grid_on else 'F',
            SNAPGRIDSIZE=obj.snap_grid_size,
            VISIBLEGRIDON='T' if obj.visible_grid_on else 'F',
            VISIBLEGRIDSIZE=obj.visible_grid_size,
            DISPLAY_UNIT=obj.display_unit,
            REFERENCEZONESON='T' if obj.reference_zones_on else 'F',
            WORKSPACEORIENTATION=obj.workspace_orientation,
            HOTSPOTGRIDON='T' if obj.hot_spot_grid_on else 'F',
            HOTSPOTGRIDSIZE=obj.hot_spot_grid_size,
        )

        # Add font definitions
        for i, font in enumerate(obj.fonts, 1):
            props[f'SIZE{i}'] = str(font.get('size', 10))
            props[f'FONTNAME{i}'] = font.get('name', 'Arial')
            if font.get('bold'):
                props[f'BOLD{i}'] = 'T'
            if font.get('italic'):
                props[f'ITALIC{i}'] = 'T'
            if font.get('underline'):
                props[f'UNDERLINE{i}'] = 'T'

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_component(self, obj: Component) -> bytes:
        """Serialize component"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=1,
            LIBREFERENCE=obj.library_reference if obj.library_reference else None,
            COMPONENTDESCRIPTION=obj.component_description if obj.component_description else None,
        )

        # Location
        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            ORIENTATION=obj.orientation.value,
            CURRENTPARTID=obj.current_part_id,
            PARTCOUNT=obj.part_count if obj.part_count > 1 else None,
            DISPLAYMODECOUNT=obj.display_mode_count,
            DISPLAYMODE=obj.display_mode if obj.display_mode > 0 else None,
            COLOR=obj.color,
            AREACOLOR=obj.area_color,
            OWNERINDEX=obj.owner_index if obj.owner_index >= 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            SOURCELIBRARYNAME=obj.source_library_name if obj.source_library_name else None,
            SHEETPARTFILENAME=obj.sheet_part_filename if obj.sheet_part_filename else None,
            TARGETFILENAME=obj.target_filename if obj.target_filename else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_pin(self, obj: Pin) -> bytes:
        """Serialize pin"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=2,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            ELECTRICAL=obj.electrical.value,
            PINCONGLOMERATE=obj.pin_conglomerate,
            NAME=obj.name if obj.name else None,
            DESIGNATOR=obj.designator if obj.designator else None,
            COLOR=obj.color,
            OWNERINDEX=obj.owner_index,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_wire(self, obj: Wire) -> bytes:
        """Serialize wire"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=27,
            LOCATIONCOUNT=len(obj.points),
            COLOR=obj.color,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        # Add points
        for i, (x, y) in enumerate(obj.points, 1):
            self._add_location(props, f'X{i}', x)
            self._add_location(props, f'Y{i}', y)

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_net_label(self, obj: NetLabel) -> bytes:
        """Serialize net label"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=25,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            TEXT=obj.text,
            ORIENTATION=obj.orientation.value,
            COLOR=obj.color,
            FONTID=obj.font_id,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_power_port(self, obj: PowerPort) -> bytes:
        """Serialize power port"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=17,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            TEXT=obj.text,
            STYLE=obj.style.value,
            ORIENTATION=obj.orientation.value,
            COLOR=obj.color,
            FONTID=obj.font_id,
            SHOWNETNAME='T' if obj.show_net_name else 'F',
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_junction(self, obj: Junction) -> bytes:
        """Serialize junction"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=29,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            COLOR=obj.color,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_parameter(self, obj: Parameter) -> bytes:
        """Serialize parameter"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=41,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            TEXT=obj.text if obj.text else None,
            NAME=obj.name if obj.name else None,
            COLOR=obj.color,
            FONTID=obj.font_id,
            ISHIDDEN='T' if obj.is_hidden else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            ISMIRRORED='T' if obj.is_mirrored else None,
            ORIENTATION=obj.orientation.value if obj.orientation != Orientation.RIGHT else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            READONLYSTATE=obj.read_only_state if obj.read_only_state > 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_bus(self, obj: Bus) -> bytes:
        """Serialize bus"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=26,
            LOCATIONCOUNT=len(obj.points),
            COLOR=obj.color,
            LINEWIDTH=obj.line_width,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        # Add points
        for i, (x, y) in enumerate(obj.points, 1):
            self._add_location(props, f'X{i}', x)
            self._add_location(props, f'Y{i}', y)

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_bus_entry(self, obj: BusEntry) -> bytes:
        """Serialize bus entry"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=37,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)
        self._add_location(props, 'CORNERX', obj.corner_x)
        self._add_location(props, 'CORNERY', obj.corner_y)

        props = PropertySerializer.build_props(
            props,
            COLOR=obj.color,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_line(self, obj: Line) -> bytes:
        """Serialize line"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=13,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)
        self._add_location(props, 'CORNERX', obj.corner_x)
        self._add_location(props, 'CORNERY', obj.corner_y)

        props = PropertySerializer.build_props(
            props,
            COLOR=obj.color,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_rectangle(self, obj: Rectangle) -> bytes:
        """Serialize rectangle"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=14,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)
        self._add_location(props, 'CORNERX', obj.corner_x)
        self._add_location(props, 'CORNERY', obj.corner_y)

        props = PropertySerializer.build_props(
            props,
            COLOR=obj.color,
            AREACOLOR=obj.area_color,
            ISSOLID='T' if obj.is_solid else None,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            TRANSPARENT='T' if obj.transparent else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_polyline(self, obj: Polyline) -> bytes:
        """Serialize polyline"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=6,
            LOCATIONCOUNT=len(obj.points),
            COLOR=obj.color,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            LINESHAPE=obj.line_shape if obj.line_shape > 0 else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        # Add points
        for i, (x, y) in enumerate(obj.points, 1):
            self._add_location(props, f'X{i}', x)
            self._add_location(props, f'Y{i}', y)

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_polygon(self, obj: Polygon) -> bytes:
        """Serialize polygon"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=7,
            LOCATIONCOUNT=len(obj.points),
            COLOR=obj.color,
            AREACOLOR=obj.area_color,
            ISSOLID='T' if obj.is_solid else None,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            TRANSPARENT='T' if obj.transparent else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        # Add points
        for i, (x, y) in enumerate(obj.points, 1):
            self._add_location(props, f'X{i}', x)
            self._add_location(props, f'Y{i}', y)

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_arc(self, obj: Arc) -> bytes:
        """Serialize arc"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=12,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            RADIUS=obj.radius,
            STARTANGLE=obj.start_angle,
            ENDANGLE=obj.end_angle,
            COLOR=obj.color,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_ellipse(self, obj: Ellipse) -> bytes:
        """Serialize ellipse"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=8,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            RADIUS=obj.radius,
            SECONDARYRADIUS=obj.secondary_radius,
            COLOR=obj.color,
            AREACOLOR=obj.area_color,
            ISSOLID='T' if obj.is_solid else None,
            LINEWIDTH=obj.line_width if obj.line_width != 1 else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            TRANSPARENT='T' if obj.transparent else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_label(self, obj: Label) -> bytes:
        """Serialize label"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=4,
        )

        self._add_location(props, 'X', obj.location_x)
        self._add_location(props, 'Y', obj.location_y)

        props = PropertySerializer.build_props(
            props,
            TEXT=obj.text if obj.text else None,
            ORIENTATION=obj.orientation.value if obj.orientation != Orientation.RIGHT else None,
            COLOR=obj.color,
            FONTID=obj.font_id,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            OWNERPARTID=obj.owner_part_id if obj.owner_part_id >= 0 else None,
            ISNOTACCESIBLE='T' if obj.is_not_accessible else None,
            ISMIRRORED='T' if obj.is_mirrored else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_implementation(self, obj: Implementation) -> bytes:
        """Serialize implementation"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=45,
            MODELNAME=obj.model_name if obj.model_name else None,
            MODELTYPE=obj.model_type if obj.model_type else None,
            DATAFILECOUNT=obj.datafile_count,
            MODELDATAFILEENTITY=obj.model_datafile_entity if obj.model_datafile_entity else None,
            MODELDATAFILEKIND=obj.model_datafile_kind if obj.model_datafile_kind else None,
            ISCURRENT='T' if obj.is_current else None,
            DATABASEMODEL='T' if obj.database_model else None,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
            UNIQUEID=obj.unique_id if obj.unique_id else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    def _serialize_implementation_list(self, obj: ImplementationList) -> bytes:
        """Serialize implementation list"""
        props = PropertySerializer.build_props(
            obj.properties,
            RECORD=44,
            OWNERINDEX=obj.owner_index if obj.owner_index > 0 else None,
        )

        data = PropertySerializer.serialize(props)
        return RecordWriter.write_record(data)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _add_location(self, props: Dict[str, str], prefix: str, value: int):
        """
        Add location property with optional fractional part.

        For simplicity, we use LOCATION.X format without fractional parts.
        """
        props[f'LOCATION.{prefix}'] = str(value)
