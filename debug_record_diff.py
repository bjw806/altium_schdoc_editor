#!/usr/bin/env python3
"""
5개 레코드 차이 분석
JSON: 1580개, MY PARSER: 1585개
"""

import json
from altium_parser import AltiumParser
from altium_objects import *

print("="*80)
print("레코드 개수 차이 분석")
print("="*80)

# 1. JSON 로드
with open("DI.json", "r") as f:
    json_data = json.load(f)

json_records = json_data["records"]
print(f"\nJSON 레코드: {len(json_records)}개")

# 2. 내 파서로 파싱
parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")
my_records = [obj for obj in doc.objects if not isinstance(obj, Header)]
print(f"MY PARSER 레코드: {len(my_records)}개")
print(f"차이: {len(my_records) - len(json_records)}개")

# 3. RECORD 타입별 개수 비교
def get_value(record, *keys):
    """대소문자 구분 없이 값 가져오기"""
    for key in keys:
        if key in record:
            return record[key]
        if key.upper() in record:
            return record[key.upper()]
        if key.lower() in record:
            return record[key.lower()]
        if key.capitalize() in record:
            return record[key.capitalize()]
    return None

print("\n" + "="*80)
print("RECORD 타입별 개수 비교")
print("="*80)

# JSON 레코드 타입 카운트
json_types = {}
for rec in json_records:
    rec_type = get_value(rec, 'RECORD', 'Record')
    if rec_type:
        json_types[rec_type] = json_types.get(rec_type, 0) + 1

# 내 파서 레코드 타입 카운트
my_types = {}
for obj in my_records:
    # RecordType enum에서 값 추출
    rec_type = str(obj.record_type.value)
    type_name = type(obj).__name__

    if rec_type not in my_types:
        my_types[rec_type] = {'count': 0, 'type_name': type_name}
    my_types[rec_type]['count'] += 1

# 비교
all_types = sorted(set(json_types.keys()) | set(my_types.keys()), key=lambda x: int(x))

print("\nRECORD | JSON | MY PARSER | 차이 | 타입")
print("-" * 60)

differences = []
for rec_type in all_types:
    json_count = json_types.get(rec_type, 0)
    my_count = my_types.get(rec_type, {}).get('count', 0)
    type_name = my_types.get(rec_type, {}).get('type_name', '?')
    diff = my_count - json_count

    status = "  " if diff == 0 else "✗"
    print(f"{status} {rec_type:4s} | {json_count:4d} | {my_count:9d} | {diff:+4d} | {type_name}")

    if diff != 0:
        differences.append((rec_type, json_count, my_count, diff, type_name))

# 차이 요약
print("\n" + "="*80)
print("차이 요약")
print("="*80)

if differences:
    print(f"\n차이가 있는 RECORD 타입: {len(differences)}개")
    for rec_type, json_count, my_count, diff, type_name in differences:
        print(f"  RECORD={rec_type} ({type_name}): JSON {json_count}개, MY {my_count}개 (차이 {diff:+d})")
else:
    print("\n모든 RECORD 타입의 개수가 일치합니다!")

print("\n" + "="*80)
