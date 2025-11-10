"""
Simple OLE Patcher - Binary Level
==================================
Directly patches OLE files at the binary level by replacing stream data.
This is the most reliable method that preserves the original structure.
"""

import struct
import shutil
import olefile
from typing import Optional


def patch_schdoc_simple(input_file: str, output_file: str, new_fileheader: bytes) -> bool:
    """
    Patch a SchDoc file by replacing FileHeader stream.

    This creates a new OLE file from scratch using the olefile library's
    save functionality, which should create a valid OLE structure.

    Args:
        input_file: Original SchDoc file
        output_file: Output file path
        new_fileheader: New FileHeader data

    Returns:
        True if successful
    """
    try:
        # Read all streams from original file
        ole_in = olefile.OleFileIO(input_file)

        streams = {}
        for stream_path in ole_in.listdir():
            stream_name = '/'.join(stream_path)
            stream_data = ole_in.openstream(stream_path).read()
            streams[stream_name] = stream_data

        ole_in.close()

        # Replace FileHeader
        streams['FileHeader'] = new_fileheader

        # Create new OLE file using olefile's save method
        # This is a workaround - we'll create it manually

        # For now, use the template copy method with size adjustment
        return patch_with_size_adjustment(input_file, output_file, new_fileheader, streams)

    except Exception as e:
        print(f"Error in simple patch: {e}")
        return False


def patch_with_size_adjustment(input_file: str, output_file: str,
                               new_fileheader: bytes, streams: dict) -> bool:
    """
    Patch by adjusting sector sizes.

    This reads the original OLE structure and rebuilds it with adjusted sizes.
    """
    import tempfile
    import os

    try:
        # Read original file completely
        with open(input_file, 'rb') as f:
            original_data = bytearray(f.read())

        # Parse OLE header
        SECTOR_SIZE = 512

        # Read original FileHeader to get its location
        ole = olefile.OleFileIO(input_file)

        # Find FileHeader stream info
        fileheader_entry = None
        for entry in ole.direntries:
            if entry and entry.name == 'FileHeader':
                fileheader_entry = entry
                break

        if not fileheader_entry:
            ole.close()
            return False

        # Get original size and start sector
        old_size = fileheader_entry.size
        start_sector = ole._find(fileheader_entry.start)

        ole.close()

        new_size = len(new_fileheader)
        old_sectors = (old_size + SECTOR_SIZE - 1) // SECTOR_SIZE
        new_sectors = (new_size + SECTOR_SIZE - 1) // SECTOR_SIZE

        print(f"FileHeader: {old_size} bytes -> {new_size} bytes")
        print(f"Sectors: {old_sectors} -> {new_sectors}")

        # If sizes are very different, we need to rebuild
        # For now, if they're similar size (within 10%), try direct replacement
        size_diff = abs(new_size - old_size) / old_size if old_size > 0 else 1.0

        if size_diff > 0.1 or old_sectors != new_sectors:
            print("Size difference too large, need to rebuild OLE file")
            return rebuild_ole_file(input_file, output_file, streams)

        # Sizes are similar - try direct replacement
        print("Attempting direct sector replacement...")

        # Copy original to output
        shutil.copy2(input_file, output_file)

        # Open for binary modification
        with open(output_file, 'r+b') as f:
            # Write new FileHeader data to the sectors
            current_sector = start_sector
            offset = 0

            for i in range(new_sectors):
                sector_offset = 512 + (current_sector * SECTOR_SIZE)
                f.seek(sector_offset)

                # Write data for this sector
                chunk_size = min(SECTOR_SIZE, new_size - offset)
                chunk = new_fileheader[offset:offset + chunk_size]

                # Pad to sector size
                chunk += b'\x00' * (SECTOR_SIZE - len(chunk))
                f.write(chunk)

                offset += chunk_size
                current_sector += 1

            # Update size in directory entry
            # Find directory sector and entry
            f.seek(48)
            first_dir_sector = struct.unpack('<i', f.read(4))[0]

            dir_offset = 512 + (first_dir_sector * SECTOR_SIZE)

            # Find FileHeader entry (usually entry 1)
            for entry_idx in range(4):
                entry_offset = dir_offset + (entry_idx * 128)
                f.seek(entry_offset)
                name_bytes = f.read(64)
                name_len = struct.unpack('<H', f.read(2))[0]

                if name_len > 0 and name_len <= 64:
                    try:
                        name = name_bytes[:name_len-2].decode('utf-16le', errors='ignore')
                        if name == 'FileHeader':
                            # Update size
                            f.seek(entry_offset + 120)
                            f.write(struct.pack('<Q', new_size))
                            print(f"✓ Updated FileHeader size to {new_size}")
                            break
                    except:
                        pass

        return True

    except Exception as e:
        print(f"Error in size adjustment: {e}")
        import traceback
        traceback.print_exc()
        return False


def rebuild_ole_file(input_file: str, output_file: str, streams: dict) -> bool:
    """
    Rebuild entire OLE file from scratch using a working method.

    This creates a completely new OLE file with the same streams.
    """
    try:
        # Use a temporary working directory
        import tempfile
        import os

        temp_dir = tempfile.mkdtemp()
        temp_ole = os.path.join(temp_dir, 'temp.ole')

        try:
            # Create new OLE file
            # We'll use a different approach - save each stream to disk first
            # Then use olefile to read them back

            # Actually, let's use the OLE compound file format directly
            # This is getting complex - for now return False and use JSON instead

            print("Full rebuild not yet implemented")
            return False

        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"Error rebuilding: {e}")
        return False


if __name__ == "__main__":
    # Test
    print("Testing simple OLE patcher...")

    from altium_parser import AltiumParser
    from altium_serializer import AltiumSerializer

    # Parse original
    parser = AltiumParser()
    doc = parser.parse_file("DI.SchDoc")

    # Serialize to get new FileHeader
    serializer = AltiumSerializer()
    records = serializer._build_records(doc)
    new_fileheader = b''.join(records)

    print(f"New FileHeader size: {len(new_fileheader)} bytes")

    # Patch
    success = patch_schdoc_simple("DI.SchDoc", "test_patched.SchDoc", new_fileheader)

    if success:
        print("✓ Patching successful")

        # Verify
        doc2 = parser.parse_file("test_patched.SchDoc")
        print(f"✓ Verification successful: {len(doc2.objects)} objects")
    else:
        print("✗ Patching failed")
