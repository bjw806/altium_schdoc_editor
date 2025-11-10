#!/usr/bin/env python3
"""
Index 문제 디버깅
"""

from altium_parser import RecordReader, PropertyParser
import olefile

ole = olefile.OleFileIO("DI.SchDoc")
data = ole.openstream('FileHeader').read()
ole.close()

records = RecordReader.read_records(data)

print("="*80)
print("레코드 Index 분석")
print("="*80)

print("\n처음 30개 레코드의 INDEXINSHEET 확인:")
for i, (record_type, raw_data, props) in enumerate(records[:30]):
    record_id = props.get('RECORD', 'HEADER' if i == 0 else '?')
    index_in_sheet = props.get('INDEXINSHEET', 'N/A')
    owner_index = props.get('OWNERINDEX', 'N/A')

    print(f"Loop index {i:3d}: RECORD={record_id:5s}, INDEXINSHEET={index_in_sheet:5s}, OWNERINDEX={owner_index:5s}")

# Component와 그 자식들 찾기
print("\n" + "="*80)
print("Component와 바로 다음 레코드들:")
print("="*80)

for i, (record_type, raw_data, props) in enumerate(records):
    record_id = props.get('RECORD', '?')

    if record_id == '1':  # Component
        print(f"\n{'='*60}")
        print(f"Loop index {i}: Component")
        index_in_sheet = props.get('INDEXINSHEET', 'N/A')
        lib_ref = props.get('LIBREFERENCE', 'N/A')
        print(f"  INDEXINSHEET: {index_in_sheet}")
        print(f"  LIBREFERENCE: {lib_ref}")

        # 다음 10개 레코드 확인
        print(f"\n  다음 레코드들:")
        for j in range(1, min(11, len(records) - i)):
            next_rec = records[i + j]
            next_props = next_rec[2]
            next_record_id = next_props.get('RECORD', '?')
            next_index = next_props.get('INDEXINSHEET', 'N/A')
            next_owner = next_props.get('OWNERINDEX', 'N/A')

            rec_name = {
                '2': 'Pin',
                '41': 'Parameter',
                '44': 'ImplList',
                '45': 'Impl',
            }.get(next_record_id, f'REC{next_record_id}')

            print(f"    [{i+j}] {rec_name:12s} INDEXINSHEET={next_index:5s} OWNERINDEX={next_owner:5s}")

        if i > 200:  # 처음 몇 개만
            break
