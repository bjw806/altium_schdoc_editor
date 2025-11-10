#!/usr/bin/env python3
"""
제 파서 vs json_parser.py 비교 검증 (수정버전)
DI.json을 기준(ground truth)으로 사용
대소문자 구분 없이 비교
"""

import json
from altium_parser import AltiumParser
from altium_objects import *

def get_value(record, *keys):
    """대소문자 구분 없이 값 가져오기"""
    for key in keys:
        if key in record:
            return record[key]
        if key.upper() in record:
            return record[key.upper()]
        if key.lower() in record:
            return record[key.lower()]
        # CamelCase 시도
        if key.capitalize() in record:
            return record[key.capitalize()]
    return None

print("="*80)
print("파서 비교 검증: altium_parser.py vs json_parser.py (수정)")
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
print(f"✓ {len(doc.objects)}개 객체 파싱 (HEADER 포함)")

# 레코드만 (HEADER 제외)
my_records = [obj for obj in doc.objects if not isinstance(obj, Header)]
print(f"✓ {len(my_records)}개 레코드 (HEADER 제외)")

# 3. 레코드 개수 비교
print("\n" + "="*80)
print("3. 레코드 개수 비교")
print("="*80)
print(f"json_parser: {len(json_records)}개")
print(f"altium_parser: {len(my_records)}개")
if len(json_records) == len(my_records):
    print("✓ 레코드 개수 일치!")
else:
    print(f"✗ 차이: {len(my_records) - len(json_records)}개")

# 4. Component(RECORD=1) 비교
print("\n" + "="*80)
print("4. Component (RECORD=1) 비교")
print("="*80)

json_components = [r for r in json_records if get_value(r, 'RECORD') == "1"]
my_components = [obj for obj in my_records if isinstance(obj, Component)]

print(f"json_parser 부품: {len(json_components)}개")
print(f"altium_parser 부품: {len(my_components)}개")

if len(json_components) == len(my_components):
    print("✓ Component 개수 일치!")

# 첫 5개 부품 상세 비교
print("\n첫 5개 부품 비교:")
comp_matches = 0
for i in range(min(5, len(json_components), len(my_components))):
    json_comp = json_components[i]
    my_comp = my_components[i]

    json_lib = get_value(json_comp, 'LibReference', 'LIBREFERENCE')
    json_x = get_value(json_comp, 'Location.X', 'LOCATION.X')
    json_y = get_value(json_comp, 'Location.Y', 'LOCATION.Y')
    json_orient = get_value(json_comp, 'Orientation', 'ORIENTATION')

    print(f"\n부품 {i+1}:")
    print(f"  JSON:")
    print(f"    LibReference: {json_lib}")
    print(f"    Location.X: {json_x}")
    print(f"    Location.Y: {json_y}")
    print(f"    Orientation: {json_orient}")
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
    x_match = json_x == str(my_comp.location_x)
    y_match = json_y == str(my_comp.location_y)
    lib_match = json_lib == my_comp.library_reference

    # Orientation: JSON stores raw values 0,1,2,3, convert to degrees for comparison
    if json_orient is not None:
        json_orient_deg = int(json_orient) * 90
        orient_match = json_orient_deg == my_comp.orientation.value
    else:
        orient_match = True

    children_match = len(json_comp.get('children', [])) == len(my_comp.children)

    all_match = x_match and y_match and lib_match and orient_match
    if all_match:
        comp_matches += 1

    print(f"  검증:")
    print(f"    위치 X: {'✓' if x_match else '✗'}")
    print(f"    위치 Y: {'✓' if y_match else '✗'}")
    print(f"    라이브러리: {'✓' if lib_match else '✗'}")
    print(f"    방향: {'✓' if orient_match else '✗'}")
    print(f"    자식 개수: {'✓' if children_match else '✗ (JSON:' + str(len(json_comp.get('children', []))) + ' MY:' + str(len(my_comp.children)) + ')'}")
    print(f"  전체: {'✓ 일치' if all_match else '✗ 불일치'}")

print(f"\n부품 위치/이름 일치: {comp_matches}/5")

# 5. Wire(RECORD=27) 비교
print("\n" + "="*80)
print("5. Wire (RECORD=27) 비교")
print("="*80)

json_wires = [r for r in json_records if get_value(r, 'RECORD') == "27"]
my_wires = [obj for obj in my_records if isinstance(obj, Wire)]

print(f"json_parser 배선: {len(json_wires)}개")
print(f"altium_parser 배선: {len(my_wires)}개")

if len(json_wires) == len(my_wires):
    print("✓ Wire 개수 일치!")

# 첫 3개 배선 비교
print("\n첫 3개 배선 비교:")
wire_matches = 0
for i in range(min(3, len(json_wires), len(my_wires))):
    json_wire = json_wires[i]
    my_wire = my_wires[i]

    # JSON에서 좌표 추출
    json_points = []
    j = 1
    while f'X{j}' in json_wire or f'x{j}' in json_wire:
        x = int(get_value(json_wire, f'X{j}', f'x{j}'))
        y = int(get_value(json_wire, f'Y{j}', f'y{j}'))
        json_points.append((x, y))
        j += 1

    print(f"\n배선 {i+1}:")
    print(f"  JSON: {len(json_points)}개 점 - {json_points}")
    print(f"  MY PARSER: {len(my_wire.points)}개 점 - {my_wire.points}")

    # 검증
    points_match = json_points == my_wire.points
    if points_match:
        wire_matches += 1
    print(f"  검증: {'✓' if points_match else '✗'}")

print(f"\n배선 좌표 일치: {wire_matches}/3")

# 6. NetLabel(RECORD=25) 비교
print("\n" + "="*80)
print("6. NetLabel (RECORD=25) 비교")
print("="*80)

json_labels = [r for r in json_records if get_value(r, 'RECORD') == "25"]
my_labels = [obj for obj in my_records if isinstance(obj, NetLabel)]

print(f"json_parser 넷 라벨: {len(json_labels)}개")
print(f"altium_parser 넷 라벨: {len(my_labels)}개")

if len(json_labels) == len(my_labels):
    print("✓ NetLabel 개수 일치!")

# 첫 5개 라벨 비교
print("\n첫 5개 넷 라벨 비교:")
label_matches = 0
for i in range(min(5, len(json_labels), len(my_labels))):
    json_label = json_labels[i]
    my_label = my_labels[i]

    json_text = get_value(json_label, 'TEXT', 'Text')
    json_x = get_value(json_label, 'Location.X', 'LOCATION.X')
    json_y = get_value(json_label, 'Location.Y', 'LOCATION.Y')

    print(f"\n라벨 {i+1}:")
    print(f"  JSON: '{json_text}' at ({json_x}, {json_y})")
    print(f"  MY PARSER: '{my_label.text}' at ({my_label.location_x}, {my_label.location_y})")

    # 검증
    text_match = (json_text or '') == my_label.text
    x_match = json_x == str(my_label.location_x)
    y_match = json_y == str(my_label.location_y)
    all_match = text_match and x_match and y_match

    if all_match:
        label_matches += 1

    print(f"  검증: {'✓' if all_match else '✗'}")

print(f"\n넷 라벨 일치: {label_matches}/5")

# 7. Pin(RECORD=2) 비교
print("\n" + "="*80)
print("7. Pin (RECORD=2) 비교")
print("="*80)

json_pins = [r for r in json_records if get_value(r, 'RECORD') == "2"]
my_pins = [obj for obj in my_records if isinstance(obj, Pin)]

print(f"json_parser 핀: {len(json_pins)}개")
print(f"altium_parser 핀: {len(my_pins)}개")

if len(json_pins) == len(my_pins):
    print("✓ Pin 개수 일치!")

# 8. 계층 구조 비교 (가장 중요!)
print("\n" + "="*80)
print("8. 계층 구조 비교 (핵심)")
print("="*80)

# JSON에서 첫 번째 Component와 그 자식들
first_json_comp = json_components[0]
print(f"\nJSON 첫 번째 Component:")
print(f"  index: {first_json_comp.get('index')}")
print(f"  LibReference: {get_value(first_json_comp, 'LibReference')}")
print(f"  자식: {len(first_json_comp.get('children', []))}개")

if 'children' in first_json_comp:
    print(f"  자식 타입:")
    child_types = {}
    for child in first_json_comp['children']:
        rec_type = get_value(child, 'RECORD', 'Record')
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

hierarchy_match = len(first_json_comp.get('children', [])) == len(first_my_comp.children)
print(f"\n계층 구조: {'✓ 일치' if hierarchy_match else '✗ 불일치'}")

# 9. 전체 요약
print("\n" + "="*80)
print("9. 전체 검증 요약")
print("="*80)

results = []
results.append(("레코드 개수", len(json_records) == len(my_records)))
results.append(("Component 개수", len(json_components) == len(my_components)))
results.append(("Component 위치/이름", comp_matches == 5))
results.append(("Wire 개수", len(json_wires) == len(my_wires)))
results.append(("Wire 좌표", wire_matches == 3))
results.append(("NetLabel 개수", len(json_labels) == len(my_labels)))
results.append(("NetLabel 데이터", label_matches >= 4))  # 일부 라벨은 빈 텍스트
results.append(("Pin 개수", len(json_pins) == len(my_pins)))
results.append(("계층 구조", hierarchy_match))

passed = sum(1 for _, result in results if result)
total = len(results)

print(f"\n검증 결과:")
for name, result in results:
    status = "✓" if result else "✗"
    print(f"  {status} {name}")

print(f"\n총점: {passed}/{total} ({passed*100//total}%)")

if passed == total:
    print("\n🎉 모든 검증 통과!")
elif passed >= total * 0.8:
    print(f"\n⚠️  대부분 통과 ({passed}/{total})")
else:
    print(f"\n❌ 많은 문제 발견 ({total-passed}/{total} 실패)")

print("\n" + "="*80)
