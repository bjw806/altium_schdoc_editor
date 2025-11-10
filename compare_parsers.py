#!/usr/bin/env python3
"""
제 파서 vs json_parser.py 비교 검증
DI.json을 기준(ground truth)으로 사용
"""

import json
from altium_parser import AltiumParser
from altium_objects import *

print("="*80)
print("파서 비교 검증: altium_parser.py vs json_parser.py")
print("="*80)

# 1. json_parser.py 결과 로드 (기준)
print("\n1. json_parser.py 결과 로드 (기준)...")
with open("DI.json", "r") as f:
    json_data = json.load(f)

json_records = json_data["records"]
print(f"✓ JSON에서 {len(json_records)}개 레코드 로드")

# 2. 내 파서로 파싱
print("\n2. altium_parser.py로 파싱...")
parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")
print(f"✓ {len(doc.objects)}개 객체 파싱")

# 3. 레코드 개수 비교
print("\n" + "="*80)
print("3. 레코드 개수 비교")
print("="*80)
print(f"json_parser: {len(json_records)}개")
print(f"altium_parser: {len(doc.objects)}개")
print(f"차이: {len(doc.objects) - len(json_records)}개")

# 4. Component(RECORD=1) 비교
print("\n" + "="*80)
print("4. Component (RECORD=1) 비교")
print("="*80)

json_components = [r for r in json_records if r.get("RECORD") == "1"]
my_components = doc.get_components()

print(f"json_parser 부품: {len(json_components)}개")
print(f"altium_parser 부품: {len(my_components)}개")

# 첫 5개 부품 상세 비교
print("\n첫 5개 부품 비교:")
for i in range(min(5, len(json_components), len(my_components))):
    json_comp = json_components[i]
    my_comp = my_components[i]

    print(f"\n부품 {i+1}:")
    print(f"  JSON:")
    print(f"    LIBREFERENCE: {json_comp.get('LIBREFERENCE')}")
    print(f"    LOCATION.X: {json_comp.get('LOCATION.X')}")
    print(f"    LOCATION.Y: {json_comp.get('LOCATION.Y')}")
    print(f"    ORIENTATION: {json_comp.get('ORIENTATION')}")
    print(f"    index: {json_comp.get('index')}")
    print(f"    children: {len(json_comp.get('children', []))}개")

    print(f"  MY PARSER:")
    print(f"    library_reference: {my_comp.library_reference}")
    print(f"    location_x: {my_comp.location_x}")
    print(f"    location_y: {my_comp.location_y}")
    print(f"    orientation: {my_comp.orientation.value}")
    print(f"    index: {my_comp.index}")
    print(f"    children: {len(my_comp.children)}개")

    # 검증
    x_match = json_comp.get('LOCATION.X') == str(my_comp.location_x)
    y_match = json_comp.get('LOCATION.Y') == str(my_comp.location_y)
    lib_match = json_comp.get('LIBREFERENCE') == my_comp.library_reference
    orient_match = json_comp.get('ORIENTATION') == str(my_comp.orientation.value)

    print(f"  검증:")
    print(f"    위치 X: {'✓' if x_match else '✗'}")
    print(f"    위치 Y: {'✓' if y_match else '✗'}")
    print(f"    라이브러리: {'✓' if lib_match else '✗'}")
    print(f"    방향: {'✓' if orient_match else '✗'}")
    print(f"    자식 개수: {'✓' if len(json_comp.get('children', [])) == len(my_comp.children) else '✗'}")

# 5. Wire(RECORD=27) 비교
print("\n" + "="*80)
print("5. Wire (RECORD=27) 비교")
print("="*80)

json_wires = [r for r in json_records if r.get("RECORD") == "27"]
my_wires = doc.get_wires()

print(f"json_parser 배선: {len(json_wires)}개")
print(f"altium_parser 배선: {len(my_wires)}개")

# 첫 3개 배선 비교
print("\n첫 3개 배선 비교:")
for i in range(min(3, len(json_wires), len(my_wires))):
    json_wire = json_wires[i]
    my_wire = my_wires[i]

    # JSON에서 좌표 추출
    json_points = []
    j = 1
    while f'X{j}' in json_wire:
        x = int(json_wire[f'X{j}'])
        y = int(json_wire[f'Y{j}'])
        json_points.append((x, y))
        j += 1

    print(f"\n배선 {i+1}:")
    print(f"  JSON: {len(json_points)}개 점")
    for idx, (x, y) in enumerate(json_points):
        print(f"    {idx}: ({x}, {y})")

    print(f"  MY PARSER: {len(my_wire.points)}개 점")
    for idx, (x, y) in enumerate(my_wire.points):
        print(f"    {idx}: ({x}, {y})")

    # 검증
    points_match = json_points == my_wire.points
    print(f"  검증: {'✓' if points_match else '✗'}")

# 6. NetLabel(RECORD=25) 비교
print("\n" + "="*80)
print("6. NetLabel (RECORD=25) 비교")
print("="*80)

json_labels = [r for r in json_records if r.get("RECORD") == "25"]
my_labels = doc.get_net_labels()

print(f"json_parser 넷 라벨: {len(json_labels)}개")
print(f"altium_parser 넷 라벨: {len(my_labels)}개")

# 첫 5개 라벨 비교
print("\n첫 5개 넷 라벨 비교:")
for i in range(min(5, len(json_labels), len(my_labels))):
    json_label = json_labels[i]
    my_label = my_labels[i]

    print(f"\n라벨 {i+1}:")
    print(f"  JSON:")
    print(f"    TEXT: {json_label.get('TEXT')}")
    print(f"    LOCATION.X: {json_label.get('LOCATION.X')}")
    print(f"    LOCATION.Y: {json_label.get('LOCATION.Y')}")

    print(f"  MY PARSER:")
    print(f"    text: {my_label.text}")
    print(f"    location_x: {my_label.location_x}")
    print(f"    location_y: {my_label.location_y}")

    # 검증
    text_match = json_label.get('TEXT') == my_label.text
    x_match = json_label.get('LOCATION.X') == str(my_label.location_x)
    y_match = json_label.get('LOCATION.Y') == str(my_label.location_y)

    print(f"  검증:")
    print(f"    텍스트: {'✓' if text_match else '✗'}")
    print(f"    위치 X: {'✓' if x_match else '✗'}")
    print(f"    위치 Y: {'✓' if y_match else '✗'}")

# 7. Pin(RECORD=2) 비교
print("\n" + "="*80)
print("7. Pin (RECORD=2) 비교")
print("="*80)

json_pins = [r for r in json_records if r.get("RECORD") == "2"]
my_pins = [obj for obj in doc.objects if isinstance(obj, Pin)]

print(f"json_parser 핀: {len(json_pins)}개")
print(f"altium_parser 핀: {len(my_pins)}개")

# 8. 계층 구조 비교 (가장 중요!)
print("\n" + "="*80)
print("8. 계층 구조 비교 (핵심)")
print("="*80)

# JSON에서 첫 번째 Component와 그 자식들
first_json_comp = json_components[0]
print(f"\nJSON 첫 번째 Component:")
print(f"  index: {first_json_comp.get('index')}")
print(f"  LIBREFERENCE: {first_json_comp.get('LIBREFERENCE')}")
print(f"  자식: {len(first_json_comp.get('children', []))}개")

if 'children' in first_json_comp:
    print(f"  자식 타입:")
    child_types = {}
    for child in first_json_comp['children']:
        rec_type = child.get('RECORD', '?')
        child_types[rec_type] = child_types.get(rec_type, 0) + 1
    for rec_type, count in sorted(child_types.items()):
        print(f"    RECORD={rec_type}: {count}개")

# 내 파서에서 첫 번째 Component와 그 자식들
first_my_comp = my_components[0]
print(f"\nMY PARSER 첫 번째 Component:")
print(f"  index: {first_my_comp.index}")
print(f"  library_reference: {first_my_comp.library_reference}")
print(f"  자식: {len(first_my_comp.children)}개")

if first_my_comp.children:
    print(f"  자식 타입:")
    child_types = {}
    for child in first_my_comp.children:
        type_name = type(child).__name__
        child_types[type_name] = child_types.get(type_name, 0) + 1
    for type_name, count in sorted(child_types.items()):
        print(f"    {type_name}: {count}개")

# 9. 전체 요약
print("\n" + "="*80)
print("9. 전체 검증 요약")
print("="*80)

issues = []

if len(json_records) != len(doc.objects):
    issues.append(f"레코드 개수 불일치: {len(json_records)} vs {len(doc.objects)}")

if len(json_components) != len(my_components):
    issues.append(f"Component 개수 불일치: {len(json_components)} vs {len(my_components)}")

if len(json_wires) != len(my_wires):
    issues.append(f"Wire 개수 불일치: {len(json_wires)} vs {len(my_wires)}")

if len(json_labels) != len(my_labels):
    issues.append(f"NetLabel 개수 불일치: {len(json_labels)} vs {len(my_labels)}")

if len(json_pins) != len(my_pins):
    issues.append(f"Pin 개수 불일치: {len(json_pins)} vs {len(my_pins)}")

# 계층 구조 체크
if first_json_comp.get('children') and not first_my_comp.children:
    issues.append("계층 구조 미구성: JSON에는 자식이 있지만 내 파서에는 없음")

if issues:
    print("\n❌ 발견된 문제:")
    for issue in issues:
        print(f"  • {issue}")
else:
    print("\n✅ 모든 검증 통과!")

print("\n" + "="*80)
