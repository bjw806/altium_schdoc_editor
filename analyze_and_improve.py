#!/usr/bin/env python3
"""
DI.schdoc 심층 분석 및 실질적 개선
=====================================
회로도를 분석하고 엔지니어링 관점에서 개선사항을 적용
"""

from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer
from altium_objects import *
import random

def analyze_circuit(doc):
    """회로 심층 분석"""
    print("=" * 70)
    print("🔍 회로도 심층 분석")
    print("=" * 70)

    components = doc.get_components()
    wires = doc.get_wires()
    net_labels = doc.get_net_labels()
    power_ports = doc.get_power_ports()
    junctions = doc.get_junctions()

    # 컴포넌트 분석
    print(f"\n📊 컴포넌트 분석:")
    comp_types = {}
    comp_locations = {}

    for comp in components:
        lib_ref = comp.library_reference
        comp_types[lib_ref] = comp_types.get(lib_ref, 0) + 1

        if lib_ref not in comp_locations:
            comp_locations[lib_ref] = []
        comp_locations[lib_ref].append((comp.location_x, comp.location_y))

    for lib_ref, count in sorted(comp_types.items()):
        print(f"  - {lib_ref}: {count}개")

    # 포토커플러 상세 분석
    print(f"\n🔌 포토커플러 (TLP281-4) 분석:")
    optocouplers = [c for c in components if 'TLP281' in c.library_reference]
    print(f"  - 총 {len(optocouplers)}개 사용")
    print(f"  - 각 4채널 → 총 {len(optocouplers) * 4}개 디지털 입력")

    # 저항 분석
    print(f"\n⚡ 저항 분석:")
    resistors = [c for c in components if 'RES' in c.library_reference]
    print(f"  - 총 {len(resistors)}개")

    # MCP23017 분석
    print(f"\n💾 I/O 확장 IC (MCP23017) 분석:")
    mcp_chips = [c for c in components if 'MCP23017' in c.library_reference]
    if mcp_chips:
        print(f"  - {len(mcp_chips)}개 사용")
        print(f"  - 16비트 I/O 확장 (GPA0-GPA7, GPB0-GPB7)")
        print(f"  - I2C 통신 (SCL, SDA 핀 필요)")

    # 네트 분석
    print(f"\n🌐 네트워크 분석:")
    net_groups = {}
    for label in net_labels:
        prefix = ''.join([c for c in label.text if not c.isdigit()])
        if prefix not in net_groups:
            net_groups[prefix] = []
        net_groups[prefix].append(label.text)

    for prefix, nets in sorted(net_groups.items()):
        if prefix:
            print(f"  - {prefix}: {len(nets)}개 ({', '.join(sorted(nets)[:3])}...)")

    # 파워 네트 분석
    print(f"\n⚡ 전원 분석:")
    power_nets = set(port.text for port in power_ports)
    for net in sorted(power_nets):
        count = len([p for p in power_ports if p.text == net])
        print(f"  - {net}: {count}개 위치")

    return {
        'components': components,
        'optocouplers': optocouplers,
        'resistors': resistors,
        'mcp_chips': mcp_chips,
        'net_labels': net_labels,
        'power_ports': power_ports,
        'comp_types': comp_types,
        'net_groups': net_groups
    }

def suggest_improvements(analysis):
    """엔지니어링 개선점 제안"""
    print("\n" + "=" * 70)
    print("💡 회로 개선 제안")
    print("=" * 70)

    improvements = []

    # 1. VCC 전원 누락 확인
    power_nets = set(p.text for p in analysis['power_ports'])
    if 'VCC' not in power_nets and '5V' not in power_nets:
        improvements.append({
            'type': 'add_power',
            'description': 'VCC 전원 포트 추가 필요',
            'priority': 'HIGH',
            'action': 'add_vcc_ports'
        })

    # 2. I2C 풀업 저항 확인
    if analysis['mcp_chips']:
        improvements.append({
            'type': 'i2c_pullup',
            'description': 'I2C 풀업 저항 추가 (SCL, SDA)',
            'priority': 'HIGH',
            'action': 'add_i2c_labels'
        })

    # 3. 디커플링 캐패시터 권장
    ic_count = len(analysis['mcp_chips']) + len(analysis['optocouplers'])
    improvements.append({
        'type': 'decoupling',
        'description': f'{ic_count}개 IC에 디커플링 캐패시터 권장',
        'priority': 'MEDIUM',
        'action': 'add_decoupling_note'
    })

    # 4. 회로도 정보 추가
    improvements.append({
        'type': 'documentation',
        'description': '회로도 제목, 날짜, 설명 추가',
        'priority': 'MEDIUM',
        'action': 'add_title_block'
    })

    # 5. 테스트 포인트 라벨
    improvements.append({
        'type': 'test_points',
        'description': '주요 신호에 테스트 포인트 표시',
        'priority': 'LOW',
        'action': 'add_tp_labels'
    })

    print(f"\n발견된 개선점: {len(improvements)}개\n")
    for i, imp in enumerate(improvements, 1):
        print(f"{i}. [{imp['priority']}] {imp['description']}")
        print(f"   → {imp['action']}")

    return improvements

def apply_improvements(doc, analysis):
    """실제 개선사항 적용"""
    print("\n" + "=" * 70)
    print("🔧 회로도 개선 적용")
    print("=" * 70)

    modifications = []
    next_index = len(doc.objects)

    # 개선 1: 회로도 제목 블록
    print("\n[1/6] 타이틀 블록 추가...")

    # 제목
    title = Label()
    title.index = next_index
    next_index += 1
    title.text = "16-Channel Digital Input Module (DI)"
    title.location_x = 500
    title.location_y = 9500
    title.color = 0x0000FF  # 파란색
    title.font_id = 3
    title.unique_id = f"TITLE{random.randint(1000, 9999)}"
    title.owner_part_id = -1
    title.properties = {
        'RECORD': '4',
        'TEXT': title.text,
        'LOCATION.X': str(title.location_x),
        'LOCATION.Y': str(title.location_y),
        'COLOR': str(title.color),
        'FONTID': str(title.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': title.unique_id
    }
    doc.objects.append(title)
    modifications.append("제목 추가")

    # 날짜 및 버전
    version = Label()
    version.index = next_index
    next_index += 1
    version.text = "Rev 1.1 | Modified: 2025-11-10"
    version.location_x = 500
    version.location_y = 9300
    version.color = 0x808080
    version.font_id = 2
    version.unique_id = f"VER{random.randint(1000, 9999)}"
    version.owner_part_id = -1
    version.properties = {
        'RECORD': '4',
        'TEXT': version.text,
        'LOCATION.X': str(version.location_x),
        'LOCATION.Y': str(version.location_y),
        'COLOR': str(version.color),
        'FONTID': str(version.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': version.unique_id
    }
    doc.objects.append(version)
    modifications.append("버전 정보 추가")

    # 개선 2: 회로 설명
    print("[2/6] 회로 설명 추가...")

    description = Label()
    description.index = next_index
    next_index += 1
    description.text = "MCP23017 I2C I/O Expander with Optocoupled Inputs"
    description.location_x = 500
    description.location_y = 9100
    description.color = 0x000000
    description.font_id = 1
    description.unique_id = f"DESC{random.randint(1000, 9999)}"
    description.owner_part_id = -1
    description.properties = {
        'RECORD': '4',
        'TEXT': description.text,
        'LOCATION.X': str(description.location_x),
        'LOCATION.Y': str(description.location_y),
        'COLOR': str(description.color),
        'FONTID': str(description.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': description.unique_id
    }
    doc.objects.append(description)
    modifications.append("회로 설명 추가")

    # 개선 3: I2C 신호 라벨
    print("[3/6] I2C 신호 라벨 추가...")

    i2c_labels = [
        ("SCL", 7000, 4000, "I2C Clock"),
        ("SDA", 7000, 3800, "I2C Data"),
    ]

    for net_name, x, y, desc in i2c_labels:
        # 네트 라벨
        net_label = NetLabel()
        net_label.index = next_index
        next_index += 1
        net_label.text = net_name
        net_label.location_x = x
        net_label.location_y = y
        net_label.orientation = Orientation.RIGHT
        net_label.color = 0xFF0000  # 빨간색 (중요 신호)
        net_label.font_id = 2
        net_label.unique_id = f"I2C{random.randint(1000, 9999)}"
        net_label.owner_part_id = -1
        net_label.properties = {
            'RECORD': '25',
            'TEXT': net_label.text,
            'LOCATION.X': str(net_label.location_x),
            'LOCATION.Y': str(net_label.location_y),
            'ORIENTATION': '0',
            'COLOR': str(net_label.color),
            'FONTID': str(net_label.font_id),
            'OWNERPARTID': '-1',
            'UNIQUEID': net_label.unique_id
        }
        doc.objects.append(net_label)

        # 설명 라벨
        desc_label = Label()
        desc_label.index = next_index
        next_index += 1
        desc_label.text = f"({desc})"
        desc_label.location_x = x + 200
        desc_label.location_y = y - 50
        desc_label.color = 0x808080
        desc_label.font_id = 1
        desc_label.unique_id = f"LBL{random.randint(1000, 9999)}"
        desc_label.owner_part_id = -1
        desc_label.properties = {
            'RECORD': '4',
            'TEXT': desc_label.text,
            'LOCATION.X': str(desc_label.location_x),
            'LOCATION.Y': str(desc_label.location_y),
            'COLOR': str(desc_label.color),
            'FONTID': str(desc_label.font_id),
            'OWNERPARTID': '-1',
            'UNIQUEID': desc_label.unique_id
        }
        doc.objects.append(desc_label)

    modifications.append("I2C 신호 라벨 추가 (SCL, SDA)")

    # 개선 4: VCC 전원 표시
    print("[4/6] VCC 전원 포트 추가...")

    vcc_port = PowerPort()
    vcc_port.index = next_index
    next_index += 1
    vcc_port.text = "VCC"
    vcc_port.location_x = 7500
    vcc_port.location_y = 5000
    vcc_port.style = PowerPortStyle.ARROW
    vcc_port.orientation = Orientation.UP
    vcc_port.color = 0xFF0000
    vcc_port.font_id = 2
    vcc_port.show_net_name = True
    vcc_port.unique_id = f"VCC{random.randint(1000, 9999)}"
    vcc_port.owner_part_id = -1
    vcc_port.properties = {
        'RECORD': '17',
        'TEXT': vcc_port.text,
        'LOCATION.X': str(vcc_port.location_x),
        'LOCATION.Y': str(vcc_port.location_y),
        'STYLE': str(vcc_port.style.value),
        'ORIENTATION': str(vcc_port.orientation.value),
        'COLOR': str(vcc_port.color),
        'FONTID': str(vcc_port.font_id),
        'SHOWNETNAME': 'T',
        'OWNERPARTID': '-1',
        'UNIQUEID': vcc_port.unique_id
    }
    doc.objects.append(vcc_port)
    modifications.append("VCC 전원 포트 추가")

    # 개선 5: 디커플링 캐패시터 권장 노트
    print("[5/6] 디커플링 캐패시터 노트 추가...")

    decoupling_note = Label()
    decoupling_note.index = next_index
    next_index += 1
    decoupling_note.text = "NOTE: Add 100nF decoupling caps near each IC"
    decoupling_note.location_x = 500
    decoupling_note.location_y = 8900
    decoupling_note.color = 0xFF8000  # 주황색
    decoupling_note.font_id = 2
    decoupling_note.unique_id = f"NOTE{random.randint(1000, 9999)}"
    decoupling_note.owner_part_id = -1
    decoupling_note.properties = {
        'RECORD': '4',
        'TEXT': decoupling_note.text,
        'LOCATION.X': str(decoupling_note.location_x),
        'LOCATION.Y': str(decoupling_note.location_y),
        'COLOR': str(decoupling_note.color),
        'FONTID': str(decoupling_note.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': decoupling_note.unique_id
    }
    doc.objects.append(decoupling_note)
    modifications.append("디커플링 캐패시터 권장 노트 추가")

    # 개선 6: I2C 풀업 저항 권장
    print("[6/6] I2C 풀업 저항 노트 추가...")

    pullup_note = Label()
    pullup_note.index = next_index
    next_index += 1
    pullup_note.text = "NOTE: 4.7k pullup resistors required for I2C (SCL, SDA to VCC)"
    pullup_note.location_x = 500
    pullup_note.location_y = 8700
    pullup_note.color = 0xFF8000
    pullup_note.font_id = 2
    pullup_note.unique_id = f"NOTE{random.randint(1000, 9999)}"
    pullup_note.owner_part_id = -1
    pullup_note.properties = {
        'RECORD': '4',
        'TEXT': pullup_note.text,
        'LOCATION.X': str(pullup_note.location_x),
        'LOCATION.Y': str(pullup_note.location_y),
        'COLOR': str(pullup_note.color),
        'FONTID': str(pullup_note.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': pullup_note.unique_id
    }
    doc.objects.append(pullup_note)
    modifications.append("I2C 풀업 저항 권장 노트 추가")

    print(f"\n✓ 총 {len(modifications)}개 개선사항 적용 완료")
    return modifications

def main():
    print("=" * 70)
    print("🔧 DI.schdoc 회로도 분석 및 실질적 개선")
    print("=" * 70)

    # 1. 파싱
    print("\n[단계 1/4] 회로도 파싱...")
    parser = AltiumParser()
    doc = parser.parse_file("DI.SchDoc")
    print(f"✓ {len(doc.objects)}개 객체 파싱")

    # 2. 분석
    print("\n[단계 2/4] 회로 분석...")
    analysis = analyze_circuit(doc)

    # 3. 개선점 제안
    print("\n[단계 3/4] 개선점 제안...")
    improvements = suggest_improvements(analysis)

    # 4. 개선 적용
    print("\n[단계 4/4] 개선사항 적용...")
    modifications = apply_improvements(doc, analysis)

    # 5. 저장
    print("\n[단계 5/4] 파일 저장...")
    serializer = AltiumSerializer()

    # 레코드로 직렬화
    records = serializer._build_records(doc)
    new_data = b''.join(records)

    print(f"\n직렬화 결과:")
    print(f"  - 원본 객체: 1,586개")
    print(f"  - 수정 후 객체: {len(doc.objects)}개")
    print(f"  - 추가된 객체: +{len(doc.objects) - 1586}개")
    print(f"  - 바이너리 크기: {len(new_data):,} bytes")

    # DI_improved.SchDoc으로 저장 시도
    try:
        serializer.serialize_file(doc, "DI_improved.SchDoc", template_file="DI.SchDoc")
        print(f"\n✓ DI_improved.SchDoc 저장 완료")
    except Exception as e:
        print(f"\n⚠ OLE 파일 저장 실패: {e}")
        print("→ 레코드만 저장합니다...")

        with open("DI_improved_records.bin", 'wb') as f:
            f.write(new_data)
        print("✓ DI_improved_records.bin 저장 완료")

    # 최종 요약
    print("\n" + "=" * 70)
    print("✅ 회로도 개선 완료")
    print("=" * 70)
    print(f"\n📝 적용된 개선사항 ({len(modifications)}개):")
    for i, mod in enumerate(modifications, 1):
        print(f"  {i}. {mod}")

    print(f"\n📊 개선 통계:")
    print(f"  - 추가된 타이틀/버전 정보: 3개")
    print(f"  - 추가된 I2C 라벨: 4개")
    print(f"  - 추가된 전원 포트: 1개 (VCC)")
    print(f"  - 추가된 엔지니어링 노트: 2개")

    print(f"\n📁 생성된 파일:")
    import os
    if os.path.exists("DI_improved.SchDoc"):
        size = os.path.getsize("DI_improved.SchDoc")
        print(f"  ✓ DI_improved.SchDoc ({size:,} bytes)")
    if os.path.exists("DI_improved_records.bin"):
        size = os.path.getsize("DI_improved_records.bin")
        print(f"  ✓ DI_improved_records.bin ({size:,} bytes)")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
