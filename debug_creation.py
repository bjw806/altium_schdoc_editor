#!/usr/bin/env python3
"""
Debug: 어디서 5개의 추가 객체가 생성되는지 추적
"""

import olefile
from altium_parser import RecordReader
from altium_objects import *
from altium_parser import PropertyParser, RecordType

ole = olefile.OleFileIO("DI.SchDoc")
data = ole.openstream('FileHeader').read()
ole.close()

records = RecordReader.read_records(data)
print(f"RecordReader found: {len(records)} records (indices 0-{len(records)-1})")
print()

# 직접 루프를 돌면서 확인
objects_by_index = {}

print("Creating objects from records...")
for idx, (record_type, raw_data, properties) in enumerate(records):
    record_id = PropertyParser.get_int(properties, 'RECORD', -1)

    # 마지막 10개와 이상한 RECORD 값 출력
    if idx >= len(records) - 10 or record_id > 100:
        print(f"  [{idx}] RECORD={record_id}, props_count={len(properties)}")

    # 간단한 객체 생성 (실제 파서 로직 없이)
    obj = AltiumObject(index=idx)
    obj.properties = properties
    objects_by_index[idx] = obj

print()
print(f"Created {len(objects_by_index)} objects")
print(f"objects_by_index keys: {min(objects_by_index.keys())} to {max(objects_by_index.keys())}")
print()

# RECORD > 100인 객체 찾기
high_records = []
for idx, obj in objects_by_index.items():
    record_id = PropertyParser.get_int(obj.properties, 'RECORD', -1)
    if record_id > 100:
        high_records.append((idx, record_id))

print(f"Objects with RECORD > 100: {len(high_records)}")
for idx, rec_id in high_records:
    print(f"  Index {idx}: RECORD={rec_id}")
