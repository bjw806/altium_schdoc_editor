#!/usr/bin/env python3
"""
파싱되지 못한 요소들 찾기
"""

from altium_parser import AltiumParser
from altium_objects import *
from collections import defaultdict

parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")

print("="*80)
print("파싱 완성도 분석")
print("="*80)

# ============================================================================
# 1. Generic AltiumObject로 파싱된 것들
# ============================================================================
print("\n" + "="*80)
print("1. Generic AltiumObject로 파싱된 객체 (구체적 클래스 미구현)")
print("="*80)

generic_objects = [obj for obj in doc.objects if type(obj).__name__ == 'AltiumObject']
print(f"\n총 {len(generic_objects)}개의 generic 객체")

# RECORD 타입별 분류
record_types = defaultdict(list)
for obj in generic_objects:
    record = obj.properties.get('RECORD', 'Unknown')
    record_types[record].append(obj)

print("\nRECORD 타입별:")
for record in sorted(record_types.keys(), key=lambda x: int(x) if x.isdigit() else 999):
    objs = record_types[record]
    print(f"\n  RECORD={record}: {len(objs)}개")

    # 첫 번째 객체의 주요 속성 보기
    if objs:
        first_obj = objs[0]
        print(f"    주요 속성:")
        important_props = ['NAME', 'TEXT', 'LOCATION.X', 'LOCATION.Y', 'INDEXINSHEET']
        for prop in important_props:
            if prop in first_obj.properties:
                value = first_obj.properties[prop]
                if len(str(value)) > 50:
                    value = str(value)[:50] + "..."
                print(f"      {prop}: {value}")

# ============================================================================
# 2. 부모-자식 관계 확인
# ============================================================================
print("\n" + "="*80)
print("2. 부모-자식 관계 분석")
print("="*80)

components = [obj for obj in doc.objects if isinstance(obj, Component)]
pins = [obj for obj in doc.objects if isinstance(obj, Pin)]
parameters = [obj for obj in doc.objects if isinstance(obj, Parameter)]

print(f"\nComponent: {len(components)}개")
print(f"Pin: {len(pins)}개")
print(f"Parameter: {len(parameters)}개")

# Component children 확인
total_children = sum(len(comp.children) for comp in components)
print(f"\nComponent의 총 자식 수: {total_children}개")

if total_children == 0:
    print("⚠️  경고: Component에 자식이 하나도 없습니다!")
    print("   Pin과 Parameter가 Component에 연결되어야 합니다.")

# 첫 Component 상세 분석
if components:
    first_comp = components[0]
    print(f"\n첫 번째 Component 상세:")
    print(f"  library_reference: {first_comp.library_reference}")
    print(f"  index: {first_comp.index}")
    print(f"  children: {len(first_comp.children)}개")

    # 이 Component를 owner로 가져야 하는 객체들 찾기
    expected_children = []
    for obj in doc.objects:
        owner_idx = obj.properties.get('OWNERINDEX')
        if owner_idx and int(owner_idx) == first_comp.index:
            expected_children.append(obj)

    print(f"  기대되는 자식 (OWNERINDEX={first_comp.index}): {len(expected_children)}개")

    if len(expected_children) > 0 and len(first_comp.children) == 0:
        print(f"\n  ⚠️  인덱스 불일치 문제 발견!")
        print(f"     Component index: {first_comp.index}")
        print(f"     OWNERINDEX를 가진 객체들:")
        for child in expected_children[:5]:
            print(f"       - {type(child).__name__} OWNERINDEX={child.properties.get('OWNERINDEX')}")

# ============================================================================
# 3. Designator 접근성
# ============================================================================
print("\n" + "="*80)
print("3. Designator 접근성 분석")
print("="*80)

components_with_designator = 0
designators_found = []

for comp in components:
    # Component 객체에 직접 designator 속성이 있는지
    has_direct_designator = hasattr(comp, 'designator') and comp.designator

    # children에서 Designator Parameter 찾기
    designator_from_children = None
    for child in comp.children:
        if isinstance(child, Parameter) and child.name == "Designator":
            designator_from_children = child.text
            break

    # properties에서 직접 찾기
    designator_from_props = comp.properties.get('DESIGNATOR')

    if has_direct_designator or designator_from_children or designator_from_props:
        components_with_designator += 1
        designators_found.append({
            'lib': comp.library_reference,
            'direct': has_direct_designator,
            'from_children': designator_from_children,
            'from_props': designator_from_props
        })

print(f"\nDesignator를 가진 Component: {components_with_designator}/{len(components)}개")

if designators_found:
    print("\n처음 5개 Component의 Designator 접근 방법:")
    for i, info in enumerate(designators_found[:5], 1):
        print(f"\n  {i}. {info['lib']}")
        print(f"     직접 속성: {info['direct']}")
        print(f"     children에서: {info['from_children']}")
        print(f"     properties에서: {info['from_props']}")
else:
    print("\n⚠️  Designator를 찾을 수 없습니다!")

# ============================================================================
# 4. 미구현 RECORD 타입 분석
# ============================================================================
print("\n" + "="*80)
print("4. 미구현 RECORD 타입 상세 분석")
print("="*80)

# RECORD 타입별 의미 추정
record_info = {
    '18': 'PORT (포트)',
    '22': 'NO_ERC (ERC 무시 마커)',
    '34': 'DESIGNATOR (Designator 텍스트)',
    '46': 'Unknown Type 46',
    '48': 'Unknown Type 48',
    '215': 'Sheet Entry (계층 심볼 연결점)',
    '216': 'Sheet Entry Port (계층 포트)',
    '217': 'Sheet Entry Label (계층 라벨)',
    '218': 'Sheet Entry Line (계층 라인)',
}

print("\n미구현 타입별 상세:")
for record, description in sorted(record_info.items(), key=lambda x: int(x[0])):
    if record in record_types:
        objs = record_types[record]
        print(f"\nRECORD={record}: {description}")
        print(f"  개수: {len(objs)}개")

        # 샘플 객체
        if objs:
            sample = objs[0]
            print(f"  샘플 속성:")
            for key, value in sorted(sample.properties.items())[:8]:
                if len(str(value)) > 40:
                    value = str(value)[:40] + "..."
                print(f"    {key}: {value}")

# ============================================================================
# 5. 누락된 기능 요약
# ============================================================================
print("\n" + "="*80)
print("5. 개선 필요 사항 요약")
print("="*80)

issues = []

if total_children == 0:
    issues.append({
        'priority': 'HIGH',
        'issue': '부모-자식 관계 미연결',
        'detail': f'Component {len(components)}개에 자식이 0개. Pin/Parameter 연결 안됨',
        'fix': 'Index 계산 방식 수정 (off-by-one 문제)'
    })

if len(generic_objects) > 0:
    issues.append({
        'priority': 'MEDIUM',
        'issue': f'{len(generic_objects)}개 객체가 Generic으로 파싱됨',
        'detail': f'RECORD 타입: {", ".join(sorted(set(record_types.keys())))}',
        'fix': '각 RECORD 타입에 대한 전용 클래스 구현'
    })

if components_with_designator < len(components):
    issues.append({
        'priority': 'LOW',
        'issue': f'Designator 직접 접근 불가',
        'detail': f'{len(components) - components_with_designator}개 Component에 designator 속성 없음',
        'fix': 'Component._parse 시 Designator를 직접 속성으로 추출'
    })

print(f"\n총 {len(issues)}개 개선 필요 항목:\n")

for i, issue in enumerate(issues, 1):
    print(f"{i}. [{issue['priority']}] {issue['issue']}")
    print(f"   문제: {issue['detail']}")
    print(f"   해결: {issue['fix']}")
    print()

print("="*80)
print("분석 완료!")
print("="*80)
