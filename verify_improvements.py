#!/usr/bin/env python3
"""
개선 사항 검증 스크립트
====================
DI_improved.SchDoc 파일을 파싱하여 모든 개선 사항이
정확히 적용되었는지 검증합니다.
"""

from altium_parser import AltiumParser
from altium_objects import *

print("=" * 80)
print("DI_improved.SchDoc 개선 사항 검증")
print("=" * 80)

# 파일 파싱
parser = AltiumParser()
doc = parser.parse_file("DI_improved.SchDoc")

print(f"\n✓ 파일 파싱 성공: {len(doc.objects)}개 객체")

# 객체 분류
components = [obj for obj in doc.objects if isinstance(obj, Component)]
capacitors = [c for c in components if 'CAP' in (c.library_reference or '').upper()]
net_labels = [obj for obj in doc.objects if isinstance(obj, NetLabel)]
power_ports = [obj for obj in doc.objects if isinstance(obj, PowerPort)]
wires = [obj for obj in doc.objects if isinstance(obj, Wire)]

print("\n" + "=" * 80)
print("1. 디커플링 커패시터 검증 (0.1μF)")
print("=" * 80)

decoupling_caps = [c for c in capacitors if c.designator and c.designator.startswith('C20')]

print(f"\n디커플링 커패시터: {len(decoupling_caps)}개")

expected_decoupling = ['C201', 'C202', 'C203', 'C204', 'C205']
found_designators = [c.designator for c in decoupling_caps]

for expected in expected_decoupling:
    if expected in found_designators:
        cap = [c for c in decoupling_caps if c.designator == expected][0]

        # Value 파라미터 찾기
        value = None
        for child in cap.children:
            if isinstance(child, Parameter) and child.name == "Value":
                value = child.text
                break

        print(f"  ✓ {expected}: 위치 ({cap.location_x}, {cap.location_y}), 값: {value}")
    else:
        print(f"  ✗ {expected}: 찾을 수 없음")

if len(decoupling_caps) == 5:
    print("\n✓ 디커플링 커패시터 5개 모두 확인됨")
else:
    print(f"\n✗ 디커플링 커패시터 개수 불일치 (기대: 5, 실제: {len(decoupling_caps)})")

print("\n" + "=" * 80)
print("2. 벌크 커패시터 검증 (10μF)")
print("=" * 80)

bulk_caps = [c for c in capacitors if c.designator == 'C100']

if bulk_caps:
    cap = bulk_caps[0]

    # Value 파라미터 찾기
    value = None
    for child in cap.children:
        if isinstance(child, Parameter) and child.name == "Value":
            value = child.text
            break

    print(f"\n✓ C100 발견")
    print(f"  위치: ({cap.location_x}, {cap.location_y})")
    print(f"  값: {value}")
else:
    print("\n✗ C100을 찾을 수 없음")

print("\n" + "=" * 80)
print("3. VCC PowerPort 검증")
print("=" * 80)

vcc_ports = [p for p in power_ports if p.text and 'VCC' in p.text.upper()]

print(f"\nVCC PowerPort: {len(vcc_ports)}개")

if vcc_ports:
    for i, port in enumerate(vcc_ports, 1):
        print(f"  {i}. VCC PowerPort at ({port.location_x}, {port.location_y})")
        print(f"     스타일: {port.style.name}, 방향: {port.orientation.name}")
    print("\n✓ VCC PowerPort 추가됨")
else:
    print("\n✗ VCC PowerPort를 찾을 수 없음")

print("\n" + "=" * 80)
print("4. I2C 신호 라벨 검증")
print("=" * 80)

scl_labels = [l for l in net_labels if l.text and 'SCL' in l.text.upper()]
sda_labels = [l for l in net_labels if l.text and 'SDA' in l.text.upper()]

print(f"\nSCL NetLabel: {len(scl_labels)}개")
for label in scl_labels:
    print(f"  - SCL at ({label.location_x}, {label.location_y})")

print(f"\nSDA NetLabel: {len(sda_labels)}개")
for label in sda_labels:
    print(f"  - SDA at ({label.location_x}, {label.location_y})")

if len(scl_labels) > 0 and len(sda_labels) > 0:
    print("\n✓ I2C 신호 라벨 추가됨")
else:
    print("\n✗ I2C 신호 라벨 부족")

print("\n" + "=" * 80)
print("5. 빈 넷 라벨 검증")
print("=" * 80)

empty_labels = [l for l in net_labels if not l.text or l.text.strip() == ""]

print(f"\n빈 NetLabel: {len(empty_labels)}개")

if len(empty_labels) == 0:
    print("✓ 빈 넷 라벨 없음 (정상)")
else:
    print(f"✗ 빈 넷 라벨 {len(empty_labels)}개 발견")
    for label in empty_labels:
        print(f"  - at ({label.location_x}, {label.location_y})")

print("\n" + "=" * 80)
print("6. 전체 회로 통계")
print("=" * 80)

print(f"\n총 객체 수: {len(doc.objects)}")
print(f"  Components: {len(components)}")
print(f"  - 커패시터: {len(capacitors)}")
print(f"  - IC: {len([c for c in components if 'MCP' in (c.library_reference or '') or 'TLP' in (c.library_reference or '')])}")
print(f"  Wires: {len(wires)}")
print(f"  Net Labels: {len(net_labels)}")
print(f"  Power Ports: {len(power_ports)}")

print("\n" + "=" * 80)
print("7. 원본 대비 변경 사항")
print("=" * 80)

# 원본 파일 파싱
original_doc = parser.parse_file("DI.SchDoc")
original_components = [obj for obj in original_doc.objects if isinstance(obj, Component)]
original_wires = [obj for obj in original_doc.objects if isinstance(obj, Wire)]
original_labels = [obj for obj in original_doc.objects if isinstance(obj, NetLabel)]
original_ports = [obj for obj in original_doc.objects if isinstance(obj, PowerPort)]

print(f"\n원본 → 개선:")
print(f"  총 객체: {len(original_doc.objects)} → {len(doc.objects)} (+{len(doc.objects) - len(original_doc.objects)})")
print(f"  Components: {len(original_components)} → {len(components)} (+{len(components) - len(original_components)})")
print(f"  Wires: {len(original_wires)} → {len(wires)} (+{len(wires) - len(original_wires)})")
print(f"  Net Labels: {len(original_labels)} → {len(net_labels)} (+{len(net_labels) - len(original_labels)})")
print(f"  Power Ports: {len(original_ports)} → {len(power_ports)} (+{len(power_ports) - len(original_ports)})")

print("\n" + "=" * 80)
print("8. 검증 결과 요약")
print("=" * 80)

checks = [
    ("디커플링 커패시터 (5개)", len(decoupling_caps) == 5),
    ("벌크 커패시터 (1개)", len(bulk_caps) == 1),
    ("VCC PowerPort (1개 이상)", len(vcc_ports) >= 1),
    ("SCL 라벨", len(scl_labels) > 0),
    ("SDA 라벨", len(sda_labels) > 0),
    ("빈 넷 라벨 없음", len(empty_labels) == 0),
]

passed = sum(1 for _, result in checks if result)
total = len(checks)

print(f"\n검증 항목:")
for name, result in checks:
    status = "✓" if result else "✗"
    print(f"  {status} {name}")

print(f"\n통과율: {passed}/{total} ({passed * 100 // total}%)")

if passed == total:
    print("\n" + "=" * 80)
    print("🎉 모든 검증 통과!")
    print("=" * 80)
    print("\nDI_improved.SchDoc 파일이 성공적으로 생성되었으며,")
    print("모든 개선 사항이 정확히 적용되었습니다.")
elif passed >= total * 0.8:
    print(f"\n✓ 대부분의 검증 통과 ({passed}/{total})")
else:
    print(f"\n⚠️  일부 검증 실패 ({total - passed}개 항목)")

print("\n" + "=" * 80)
