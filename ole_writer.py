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

        # All streams are stored in regular sectors (no mini stream for simplicity)
        # Build stream data and track sectors
        stream_info = []  # (name, start_sector, size, sector_count)
        stream_data_parts = []
        current_sector = 0

        for name, data in self.streams.items():
            # Calculate sectors needed
            sectors_needed = max(1, (len(data) + SECTOR_SIZE - 1) // SECTOR_SIZE)

            stream_info.append((name, current_sector, len(data), sectors_needed))

            # Pad data to sector boundary
            padded_data = data + b'\x00' * (sectors_needed * SECTOR_SIZE - len(data))
            stream_data_parts.append(padded_data)

            current_sector += sectors_needed

        # Build directory entries
        dir_entries = []

        # Root entry (entry 0)
        root_entry = self._make_dir_entry(
            name="Root Entry",
            type=5,  # Root storage
            color=1,  # Black
            did_left=-1,
            did_right=-1,
            did_child=1 if stream_info else -1,  # First child is entry 1
            start_sect=-2,  # No data (ENDOFCHAIN)
            size=0
        )
        dir_entries.append(root_entry)

        # Add stream entries (balanced tree structure like Altium)
        # For 2-3 streams, use simple tree: middle node as root, others as children
        stream_count = len(stream_info)

        if stream_count == 1:
            # Single stream: just add it
            name, start_sect, size, _ = stream_info[0]
            entry = self._make_dir_entry(
                name=name, type=2, color=1,  # Black
                did_left=-1, did_right=-1, did_child=-1,
                start_sect=start_sect, size=size
            )
            dir_entries.append(entry)

        elif stream_count == 2:
            # Two streams: first is root (black), second is right child (red)
            name1, start1, size1, _ = stream_info[0]
            name2, start2, size2, _ = stream_info[1]

            # Entry 1: Root (black)
            entry1 = self._make_dir_entry(
                name=name1, type=2, color=1,  # Black
                did_left=-1, did_right=2, did_child=-1,
                start_sect=start1, size=size1
            )
            dir_entries.append(entry1)

            # Entry 2: Right child (red)
            entry2 = self._make_dir_entry(
                name=name2, type=2, color=0,  # Red
                did_left=-1, did_right=-1, did_child=-1,
                start_sect=start2, size=size2
            )
            dir_entries.append(entry2)

        else:
            # Three or more streams: build balanced tree
            # Like original: root node with left and right children
            # Entry order: left_child(2), right_child(1), root(3)
            # Root's child pointer goes to entry 3

            # For simplicity with 2 streams (FileHeader + Storage):
            # Storage, FileHeader, then root=Storage with FileHeader as right
            # But we'll use simpler approach: all streams directly under root
            for i, (name, start_sect, size, _) in enumerate(stream_info):
                # All as red nodes, no tree structure
                entry = self._make_dir_entry(
                    name=name, type=2, color=0,  # Red
                    did_left=-1, did_right=-1, did_child=-1,
                    start_sect=start_sect, size=size
                )
                dir_entries.append(entry)

        # Pad directory entries to fill at least one sector
        while len(dir_entries) < 4:  # At least 4 entries (512/128=4)
            dir_entries.append(self._make_empty_dir_entry())

        # Build directory data
        dir_data = b''.join(dir_entries)

        # Pad directory to sector boundary
        dir_sectors_needed = (len(dir_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
        dir_data = dir_data + b'\x00' * (dir_sectors_needed * SECTOR_SIZE - len(dir_data))

        # Build SAT (Sector Allocation Table)
        # Layout: [stream sectors] [directory sectors] [SAT sectors]
        sat = []

        # Stream sectors - chain each stream's sectors
        for _, start_sect, _, sectors in stream_info:
            for i in range(sectors):
                if i < sectors - 1:
                    sat.append(start_sect + i + 1)  # Point to next sector in chain
                else:
                    sat.append(-2)  # ENDOFCHAIN for last sector

        # Directory sectors - chain them together
        dir_start = current_sector
        for i in range(dir_sectors_needed):
            if i < dir_sectors_needed - 1:
                sat.append(dir_start + i + 1)
            else:
                sat.append(-2)  # ENDOFCHAIN

        # SAT sector(s)
        sat_start = dir_start + dir_sectors_needed
        sat.append(-3)  # SATSECT marker for SAT sector

        # Pad SAT to fill sector
        sat_entries_per_sector = SECTOR_SIZE // 4
        while len(sat) < sat_entries_per_sector:
            sat.append(-1)  # FREESECT

        sat_data = struct.pack(f'<{len(sat)}i', *sat)

        # Calculate number of FAT sectors needed
        total_stream_sectors = current_sector
        total_sectors = current_sector + dir_sectors_needed + 1  # +1 for SAT
        sat_entries_needed = total_sectors
        sat_sectors_needed = (sat_entries_needed * 4 + SECTOR_SIZE - 1) // SECTOR_SIZE

        # Build header
        header = self._make_header(
            num_fat_sectors=sat_sectors_needed,
            num_dir_sectors=dir_sectors_needed,
            first_dir_sector=dir_start,
            first_fat_sector=sat_start,
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

        # FAT sectors (4 bytes) - should be 0 for v3 OLE
        # But we'll set it anyway for compatibility
        header.write(struct.pack('<I', num_fat_sectors))

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
