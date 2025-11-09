"""
Simple OLE Compound Document Writer
===================================
Minimal implementation to write OLE files for Altium SchDoc.

This is a simplified writer that creates basic OLE compound documents
with the minimal structure needed for SchDoc files.
"""

import struct
import io
from typing import Dict, List


class OLEWriter:
    """
    Simple OLE Compound Document writer.

    Creates minimal OLE files with streams.
    """

    def __init__(self):
        self.streams: Dict[str, bytes] = {}

    def add_stream(self, name: str, data: bytes):
        """Add a stream to the OLE file"""
        self.streams[name] = data

    def save(self, filename: str):
        """
        Save the OLE file.

        This creates a minimal but valid OLE compound document.
        """
        # Sector size (512 bytes)
        SECTOR_SIZE = 512
        MINI_SECTOR_SIZE = 64

        # Build directory entries
        dir_entries = []

        # Calculate mini stream data (for small files < 4096 bytes)
        mini_stream_parts = []
        mini_stream_positions = {}  # stream_name -> position in mini stream
        mini_stream_offset = 0

        for name, data in self.streams.items():
            if len(data) < 4096:
                mini_stream_positions[name] = mini_stream_offset // MINI_SECTOR_SIZE
                # Pad to mini sector boundary
                padded = data + b'\x00' * (((len(data) + MINI_SECTOR_SIZE - 1) // MINI_SECTOR_SIZE) * MINI_SECTOR_SIZE - len(data))
                mini_stream_parts.append(padded)
                mini_stream_offset += len(padded)

        # Build mini stream data
        mini_stream_data = b''.join(mini_stream_parts)

        # Mini stream goes in regular sectors
        mini_stream_sectors = 0
        if mini_stream_data:
            mini_stream_sectors = (len(mini_stream_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
            mini_stream_data = mini_stream_data + b'\x00' * (mini_stream_sectors * SECTOR_SIZE - len(mini_stream_data))

        # Root entry (first entry)
        root_entry = self._make_dir_entry(
            name="Root Entry",
            type=5,  # Root storage
            color=1,  # Black
            did_left=-1,
            did_right=-1,
            did_child=1 if self.streams else -1,
            start_sect=0 if mini_stream_data else -2,  # Mini stream starts at sector 0
            size=len(mini_stream_data) if mini_stream_data else 0
        )
        dir_entries.append(root_entry)

        # Add stream entries
        stream_data_parts = []
        current_sector = 0

        for i, (name, data) in enumerate(self.streams.items(), 1):
            # Calculate sectors needed
            sectors_needed = (len(data) + SECTOR_SIZE - 1) // SECTOR_SIZE

            entry = self._make_dir_entry(
                name=name,
                type=2,  # Stream
                color=1,  # Black
                did_left=-1,
                did_right=-1,
                did_child=-1,
                start_sect=current_sector,
                size=len(data)
            )
            dir_entries.append(entry)

            # Pad data to sector boundary
            padded_data = data + b'\x00' * (sectors_needed * SECTOR_SIZE - len(data))
            stream_data_parts.append(padded_data)

            current_sector += sectors_needed

        # Pad directory entries to fill sectors
        while len(dir_entries) < 4:  # At least 4 entries for one sector
            dir_entries.append(self._make_empty_dir_entry())

        # Build directory data
        dir_data = b''.join(dir_entries)

        # Pad directory to sector boundary
        dir_sectors_needed = (len(dir_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
        dir_data = dir_data + b'\x00' * (dir_sectors_needed * SECTOR_SIZE - len(dir_data))

        # Build SAT (Sector Allocation Table)
        total_sectors = current_sector + dir_sectors_needed + 1  # +1 for SAT itself

        sat = []

        # Stream sectors - chain them together
        for i in range(current_sector - 1):
            sat.append(i + 1)  # Point to next sector

        if current_sector > 0:
            sat.append(-2)  # ENDOFCHAIN for last stream sector

        # Directory sectors - chain them together
        for i in range(dir_sectors_needed - 1):
            sat.append(current_sector + i + 1)

        sat.append(-2)  # ENDOFCHAIN for last directory sector

        # SAT sector itself
        sat.append(-3)  # SATSECT

        # Pad SAT to sector boundary
        sat_entries_per_sector = SECTOR_SIZE // 4
        while len(sat) < sat_entries_per_sector:
            sat.append(-1)  # FREESECT

        sat_data = struct.pack(f'<{len(sat)}i', *sat)

        # Build header
        header = self._make_header(
            num_fat_sectors=1,
            num_dir_sectors=dir_sectors_needed,
            first_dir_sector=current_sector,
            first_fat_sector=current_sector + dir_sectors_needed,
            total_sectors=total_sectors
        )

        # Write file
        with open(filename, 'wb') as f:
            f.write(header)  # Header (512 bytes)
            f.write(b''.join(stream_data_parts))  # Stream data
            f.write(dir_data)  # Directory
            f.write(sat_data)  # SAT

    def _make_header(self, num_fat_sectors, num_dir_sectors, first_dir_sector, first_fat_sector, total_sectors) -> bytes:
        """Create OLE file header"""
        header = io.BytesIO()

        # Signature
        header.write(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')

        # CLSID (16 bytes of zeros)
        header.write(b'\x00' * 16)

        # Minor version (0x003E)
        header.write(struct.pack('<H', 0x003E))

        # Major version (0x0003 for 512-byte sectors)
        header.write(struct.pack('<H', 0x0003))

        # Byte order (0xFFFE = little-endian)
        header.write(struct.pack('<H', 0xFFFE))

        # Sector size power (0x0009 = 512 bytes)
        header.write(struct.pack('<H', 0x0009))

        # Mini sector size power (0x0006 = 64 bytes)
        header.write(struct.pack('<H', 0x0006))

        # Reserved (6 bytes)
        header.write(b'\x00' * 6)

        # Total sectors (4 bytes) - can be 0 for v3
        header.write(struct.pack('<I', 0))

        # FAT sectors (4 bytes)
        header.write(struct.pack('<I', 0))

        # First directory sector
        header.write(struct.pack('<i', first_dir_sector))

        # Transaction signature (4 bytes)
        header.write(b'\x00' * 4)

        # Mini stream cutoff size (4096)
        header.write(struct.pack('<I', 4096))

        # First mini FAT sector (-2 = ENDOFCHAIN)
        header.write(struct.pack('<i', -2))

        # Number of mini FAT sectors (0)
        header.write(struct.pack('<I', 0))

        # First DIFAT sector (-2 = ENDOFCHAIN)
        header.write(struct.pack('<i', -2))

        # Number of DIFAT sectors (0)
        header.write(struct.pack('<I', 0))

        # DIFAT array (109 entries, first entry is SAT sector)
        difat = [first_fat_sector] + [-1] * 108
        for sect in difat:
            header.write(struct.pack('<i', sect))

        # Pad to 512 bytes
        current_size = header.tell()
        if current_size < 512:
            header.write(b'\x00' * (512 - current_size))

        return header.getvalue()

    def _make_dir_entry(self, name, type, color, did_left, did_right, did_child, start_sect, size) -> bytes:
        """Create a directory entry (128 bytes)"""
        entry = io.BytesIO()

        # Name (64 bytes, UTF-16LE)
        name_utf16 = name.encode('utf-16le')
        if len(name_utf16) > 62:
            name_utf16 = name_utf16[:62]

        entry.write(name_utf16)
        entry.write(b'\x00' * (64 - len(name_utf16)))

        # Name length (including null terminator)
        entry.write(struct.pack('<H', len(name_utf16) + 2))

        # Type (1=storage, 2=stream, 5=root)
        entry.write(struct.pack('<B', type))

        # Color (0=red, 1=black)
        entry.write(struct.pack('<B', color))

        # DID left
        entry.write(struct.pack('<i', did_left))

        # DID right
        entry.write(struct.pack('<i', did_right))

        # DID child
        entry.write(struct.pack('<i', did_child))

        # CLSID (16 bytes)
        entry.write(b'\x00' * 16)

        # State bits (4 bytes)
        entry.write(b'\x00' * 4)

        # Creation time (8 bytes)
        entry.write(b'\x00' * 8)

        # Modified time (8 bytes)
        entry.write(b'\x00' * 8)

        # Start sector
        entry.write(struct.pack('<i', start_sect))

        # Size (8 bytes, but we only use lower 4 bytes)
        entry.write(struct.pack('<Q', size))

        return entry.getvalue()

    def _make_empty_dir_entry(self) -> bytes:
        """Create an empty directory entry"""
        return self._make_dir_entry(
            name="",
            type=0,  # Empty
            color=1,
            did_left=-1,
            did_right=-1,
            did_child=-1,
            start_sect=-1,
            size=0
        )
