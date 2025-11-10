"""
OLE File Rebuilder
==================
Rebuilds OLE files from scratch, properly handling large files with multiple FAT sectors.
"""

import struct
import io
from typing import Dict, List, Tuple


class OLERebuilder:
    """
    Rebuilds OLE files with proper FAT support for large files.

    This reads streams from an existing file and recreates it with correct structure.
    """

    def __init__(self, template_file: str):
        """Initialize by reading template file"""
        import olefile

        self.template_file = template_file
        self.streams = {}

        # Read all streams from template
        ole = olefile.OleFileIO(template_file)
        for stream_path in ole.listdir():
            stream_name = stream_path[0] if len(stream_path) == 1 else '/'.join(stream_path)
            stream_data = ole.openstream(stream_path).read()
            self.streams[stream_name] = stream_data
        ole.close()

    def replace_stream(self, stream_name: str, new_data: bytes):
        """Replace a stream's data"""
        self.streams[stream_name] = new_data

    def save(self, filename: str):
        """
        Save rebuilt OLE file with proper FAT structure.

        This creates a valid OLE file that can handle large streams.
        """
        SECTOR_SIZE = 512

        # Calculate total sectors needed for all streams
        stream_info = []  # (name, start_sector, size, sector_count)
        current_sector = 0

        # Sort streams for consistent ordering (FileHeader, Storage, Additional)
        stream_order = ['FileHeader', 'Storage', 'Additional']
        sorted_streams = []
        for name in stream_order:
            if name in self.streams:
                sorted_streams.append((name, self.streams[name]))

        # Add any other streams not in the standard order
        for name, data in self.streams.items():
            if name not in stream_order:
                sorted_streams.append((name, data))

        # Calculate stream sectors
        for name, data in sorted_streams:
            sectors_needed = max(1, (len(data) + SECTOR_SIZE - 1) // SECTOR_SIZE)
            stream_info.append((name, current_sector, len(data), sectors_needed))
            current_sector += sectors_needed

        total_stream_sectors = current_sector

        # Calculate directory sectors (4 entries per sector minimum)
        num_streams = len(stream_info)
        dir_entries_needed = 1 + num_streams  # Root + streams
        dir_entries_per_sector = SECTOR_SIZE // 128
        dir_sectors_needed = max(1, (dir_entries_needed + dir_entries_per_sector - 1) // dir_entries_per_sector)

        dir_start_sector = total_stream_sectors

        # Calculate FAT sectors needed
        total_sectors_before_fat = total_stream_sectors + dir_sectors_needed

        # FAT needs to cover: stream sectors + directory sectors + FAT sectors themselves
        # Each FAT sector can hold 128 entries (512 / 4)
        entries_per_fat_sector = SECTOR_SIZE // 4

        # Iterate to find correct number of FAT sectors
        fat_sectors_needed = 1
        while True:
            total_sectors = total_sectors_before_fat + fat_sectors_needed
            required_fat_sectors = (total_sectors + entries_per_fat_sector - 1) // entries_per_fat_sector
            if required_fat_sectors <= fat_sectors_needed:
                break
            fat_sectors_needed = required_fat_sectors

        fat_start_sector = total_sectors_before_fat
        total_sectors = total_sectors_before_fat + fat_sectors_needed

        # Build FAT (Sector Allocation Table)
        fat = []

        # Stream sectors - chain them
        for _, start_sect, _, sectors in stream_info:
            for i in range(sectors):
                if i < sectors - 1:
                    fat.append(start_sect + i + 1)
                else:
                    fat.append(-2)  # ENDOFCHAIN

        # Directory sectors - chain them
        for i in range(dir_sectors_needed):
            if i < dir_sectors_needed - 1:
                fat.append(dir_start_sector + i + 1)
            else:
                fat.append(-2)  # ENDOFCHAIN

        # FAT sectors
        for i in range(fat_sectors_needed):
            fat.append(-3)  # SATSECT

        # Pad FAT to fill all FAT sectors
        total_fat_entries = fat_sectors_needed * entries_per_fat_sector
        while len(fat) < total_fat_entries:
            fat.append(-1)  # FREESECT

        # Build directory
        dir_entries = []

        # Root entry
        root_entry = self._make_dir_entry(
            name="Root Entry",
            type=5,  # Root storage
            color=1,  # Black
            did_left=-1,
            did_right=-1,
            did_child=1 if stream_info else -1,
            start_sect=-2,
            size=0
        )
        dir_entries.append(root_entry)

        # Stream entries - create a simple tree structure
        for i, (name, start_sect, size, _) in enumerate(stream_info):
            # Simple structure: all streams as children of root
            entry = self._make_dir_entry(
                name=name,
                type=2,  # Stream
                color=1,  # Black
                did_left=-1,
                did_right=i+2 if i+1 < len(stream_info) else -1,  # Next sibling
                did_child=-1,
                start_sect=start_sect,
                size=size
            )
            dir_entries.append(entry)

        # Pad directory
        while len(dir_entries) < dir_sectors_needed * dir_entries_per_sector:
            dir_entries.append(self._make_empty_dir_entry())

        # Build header
        header = self._make_header(
            num_fat_sectors=fat_sectors_needed,
            num_dir_sectors=dir_sectors_needed,
            first_dir_sector=dir_start_sector,
            first_fat_sector=fat_start_sector,
            total_sectors=total_sectors
        )

        # Write file
        with open(filename, 'wb') as f:
            # Write header
            f.write(header)

            # Write stream data
            for name, data in sorted_streams:
                # Find this stream's sector info
                for sname, start_sect, size, sectors in stream_info:
                    if sname == name:
                        # Pad to sector boundary
                        padded = data + b'\x00' * (sectors * SECTOR_SIZE - len(data))
                        f.write(padded)
                        break

            # Write directory
            dir_data = b''.join(dir_entries)
            f.write(dir_data)

            # Write FAT
            fat_data = struct.pack(f'<{len(fat)}i', *fat)
            f.write(fat_data)

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

        # Total sectors (4 bytes) - 0 for v3
        header.write(struct.pack('<I', 0))

        # FAT sectors (4 bytes)
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

        # DIFAT array (109 entries)
        # Fill with FAT sector numbers
        difat = []
        for i in range(min(num_fat_sectors, 109)):
            difat.append(first_fat_sector + i)
        while len(difat) < 109:
            difat.append(-1)

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

        # Size (8 bytes)
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


def rebuild_schdoc(template_file: str, output_file: str, new_fileheader: bytes):
    """
    Rebuild a SchDoc file with new FileHeader data.

    Args:
        template_file: Source file to use as template
        output_file: Output file path
        new_fileheader: New FileHeader stream data
    """
    rebuilder = OLERebuilder(template_file)
    rebuilder.replace_stream('FileHeader', new_fileheader)
    rebuilder.save(output_file)
