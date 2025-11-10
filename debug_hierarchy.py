#!/usr/bin/env python3
"""
부모-자식 관계 디버깅 스크립트
왜 핀과 파라미터가 부품에 연결되지 않는지 확인
"""

from altium_parser import AltiumParser
from altium_objects import *

parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")

print("="*80)
print("부모-자식 관계 디버깅")
print("="*80)

# 1. Pin 객체들의 OWNERINDEX 확인
print("\n1. Pin 객체들의 OWNERINDEX 확인:")
pins = [obj for obj in doc.objects if isinstance(obj, Pin)]
print(f"총 Pin: {len(pins)}개")

for i, pin in enumerate(pins[:5], 1):
    print(f"\nPin {i}:")
    print(f"  Index: {pin.index}")
    print(f"  OWNERINDEX: {pin.properties.get('OWNERINDEX', 'NONE')}")
    print(f"  owner_index: {pin.owner_index}")
    print(f"  Designator: {pin.designator}")
    print(f"  Name: {pin.name}")

# 2. Component 객체들의 index 확인
print("\n" + "="*80)
print("2. Component 객체들의 index 확인:")
components = [obj for obj in doc.objects if isinstance(obj, Component)]
print(f"총 Component: {len(components)}개")

for i, comp in enumerate(components[:5], 1):
    print(f"\nComponent {i}:")
    print(f"  Index: {comp.index}")
    print(f"  Library: {comp.library_reference}")
    print(f"  Children count: {len(comp.children)}")

# 3. objects_by_index 맵 확인
print("\n" + "="*80)
print("3. Parser의 objects_by_index 맵 확인:")
print(f"총 매핑된 객체: {len(parser.objects_by_index)}개")
print(f"Index 범위: {min(parser.objects_by_index.keys())} ~ {max(parser.objects_by_index.keys())}")

# Component의 index가 맵에 있는지 확인
print("\nComponent index가 맵에 존재하는지:")
for comp in components[:3]:
    exists = comp.index in parser.objects_by_index
    print(f"  Component index {comp.index}: {exists}")

# 4. 실제 연결 시도 (수동)
print("\n" + "="*80)
print("4. 수동으로 부모-자식 관계 확인:")

# 첫 번째 Component의 children을 찾아보기
if components:
    first_comp = components[0]
    print(f"\n첫 번째 Component (index {first_comp.index})의 자식 찾기:")

    # 이 Component를 owner로 가진 객체들 찾기
    children = []
    for obj in doc.objects:
        owner_idx = obj.properties.get('OWNERINDEX', None)
        if owner_idx and int(owner_idx) == first_comp.index:
            children.append(obj)
            print(f"  - {type(obj).__name__} (index {obj.index})")

    print(f"\n실제 찾은 자식: {len(children)}개")
    print(f"Component.children: {len(first_comp.children)}개")

# 5. OWNERINDEX 분포 확인
print("\n" + "="*80)
print("5. OWNERINDEX 분포 확인:")

owner_indices = {}
for obj in doc.objects:
    owner_idx = obj.properties.get('OWNERINDEX', None)
    if owner_idx:
        owner_idx = int(owner_idx)
        if owner_idx not in owner_indices:
            owner_indices[owner_idx] = []
        owner_indices[owner_idx].append(type(obj).__name__)

print(f"\n고유 OWNERINDEX 값: {len(owner_indices)}개")
print("\n상위 10개 OWNERINDEX와 자식 객체들:")
for owner_idx in sorted(owner_indices.keys())[:10]:
    children = owner_indices[owner_idx]
    print(f"  Index {owner_idx}: {len(children)}개 자식")
    # 타입별 개수
    type_counts = {}
    for t in children:
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, count in sorted(type_counts.items()):
        print(f"    - {t}: {count}")

# 6. Component index와 OWNERINDEX 비교
print("\n" + "="*80)
print("6. Component index와 Pin OWNERINDEX 매칭 확인:")

comp_indices = set(comp.index for comp in components)
pin_owner_indices = set()
for pin in pins:
    owner_idx = pin.properties.get('OWNERINDEX', None)
    if owner_idx:
        pin_owner_indices.add(int(owner_idx))

print(f"Component indices: {sorted(comp_indices)[:10]}")
print(f"Pin OWNERINDEX 값들: {sorted(pin_owner_indices)[:10]}")
print(f"\n매칭되는 index: {comp_indices & pin_owner_indices}")
print(f"매칭 안되는 Component index: {comp_indices - pin_owner_indices}")
print(f"매칭 안되는 Pin OWNERINDEX: {pin_owner_indices - comp_indices}")
