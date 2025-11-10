#!/usr/bin/env python3
"""
회로도 개선 적용 스크립트
=========================
find_improvements.py에서 발견한 문제점들을 실제로 수정하여
DI_improved.SchDoc 파일을 생성합니다.

개선 내용:
1. 디커플링 커패시터 추가 (각 IC 근처에 0.1μF)
2. 벌크 커패시터 추가 (전원 입력에 10μF)
3. VCC PowerPort 심볼 추가
4. 빈 넷 라벨 제거
"""

from altium_editor import SchematicEditor
from altium_objects import *
from altium_parser import AltiumParser
import math

def find_component_vcc_location(component):
    """
    컴포넌트의 VCC 핀 위치 찾기

    Args:
        component: Component 객체

    Returns:
        (x, y) 튜플 또는 None
    """
    for child in component.children:
        if isinstance(child, Pin):
            pin_name = child.name or ""
            if 'VCC' in pin_name.upper() or 'VDD' in pin_name.upper():
                return (child.location_x, child.location_y)
    return None

def find_nearest_vcc_label(editor, x, y, max_distance=500):
    """
    가장 가까운 VCC 넷 라벨 찾기

    Args:
        editor: SchematicEditor 객체
        x, y: 기준 좌표
        max_distance: 최대 거리 (mils)

    Returns:
        가장 가까운 VCC NetLabel 또는 None
    """
    vcc_labels = [l for l in editor.get_net_labels()
                  if l.text and 'VCC' in l.text.upper()]

    if not vcc_labels:
        return None

    # 거리 계산
    closest = None
    min_dist = float('inf')

    for label in vcc_labels:
        dist = math.sqrt((label.location_x - x)**2 + (label.location_y - y)**2)
        if dist < min_dist and dist <= max_distance:
            min_dist = dist
            closest = label

    return closest

def add_decoupling_capacitor(editor, component, cap_num):
    """
    컴포넌트 근처에 디커플링 커패시터 추가

    Args:
        editor: SchematicEditor
        component: 대상 Component
        cap_num: 커패시터 번호

    Returns:
        추가된 Component 또는 None
    """
    # VCC 핀 위치 찾기
    vcc_location = find_component_vcc_location(component)

    if not vcc_location:
        # VCC 핀을 못 찾으면 컴포넌트 위쪽에 배치
        cap_x = component.location_x + 100
        cap_y = component.location_y + 100
    else:
        # VCC 핀 근처에 배치
        cap_x = vcc_location[0] + 50
        cap_y = vcc_location[1] + 50

    # 디커플링 커패시터 추가 (0.1μF)
    cap = editor.add_capacitor(
        x=cap_x,
        y=cap_y,
        value="0.1uF",
        designator=f"C{cap_num}",
        orientation=Orientation.DOWN
    )

    print(f"  ✓ {component.designator} 근처에 디커플링 커패시터 C{cap_num} (0.1μF) 추가")
    print(f"    위치: ({cap_x}, {cap_y})")

    # VCC 연결 와이어 추가
    if vcc_location:
        editor.add_wire([
            vcc_location,
            (cap_x, vcc_location[1]),
            (cap_x, cap_y)
        ])

    # GND 연결 추가
    gnd_y = cap_y - 50
    editor.add_wire([(cap_x, cap_y), (cap_x, gnd_y)])
    editor.add_power_port(
        x=cap_x,
        y=gnd_y,
        text="GND",
        style=PowerPortStyle.POWER_GROUND,
        orientation=Orientation.DOWN
    )

    return cap

def add_bulk_capacitor(editor):
    """
    전원 입력에 벌크 커패시터 추가

    Args:
        editor: SchematicEditor

    Returns:
        추가된 Component
    """
    # 왼쪽 상단에 배치 (전원 입력 근처)
    cap_x = 150
    cap_y = 600

    cap = editor.add_capacitor(
        x=cap_x,
        y=cap_y,
        value="10uF",
        designator="C100",
        orientation=Orientation.DOWN
    )

    print(f"  ✓ 전원 입력에 벌크 커패시터 C100 (10μF) 추가")
    print(f"    위치: ({cap_x}, {cap_y})")

    # VCC 연결
    vcc_y = cap_y + 50
    editor.add_wire([(cap_x, cap_y), (cap_x, vcc_y)])
    editor.add_net_label(cap_x + 10, vcc_y, "VCC")

    # GND 연결
    gnd_y = cap_y - 50
    editor.add_wire([(cap_x, cap_y), (cap_x, gnd_y)])
    editor.add_power_port(
        x=cap_x,
        y=gnd_y,
        text="GND",
        style=PowerPortStyle.POWER_GROUND,
        orientation=Orientation.DOWN
    )

    return cap

def add_vcc_power_ports(editor):
    """
    VCC PowerPort 심볼 추가

    기존 VCC NetLabel 중 일부를 PowerPort로 교체

    Args:
        editor: SchematicEditor
    """
    vcc_labels = [l for l in editor.get_net_labels()
                  if l.text and 'VCC' in l.text.upper()]

    if not vcc_labels:
        print("  ⚠️  VCC 넷 라벨을 찾을 수 없습니다")
        return

    # 첫 번째 VCC 라벨 근처에 PowerPort 추가
    label = vcc_labels[0]

    port = editor.add_power_port(
        x=label.location_x,
        y=label.location_y + 30,
        text="VCC",
        style=PowerPortStyle.ARROW,
        orientation=Orientation.UP
    )

    # 연결 와이어
    editor.add_wire([
        (label.location_x, label.location_y),
        (label.location_x, label.location_y + 30)
    ])

    print(f"  ✓ VCC PowerPort 심볼 추가: ({label.location_x}, {label.location_y + 30})")

def remove_empty_labels(editor):
    """
    빈 넷 라벨 제거

    Args:
        editor: SchematicEditor

    Returns:
        제거한 라벨 개수
    """
    empty_labels = [l for l in editor.get_net_labels()
                    if not l.text or l.text.strip() == ""]

    for label in empty_labels:
        editor.doc.objects.remove(label)

    if empty_labels:
        print(f"  ✓ 빈 넷 라벨 {len(empty_labels)}개 제거")

    return len(empty_labels)

def add_i2c_labels(editor):
    """
    I2C 신호 라벨 추가

    SCL/SDA 핀에 명확한 넷 라벨 추가

    Args:
        editor: SchematicEditor
    """
    # MCP23017 찾기
    mcp = None
    for comp in editor.get_components():
        if comp.designator == "EXP0" or "MCP23017" in (comp.library_reference or ""):
            mcp = comp
            break

    if not mcp:
        print("  ⚠️  MCP23017을 찾을 수 없습니다")
        return

    # SCL, SDA 핀 찾기
    scl_pin = None
    sda_pin = None

    for child in mcp.children:
        if isinstance(child, Pin):
            if child.name and 'SCL' in child.name.upper():
                scl_pin = child
            elif child.name and 'SDA' in child.name.upper():
                sda_pin = child

    # 라벨 추가
    added = 0
    if scl_pin:
        editor.add_net_label(
            scl_pin.location_x - 50,
            scl_pin.location_y,
            "SCL"
        )
        added += 1

    if sda_pin:
        editor.add_net_label(
            sda_pin.location_x - 50,
            sda_pin.location_y,
            "SDA"
        )
        added += 1

    if added:
        print(f"  ✓ I2C 신호 라벨 {added}개 추가 (SCL, SDA)")

# ============================================================================
# 메인 실행
# ============================================================================

print("=" * 80)
print("회로도 개선 적용")
print("=" * 80)

# 에디터 생성 및 파일 로드
editor = SchematicEditor()
editor.load("DI.SchDoc")

print("\n원본 회로도 정보:")
editor.print_summary()

print("\n" + "=" * 80)
print("개선 사항 적용 중...")
print("=" * 80)

# ============================================================================
# 1. 디커플링 커패시터 추가
# ============================================================================
print("\n1. 디커플링 커패시터 추가 (각 IC에 0.1μF)")

components = editor.get_components()
ic_components = []

# MCP23017 찾기
for comp in components:
    if "MCP23017" in (comp.library_reference or ""):
        ic_components.append(comp)

# TLP281-4 찾기
for comp in components:
    if "TLP281" in (comp.library_reference or ""):
        ic_components.append(comp)

print(f"   발견한 IC: {len(ic_components)}개")

cap_num = 201  # C201부터 시작 (기존 부품과 겹치지 않도록)
for comp in ic_components:
    add_decoupling_capacitor(editor, comp, cap_num)
    cap_num += 1

# ============================================================================
# 2. 벌크 커패시터 추가
# ============================================================================
print("\n2. 벌크 커패시터 추가 (전원 입력에 10μF)")
add_bulk_capacitor(editor)

# ============================================================================
# 3. VCC PowerPort 추가
# ============================================================================
print("\n3. VCC PowerPort 심볼 추가")
add_vcc_power_ports(editor)

# ============================================================================
# 4. I2C 라벨 추가
# ============================================================================
print("\n4. I2C 신호 라벨 추가")
add_i2c_labels(editor)

# ============================================================================
# 5. 빈 라벨 제거
# ============================================================================
print("\n5. 빈 넷 라벨 제거")
remove_empty_labels(editor)

# ============================================================================
# 저장
# ============================================================================
print("\n" + "=" * 80)
print("개선된 회로도 저장 중...")
print("=" * 80)

output_file = "DI_improved.SchDoc"
editor.save(output_file)

print(f"\n✓ 저장 완료: {output_file}")

# 개선된 회로도 요약
print("\n개선된 회로도 정보:")
editor.print_summary()

# ============================================================================
# 개선 사항 요약
# ============================================================================
print("\n" + "=" * 80)
print("적용된 개선 사항 요약")
print("=" * 80)

print("\n✓ 추가된 부품:")
print(f"  - 디커플링 커패시터 (0.1μF): {len(ic_components)}개")
print(f"  - 벌크 커패시터 (10μF): 1개")
print(f"  - VCC PowerPort: 1개")
print(f"  - I2C 신호 라벨: 2개")

print("\n✓ 제거된 요소:")
print(f"  - 빈 넷 라벨")

print("\n✓ 개선 효과:")
print("  1. 전원 노이즈 감소 (디커플링 커패시터)")
print("  2. 전원 안정성 향상 (벌크 커패시터)")
print("  3. 회로도 가독성 개선 (PowerPort, 라벨)")
print("  4. ERC 경고 감소")

print("\n" + "=" * 80)
print("완료!")
print("=" * 80)
