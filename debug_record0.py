#!/usr/bin/env python3
"""
RECORD=0인 5개 객체 조사
"""

from altium_parser import AltiumParser
from altium_objects import *

parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")

print("="*80)
print("RECORD=0 객체 조사")
print("="*80)

# RECORD=0인 객체 찾기 (Header 제외)
record0_objects = []
for obj in doc.objects:
    if not isinstance(obj, Header) and obj.record_type.value == 0:
        record0_objects.append(obj)

print(f"\n총 {len(record0_objects)}개의 RECORD=0 객체 발견 (Header 제외)")

for i, obj in enumerate(record0_objects, 1):
    print(f"\n{'='*60}")
    print(f"객체 {i}:")
    print(f"  타입: {type(obj).__name__}")
    print(f"  record_type: {obj.record_type.name} ({obj.record_type.value})")
    print(f"  index: {obj.index}")
    print(f"  owner_index: {obj.properties.get('OWNERINDEX', 'N/A')}")
    print(f"\n  속성:")
    for key, value in sorted(obj.properties.items()):
        # 긴 값은 잘라서 표시
        value_str = str(value)
        if len(value_str) > 60:
            value_str = value_str[:60] + "..."
        print(f"    {key}: {value_str}")

print("\n" + "="*80)
