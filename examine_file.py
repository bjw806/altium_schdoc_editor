#!/usr/bin/env python3
"""Quick script to examine the DI.SchDoc file structure"""

import olefile
import struct

def examine_schdoc(filename):
    print(f"Examining: {filename}\n")

    ole = olefile.OleFileIO(filename)

    print("=== OLE Streams ===")
    for stream in ole.listdir():
        stream_name = '/'.join(stream)
        size = ole.get_size(stream_name)
        print(f"  {stream_name}: {size} bytes")

    print("\n=== FileHeader Stream ===")
    if ole.exists('FileHeader'):
        data = ole.openstream('FileHeader').read()
        print(f"Total size: {len(data)} bytes")

        # Parse first few records
        print("\nFirst 5 records:")
        pos = 0
        for i in range(5):
            if pos + 4 > len(data):
                break

            length = struct.unpack('<H', data[pos:pos+2])[0]
            zero_byte = data[pos+2]
            record_type = data[pos+3]

            print(f"\n  Record {i}:")
            print(f"    Length: {length}")
            print(f"    Zero byte: {zero_byte}")
            print(f"    Type: {record_type}")

            if pos + 4 + length <= len(data):
                record_data = data[pos+4:pos+4+length]
                # Try to decode as ASCII
                try:
                    text = record_data.decode('ascii', errors='replace')
                    # Show first 200 chars
                    preview = text[:200] if len(text) > 200 else text
                    print(f"    Data preview: {preview!r}")
                except:
                    print(f"    Data (hex): {record_data[:50].hex()}")

            pos += 4 + length

    ole.close()

if __name__ == '__main__':
    examine_schdoc('DI.SchDoc')
