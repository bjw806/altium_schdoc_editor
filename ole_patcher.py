"""
OLE File Patcher
================
Patches existing OLE files by replacing stream contents.
This is more reliable than creating OLE files from scratch.
"""

import struct
import os


class OLEPatcher:
    """
    Simple OLE file patcher that can replace stream data.

    This works by:
    1. Parsing the existing OLE file structure
    2. Locating the target stream
    3. Replacing its data (may resize the file)
    """

    def __init__(self, filename):
        """Load an OLE file for patching"""
        with open(filename, 'rb') as f:
            self.data = bytearray(f.read())

        self.sector_size = 512
        self._parse_header()

    def _parse_header(self):
        """Parse OLE header"""
        # Signature check
        sig = self.data[0:8]
        if sig != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            raise ValueError("Not a valid OLE file")

        # Sector size
        sector_shift = struct.unpack('<H', self.data[30:32])[0]
        self.sector_size = 1 << sector_shift

        # First directory sector
        self.first_dir_sector = struct.unpack('<i', self.data[48:52])[0]

        # First FAT sector
        self.first_fat_sector = struct.unpack('<i', self.data[76:80])[0]

    def replace_stream(self, stream_name: str, new_data: bytes):
        """
        Replace a stream's data.

        Note: This is a simple implementation that works for streams
        where new data is similar size to old data.
        """
        # Find stream in directory
        dir_entry = self._find_stream(stream_name)
        if not dir_entry:
            raise ValueError(f"Stream '{stream_name}' not found")

        entry_index, start_sect, old_size = dir_entry

        # Calculate old and new sector counts
        old_sectors = (old_size + self.sector_size - 1) // self.sector_size
        new_sectors = (len(new_data) + self.sector_size - 1) // self.sector_size

        if new_sectors != old_sectors:
            # For now, only support same-size replacement
            # A full implementation would rebuild the FAT
            raise ValueError(f"Stream size change not supported yet (old={old_sectors} sectors, new={new_sectors} sectors)")

        # Replace data in sectors
        current_sect = start_sect
        data_offset = 0

        for i in range(new_sectors):
            # Calculate file offset for this sector
            file_offset = 512 + (current_sect * self.sector_size)

            # Calculate how much data to write
            remaining = len(new_data) - data_offset
            to_write = min(remaining, self.sector_size)

            # Write data
            self.data[file_offset:file_offset + to_write] = new_data[data_offset:data_offset + to_write]

            # Pad rest of sector if needed
            if to_write < self.sector_size:
                self.data[file_offset + to_write:file_offset + self.sector_size] = b'\x00' * (self.sector_size - to_write)

            data_offset += to_write

            # Get next sector from FAT
            current_sect = self._get_next_sector(current_sect)
            if current_sect == -2:  # ENDOFCHAIN
                break

        # Update size in directory entry
        dir_offset = 512 + (self.first_dir_sector * self.sector_size) + (entry_index * 128)
        struct.pack_into('<Q', self.data, dir_offset + 120, len(new_data))

    def _find_stream(self, stream_name: str):
        """
        Find a stream in the directory.

        Returns: (entry_index, start_sector, size) or None
        """
        # Read directory
        dir_sector = self.first_dir_sector
        entry_index = 0

        while dir_sector != -2:  # Not ENDOFCHAIN
            # Read directory sector
            offset = 512 + (dir_sector * self.sector_size)

            # Each directory entry is 128 bytes
            for i in range(self.sector_size // 128):
                entry_offset = offset + (i * 128)

                # Read entry name (UTF-16LE)
                name_bytes = self.data[entry_offset:entry_offset + 64]
                name_len = struct.unpack('<H', self.data[entry_offset + 64:entry_offset + 66])[0]

                if name_len > 0 and name_len <= 64:
                    name = name_bytes[:name_len - 2].decode('utf-16le', errors='ignore')

                    if name == stream_name:
                        # Found it!
                        start_sect = struct.unpack('<i', self.data[entry_offset + 116:entry_offset + 120])[0]
                        size = struct.unpack('<Q', self.data[entry_offset + 120:entry_offset + 128])[0]
                        return (entry_index, start_sect, size)

                entry_index += 1

            # Get next directory sector
            dir_sector = self._get_next_sector(dir_sector)

        return None

    def _get_next_sector(self, sector: int) -> int:
        """Get next sector from FAT"""
        # Read from FAT
        fat_sector = self.first_fat_sector
        fat_offset = 512 + (fat_sector * self.sector_size)

        # Each FAT entry is 4 bytes
        entry_offset = fat_offset + (sector * 4)
        next_sect = struct.unpack('<i', self.data[entry_offset:entry_offset + 4])[0]

        return next_sect

    def save(self, filename: str):
        """Save modified OLE file"""
        with open(filename, 'wb') as f:
            f.write(self.data)


def patch_schdoc_file(input_file: str, output_file: str, new_fileheader_data: bytes):
    """
    Patch a SchDoc file with new FileHeader data.

    Args:
        input_file: Source SchDoc file to use as template
        output_file: Output file path
        new_fileheader_data: New FileHeader stream data
    """
    import shutil

    # Copy input to output
    shutil.copy2(input_file, output_file)

    # Patch the output file
    patcher = OLEPatcher(output_file)

    try:
        patcher.replace_stream('FileHeader', new_fileheader_data)
        patcher.save(output_file)
    except ValueError as e:
        # If sizes don't match, we need a different approach
        # For now, just raise the error
        raise ValueError(f"Cannot patch file: {e}")
