#!/usr/bin/env python3
"""
DI.SchDoc 회로도 분석
LLM이 회로도를 읽고 이해하는 예제
"""

from altium_parser import AltiumParser
from altium_objects import *
from collections import defaultdict

parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")

print("="*80)
print("DI.SchDoc 회로도 분석")
print("="*80)

# ============================================================================
# 1. 전체 개요
# ============================================================================
print("\n" + "="*80)
print("1. 회로도 전체 개요")
print("="*80)

# 객체 타입별 개수
type_counts = defaultdict(int)
for obj in doc.objects:
    type_counts[type(obj).__name__] += 1

print(f"\n총 객체 수: {len(doc.objects)}개")
print("\n객체 타입별 개수:")
for type_name in sorted(type_counts.keys()):
    count = type_counts[type_name]
    print(f"  {type_name:20s}: {count:4d}개")

# ============================================================================
# 2. 부품 분석
# ============================================================================
print("\n" + "="*80)
print("2. 부품(Component) 분석")
print("="*80)

components = [obj for obj in doc.objects if isinstance(obj, Component)]
print(f"\n총 부품 수: {len(components)}개")

# 부품 타입별 분류
component_types = defaultdict(list)
for comp in components:
    lib_ref = comp.library_reference or "Unknown"
    component_types[lib_ref].append(comp)

print("\n부품 타입별:")
for lib_ref in sorted(component_types.keys()):
    comps = component_types[lib_ref]
    print(f"  {lib_ref:30s}: {len(comps)}개")

# 주요 IC 상세 정보
print("\n주요 IC 상세:")
for comp in components[:5]:
    print(f"\n  {comp.library_reference}:")
    print(f"    위치: ({comp.location_x}, {comp.location_y}) mils")
    print(f"    위치: ({comp.location_x * 0.0254:.1f}, {comp.location_y * 0.0254:.1f}) mm")
    print(f"    방향: {comp.orientation.value}°")

    # Designator 찾기 (파라미터에서)
    designator = None
    for child in comp.children:
        if isinstance(child, Parameter):
            if child.name == "Designator":
                designator = child.text
                break
    if designator:
        print(f"    Designator: {designator}")

# ============================================================================
# 3. 배선(Wire) 분석
# ============================================================================
print("\n" + "="*80)
print("3. 배선(Wire) 분석")
print("="*80)

wires = [obj for obj in doc.objects if isinstance(obj, Wire)]
print(f"\n총 배선 수: {len(wires)}개")

# 배선 길이 계산
import math
total_length = 0
for wire in wires:
    for i in range(len(wire.points) - 1):
        x1, y1 = wire.points[i]
        x2, y2 = wire.points[i + 1]
        length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        total_length += length

print(f"총 배선 길이: {total_length:.0f} mils ({total_length * 0.0254:.1f} mm)")
print(f"평균 세그먼트당 배선 수: {len(wires) / len(components):.1f}개/부품")

# 첫 5개 배선 상세
print("\n첫 5개 배선:")
for i, wire in enumerate(wires[:5], 1):
    print(f"\n  배선 {i}:")
    print(f"    점 개수: {len(wire.points)}개")
    print(f"    경로: {' → '.join([f'({x},{y})' for x, y in wire.points])}")

# ============================================================================
# 4. 넷 라벨(NetLabel) 분석
# ============================================================================
print("\n" + "="*80)
print("4. 넷 라벨(NetLabel) 분석 - 신호 이름")
print("="*80)

net_labels = [obj for obj in doc.objects if isinstance(obj, NetLabel)]
print(f"\n총 넷 라벨 수: {len(net_labels)}개")

# 신호 이름별 분류
signal_names = defaultdict(list)
for label in net_labels:
    name = label.text or "(빈 라벨)"
    signal_names[name].append((label.location_x, label.location_y))

print("\n신호 이름별 사용 횟수:")
for name in sorted(signal_names.keys()):
    locations = signal_names[name]
    print(f"  '{name}': {len(locations)}회 사용")
    if len(locations) <= 3:  # 3개 이하면 위치도 표시
        for x, y in locations:
            print(f"    - ({x}, {y})")

# ============================================================================
# 5. 전원 포트(PowerPort) 분석
# ============================================================================
print("\n" + "="*80)
print("5. 전원 포트(PowerPort) 분석")
print("="*80)

power_ports = [obj for obj in doc.objects if isinstance(obj, PowerPort)]
print(f"\n총 전원 포트 수: {len(power_ports)}개")

# 전원별 분류
power_nets = defaultdict(list)
for port in power_ports:
    net = port.text or "Unknown"
    power_nets[net].append((port.location_x, port.location_y))

print("\n전원 네트별:")
for net in sorted(power_nets.keys()):
    locations = power_nets[net]
    print(f"  {net}: {len(locations)}개 연결점")

# ============================================================================
# 6. 접합점(Junction) 분석
# ============================================================================
print("\n" + "="*80)
print("6. 접합점(Junction) 분석")
print("="*80)

junctions = [obj for obj in doc.objects if isinstance(obj, Junction)]
print(f"\n총 접합점 수: {len(junctions)}개")
print("(접합점은 3개 이상의 배선이 만나는 지점)")

# 위치별 접합점 밀도
x_positions = [j.location_x for j in junctions]
y_positions = [j.location_y for j in junctions]
if junctions:
    print(f"\n접합점 분포:")
    print(f"  X 범위: {min(x_positions)} ~ {max(x_positions)} mils")
    print(f"  Y 범위: {min(y_positions)} ~ {max(y_positions)} mils")

# ============================================================================
# 7. 핀(Pin) 분석
# ============================================================================
print("\n" + "="*80)
print("7. 핀(Pin) 분석")
print("="*80)

pins = [obj for obj in doc.objects if isinstance(obj, Pin)]
print(f"\n총 핀 수: {len(pins)}개")

# 핀 타입별 분류 (Electrical type)
pin_types = defaultdict(int)
for pin in pins:
    electrical = pin.electrical.name if pin.electrical else "Unknown"
    pin_types[electrical] += 1

print("\n핀 전기적 타입별:")
for pin_type in sorted(pin_types.keys()):
    count = pin_types[pin_type]
    print(f"  {pin_type:15s}: {count:3d}개")

# ============================================================================
# 8. 회로도 물리적 크기
# ============================================================================
print("\n" + "="*80)
print("8. 회로도 물리적 크기")
print("="*80)

# 모든 객체의 위치 수집
all_x = []
all_y = []

for obj in doc.objects:
    if hasattr(obj, 'location_x') and hasattr(obj, 'location_y'):
        if obj.location_x is not None and obj.location_y is not None:
            all_x.append(obj.location_x)
            all_y.append(obj.location_y)

if all_x and all_y:
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    width_mils = max_x - min_x
    height_mils = max_y - min_y

    width_mm = width_mils * 0.0254
    height_mm = height_mils * 0.0254

    print(f"\n회로도 범위:")
    print(f"  X: {min_x} ~ {max_x} mils (폭: {width_mils} mils = {width_mm:.1f} mm)")
    print(f"  Y: {min_y} ~ {max_y} mils (높이: {height_mils} mils = {height_mm:.1f} mm)")
    print(f"  크기: {width_mm:.1f} × {height_mm:.1f} mm")

# ============================================================================
# 9. 회로 기능 추론
# ============================================================================
print("\n" + "="*80)
print("9. 회로 기능 추론 (LLM 분석)")
print("="*80)

print("\n주요 IC 분석:")

# MCP23017 찾기
mcp_components = [c for c in components if "MCP23017" in (c.library_reference or "")]
if mcp_components:
    print(f"\n✓ MCP23017 발견 ({len(mcp_components)}개)")
    print("  - 16비트 I/O 확장 IC")
    print("  - I2C 인터페이스")
    print("  - GPIO 확장용으로 사용됨")

# TLP281 찾기 (포토커플러)
tlp_components = [c for c in components if "TLP281" in (c.library_reference or "")]
if tlp_components:
    print(f"\n✓ TLP281 발견 ({len(tlp_components)}개)")
    print("  - 4채널 포토커플러")
    print("  - 절연 및 신호 레벨 변환용")
    print("  - 디지털 신호 아이솔레이션")

# 저항 찾기
resistor_components = [c for c in components if "R" in (c.library_reference or "") and "10K" in (c.library_reference or "")]
if resistor_components:
    print(f"\n✓ 10K 저항 발견 ({len(resistor_components)}개)")
    print("  - 풀업/풀다운 또는 전류 제한용")

# 신호 분석
print("\n신호 라인 분석:")
interesting_signals = ["SCL", "SDA", "VCC", "GND"]
for sig in interesting_signals:
    count = sum(1 for label in net_labels if sig.lower() in (label.text or "").lower())
    if count > 0:
        print(f"  - {sig}: {count}개 연결점")

if "SCL" in signal_names and "SDA" in signal_names:
    print("\n✓ I2C 버스 확인 (SCL, SDA)")
    print("  - MCP23017이 I2C 슬레이브로 동작")

print("\n회로 종합 분석:")
print("  이 회로는 I2C 통신을 통해 제어되는 디지털 I/O 확장 시스템입니다.")
print("  MCP23017 IC를 사용하여 16개의 GPIO를 확장하고,")
print("  TLP281 포토커플러를 통해 외부 회로와 절연된 신호 전달을 수행합니다.")
print("  주요 용도: 산업용 제어, 센서 인터페이스, 릴레이 제어 등")

print("\n" + "="*80)
print("분석 완료!")
print("="*80)
