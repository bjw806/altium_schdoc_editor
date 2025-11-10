#!/usr/bin/env python3
"""
DI.SchDoc 회로도 개선점 찾기
설계 품질 분석 및 문제점 검출
"""

from altium_parser import AltiumParser
from altium_objects import *
from collections import defaultdict
import math

parser = AltiumParser()
doc = parser.parse_file("DI.SchDoc")

print("="*80)
print("DI.SchDoc 회로도 개선점 분석")
print("="*80)

# 객체 분류
components = [obj for obj in doc.objects if isinstance(obj, Component)]
wires = [obj for obj in doc.objects if isinstance(obj, Wire)]
net_labels = [obj for obj in doc.objects if isinstance(obj, NetLabel)]
power_ports = [obj for obj in doc.objects if isinstance(obj, PowerPort)]
pins = [obj for obj in doc.objects if isinstance(obj, Pin)]
parameters = [obj for obj in doc.objects if isinstance(obj, Parameter)]

issues = []
warnings = []
suggestions = []

# ============================================================================
# 1. 전원 디커플링 캐패시터 확인
# ============================================================================
print("\n" + "="*80)
print("1. 전원 디커플링 캐패시터 검사")
print("="*80)

# 캐패시터 찾기
capacitors = [c for c in components if 'CAP' in (c.library_reference or '').upper()
              or 'C' == (c.library_reference or '').strip()[0:1]]

# IC 찾기
ics = [c for c in components if 'MCP' in (c.library_reference or '')
       or 'TLP' in (c.library_reference or '')]

print(f"\n발견된 IC: {len(ics)}개")
for ic in ics:
    print(f"  - {ic.library_reference}")

print(f"\n발견된 캐패시터: {len(capacitors)}개")

if len(capacitors) == 0:
    issues.append("❌ CRITICAL: 전원 디커플링 캐패시터가 없습니다!")
    print("\n⚠️  문제: 디커플링 캐패시터가 발견되지 않음")
    print("   권장사항:")
    print("   - MCP23017 VDD 핀 근처에 0.1μF 세라믹 캐패시터 추가")
    print("   - 각 TLP281 VCC 핀 근처에 0.1μF 세라믹 캐패시터 추가")
    print("   - 전원 입력단에 10μF 전해 캐패시터 추가")
elif len(capacitors) < len(ics):
    warnings.append(f"⚠️  디커플링 캐패시터 부족: {len(capacitors)}개 (IC {len(ics)}개)")
    print(f"\n⚠️  경고: IC는 {len(ics)}개인데 캐패시터는 {len(capacitors)}개만 있음")
else:
    print(f"\n✓ 디커플링 캐패시터 충분: {len(capacitors)}개")

# ============================================================================
# 2. I2C 풀업 저항 확인
# ============================================================================
print("\n" + "="*80)
print("2. I2C 풀업 저항 검사")
print("="*80)

# SCL/SDA 신호 찾기
scl_labels = [l for l in net_labels if 'SCL' in (l.text or '').upper()]
sda_labels = [l for l in net_labels if 'SDA' in (l.text or '').upper()]

print(f"\nSCL 라벨: {len(scl_labels)}개")
print(f"SDA 라벨: {len(sda_labels)}개")

# 풀업 저항 찾기 (I2C 검사 전에 먼저)
resistors = [c for c in components if 'RES' in (c.library_reference or '').upper()
             or c.library_reference in ['10KR2F', 'R']]

if scl_labels or sda_labels:
    # I2C 버스 존재
    print("\n✓ I2C 버스 확인됨 (SCL/SDA)")
    print(f"\n저항 발견: {len(resistors)}개")

    # I2C 풀업은 보통 4.7K~10K
    # 정확한 값은 Parameter에서 확인 필요
    if len(resistors) < 2:
        issues.append("❌ CRITICAL: I2C 풀업 저항 부족 (최소 2개 필요: SCL, SDA)")
        print("\n⚠️  문제: I2C 풀업 저항이 부족합니다")
        print("   권장사항:")
        print("   - SCL 라인에 4.7kΩ 풀업 저항 추가 (to VCC)")
        print("   - SDA 라인에 4.7kΩ 풀업 저항 추가 (to VCC)")
    else:
        suggestions.append("💡 I2C 풀업 저항값 확인 필요 (권장: 4.7kΩ)")
        print("\n✓ 풀업 저항 존재 (값 확인 필요)")
else:
    print("\n⚠️  I2C 버스 라벨(SCL/SDA)이 없습니다")
    warnings.append("⚠️  I2C 버스 신호 라벨 누락")
    print(f"\n저항 발견: {len(resistors)}개")

# ============================================================================
# 3. 전원 연결 확인
# ============================================================================
print("\n" + "="*80)
print("3. 전원 연결 검사")
print("="*80)

# 전원 넷 분석
power_nets = defaultdict(list)
for port in power_ports:
    net = port.text or "Unknown"
    power_nets[net].append(port)

print(f"\n전원 네트:")
for net, ports in sorted(power_nets.items()):
    print(f"  {net}: {len(ports)}개 연결")

# VCC 확인
vcc_ports = [p for p in power_ports if 'VCC' in (p.text or '').upper()
             or 'VDD' in (p.text or '').upper()]
gnd_ports = [p for p in power_ports if 'GND' in (p.text or '').upper()]

if len(vcc_ports) == 0:
    issues.append("❌ CRITICAL: VCC 전원 포트가 없습니다!")
    print("\n⚠️  문제: VCC 전원 연결이 명시적이지 않음")
else:
    print(f"\n✓ VCC 연결: {len(vcc_ports)}개")

if len(gnd_ports) < 3:
    warnings.append(f"⚠️  GND 연결 부족: {len(gnd_ports)}개 (더 많이 필요)")
    print(f"\n⚠️  경고: GND 포트가 {len(gnd_ports)}개로 부족할 수 있음")
    print("   권장사항: 각 IC와 디커플링 캐패시터마다 GND 연결 명시")
else:
    print(f"\n✓ GND 연결: {len(gnd_ports)}개")

# ============================================================================
# 4. 미사용 핀 확인
# ============================================================================
print("\n" + "="*80)
print("4. 미사용 핀 검사")
print("="*80)

# MCP23017의 미사용 핀 확인
mcp_components = [c for c in components if "MCP23017" in (c.library_reference or "")]

if mcp_components:
    mcp = mcp_components[0]
    print(f"\nMCP23017 분석:")
    print(f"  위치: ({mcp.location_x}, {mcp.location_y})")

    # MCP23017은 28핀 IC
    # A0, A1, A2 (주소 핀), RESET 핀 등 확인 필요
    suggestions.append("💡 MCP23017 주소 핀(A0,A1,A2) 연결 상태 확인 필요")
    suggestions.append("💡 MCP23017 RESET 핀 풀업 확인 필요")
    print("\n  확인 필요:")
    print("  - A0, A1, A2 주소 핀: GND 또는 VCC에 연결되어야 함")
    print("  - RESET 핀: VCC에 풀업 저항으로 연결 권장")
    print("  - 미사용 GPIO 핀: 플로팅 상태로 두어도 무방")

# ============================================================================
# 5. 신호 라우팅 품질
# ============================================================================
print("\n" + "="*80)
print("5. 신호 라우팅 품질 검사")
print("="*80)

# 디지털 입력 신호 (DI0~DI15) 확인
di_signals = [l for l in net_labels if l.text and l.text.startswith('DI')]
print(f"\n디지털 입력 신호: {len(di_signals)}개")

# 신호별 그룹화
di_by_name = defaultdict(list)
for label in di_signals:
    di_by_name[label.text].append(label)

print("\n신호별 사용:")
for name in sorted(di_by_name.keys()):
    labels = di_by_name[name]
    if len(labels) < 2:
        warnings.append(f"⚠️  {name} 신호가 1곳에만 사용됨")
        print(f"  ⚠️  {name}: {len(labels)}개 (연결 확인 필요)")
    elif len(labels) > 3:
        warnings.append(f"⚠️  {name} 신호가 {len(labels)}곳에 사용됨 (많음)")
        print(f"  ⚠️  {name}: {len(labels)}개 (너무 많음, 확인 필요)")
    else:
        print(f"  ✓ {name}: {len(labels)}개")

# ============================================================================
# 6. 배선 품질 - 크로스오버 확인
# ============================================================================
print("\n" + "="*80)
print("6. 배선 품질 검사")
print("="*80)

# 배선 길이 분석
wire_lengths = []
for wire in wires:
    length = 0
    for i in range(len(wire.points) - 1):
        x1, y1 = wire.points[i]
        x2, y2 = wire.points[i + 1]
        length += math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    wire_lengths.append(length)

if wire_lengths:
    avg_length = sum(wire_lengths) / len(wire_lengths)
    max_length = max(wire_lengths)

    print(f"\n배선 통계:")
    print(f"  총 배선 수: {len(wires)}개")
    print(f"  평균 길이: {avg_length:.1f} mils ({avg_length * 0.0254:.1f} mm)")
    print(f"  최대 길이: {max_length:.1f} mils ({max_length * 0.0254:.1f} mm)")

    # 너무 긴 배선 경고
    long_wires = [w for w, l in zip(wires, wire_lengths) if l > 500]
    if long_wires:
        warnings.append(f"⚠️  긴 배선 {len(long_wires)}개 발견 (500 mils 이상)")
        print(f"\n  ⚠️  매우 긴 배선: {len(long_wires)}개")
        print("     권장: 배선 경로 최적화 고려")

# ============================================================================
# 7. 라벨링 및 문서화
# ============================================================================
print("\n" + "="*80)
print("7. 라벨링 및 문서화 검사")
print("="*80)

# 빈 라벨 확인
empty_labels = [l for l in net_labels if not l.text or l.text.strip() == '']
if empty_labels:
    warnings.append(f"⚠️  빈 넷 라벨 {len(empty_labels)}개 발견")
    print(f"\n⚠️  빈 라벨: {len(empty_labels)}개")
    print("   권장: 모든 신호에 의미있는 이름 부여")
else:
    print("\n✓ 모든 라벨이 명명됨")

# Component Designator 확인
components_with_designator = 0
for comp in components:
    has_designator = False
    for child in comp.children:
        if isinstance(child, Parameter) and child.name == "Designator":
            if child.text and child.text.strip():
                has_designator = True
                break
    if has_designator:
        components_with_designator += 1

print(f"\nDesignator 할당:")
print(f"  {components_with_designator}/{len(components)} 부품에 Designator 있음")

if components_with_designator < len(components):
    issues.append(f"❌ {len(components) - components_with_designator}개 부품에 Designator 없음")
    print("  ⚠️  일부 부품에 Designator가 없습니다")

# ============================================================================
# 8. 포토커플러 회로 확인
# ============================================================================
print("\n" + "="*80)
print("8. 포토커플러 회로 검사")
print("="*80)

tlp_components = [c for c in components if "TLP281" in (c.library_reference or "")]
print(f"\nTLP281 포토커플러: {len(tlp_components)}개")

if tlp_components:
    print("\n확인 필요:")
    print("  - 각 LED 입력에 전류 제한 저항 (보통 330Ω~1kΩ)")
    print("  - 출력측 풀업 저항 (보통 10kΩ)")
    print("  - 입력/출력 전원 분리 확인")

    # 저항 개수로 대략 확인
    if len(resistors) < len(tlp_components) * 2:
        warnings.append(f"⚠️  포토커플러 {len(tlp_components)}개에 비해 저항 부족")
        print(f"\n  ⚠️  포토커플러당 최소 2개 저항 필요 (입력 제한 + 출력 풀업)")
        print(f"     현재 저항: {len(resistors)}개, 필요: 약 {len(tlp_components) * 2}개")

# ============================================================================
# 9. 종합 평가
# ============================================================================
print("\n" + "="*80)
print("9. 종합 평가 및 개선 권장사항")
print("="*80)

print(f"\n검출된 문제:")
print(f"  심각: {len(issues)}개")
print(f"  경고: {len(warnings)}개")
print(f"  제안: {len(suggestions)}개")

if issues:
    print("\n" + "="*60)
    print("❌ 심각한 문제 (즉시 수정 필요):")
    print("="*60)
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")

if warnings:
    print("\n" + "="*60)
    print("⚠️  경고 (검토 필요):")
    print("="*60)
    for i, warning in enumerate(warnings, 1):
        print(f"{i}. {warning}")

if suggestions:
    print("\n" + "="*60)
    print("💡 개선 제안:")
    print("="*60)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")

# ============================================================================
# 10. 우선순위별 액션 아이템
# ============================================================================
print("\n" + "="*80)
print("10. 우선순위별 개선 액션 아이템")
print("="*80)

print("\n🔴 높음 (즉시 수정):")
print("  1. 각 IC(MCP23017, TLP281)에 0.1μF 디커플링 캐패시터 추가")
print("  2. I2C 라인(SCL, SDA)에 4.7kΩ 풀업 저항 추가")
print("  3. 전원 입력단에 10μF 대용량 캐패시터 추가")

print("\n🟡 중간 (검토 및 개선):")
print("  4. MCP23017 주소 핀(A0, A1, A2) 연결 확인")
print("  5. MCP23017 RESET 핀에 10kΩ 풀업 저항 추가")
print("  6. 각 포토커플러 LED 입력에 전류 제한 저항 확인")
print("  7. 빈 넷 라벨 제거 또는 명명")

print("\n🟢 낮음 (최적화):")
print("  8. 긴 배선 경로 최적화")
print("  9. 모든 부품에 Designator 할당")
print("  10. 회로도에 설명 텍스트 추가 (동작 원리, 주의사항)")

print("\n" + "="*80)
print("분석 완료!")
print("="*80)

# 점수 계산
total_checks = 10
critical_penalty = len(issues) * 3
warning_penalty = len(warnings) * 1
max_penalty = 30

penalty = min(critical_penalty + warning_penalty, max_penalty)
score = max(0, total_checks - penalty) * 10

print(f"\n회로도 품질 점수: {score}/100")
if score >= 80:
    print("평가: 우수 ✓")
elif score >= 60:
    print("평가: 양호 (개선 권장)")
elif score >= 40:
    print("평가: 보통 (여러 개선 필요)")
else:
    print("평가: 미흡 (즉각 개선 필요)")
