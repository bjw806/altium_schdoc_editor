#!/usr/bin/env python3
"""
DI.schdoc 회로도 분석 및 개선
================================
회로도를 파싱하여 분석하고, 개선점을 적용한 후 DI_modified.schdoc으로 저장
"""

from altium_parser import AltiumParser
from altium_editor import SchematicEditor
from altium_objects import *

def analyze_schematic(doc):
    """회로도 분석"""
    print("=" * 70)
    print("회로도 분석")
    print("=" * 70)

    components = doc.get_components()
    wires = doc.get_wires()
    net_labels = doc.get_net_labels()
    power_ports = doc.get_power_ports()
    junctions = doc.get_junctions()

    print(f"\n📊 통계:")
    print(f"  - 컴포넌트: {len(components)}개")
    print(f"  - 와이어: {len(wires)}개")
    print(f"  - 네트 라벨: {len(net_labels)}개")
    print(f"  - 파워 포트: {len(power_ports)}개")
    print(f"  - 접합점: {len(junctions)}개")

    print(f"\n🔍 컴포넌트 상세:")
    comp_types = {}
    for comp in components:
        lib_ref = comp.library_reference
        comp_types[lib_ref] = comp_types.get(lib_ref, 0) + 1

    for lib_ref, count in sorted(comp_types.items()):
        print(f"  - {lib_ref}: {count}개")

    print(f"\n⚡ 파워 네트:")
    power_nets = set()
    for port in power_ports:
        power_nets.add(port.text)
    for net in sorted(power_nets):
        print(f"  - {net}")

    print(f"\n🏷️  네트 라벨:")
    net_names = {}
    for label in net_labels:
        net_names[label.text] = net_names.get(label.text, 0) + 1

    for name, count in sorted(net_names.items())[:10]:  # 상위 10개만
        print(f"  - {name}: {count}개 위치")
    if len(net_names) > 10:
        print(f"  ... 외 {len(net_names) - 10}개")

    return {
        'components': components,
        'wires': wires,
        'net_labels': net_labels,
        'power_ports': power_ports,
        'comp_types': comp_types,
        'net_names': net_names
    }

def suggest_improvements(analysis):
    """개선점 제안"""
    print("\n" + "=" * 70)
    print("💡 개선점 제안")
    print("=" * 70)

    improvements = []

    # 1. 타이틀 블록 추가
    improvements.append({
        'type': 'add_label',
        'description': '회로도 제목 추가',
        'action': 'title',
        'priority': 'high'
    })

    # 2. 날짜/버전 정보
    improvements.append({
        'type': 'add_label',
        'description': '날짜 및 버전 정보 추가',
        'action': 'metadata',
        'priority': 'medium'
    })

    # 3. 주요 신호 라벨 강조
    improvements.append({
        'type': 'enhance_labels',
        'description': '주요 신호 라벨에 설명 추가',
        'action': 'annotations',
        'priority': 'medium'
    })

    for i, imp in enumerate(improvements, 1):
        print(f"\n{i}. [{imp['priority'].upper()}] {imp['description']}")
        print(f"   유형: {imp['type']}")

    return improvements

def apply_improvements(doc, analysis, improvements):
    """개선사항 적용"""
    print("\n" + "=" * 70)
    print("✏️  개선사항 적용 중...")
    print("=" * 70)

    modifications = []

    # 1. 타이틀 라벨 추가
    print("\n[1/3] 회로도 제목 추가...")
    title_label = Label()
    title_label.index = len(doc.objects)
    title_label.text = "DI Schematic - Modified & Enhanced"
    title_label.location_x = 400
    title_label.location_y = 9400
    title_label.color = 0x0000FF  # 파란색
    title_label.font_id = 3  # Bold font
    title_label.unique_id = "MOD00001"
    title_label.owner_part_id = -1
    title_label.properties = {
        'RECORD': '4',
        'TEXT': title_label.text,
        'LOCATION.X': str(title_label.location_x),
        'LOCATION.Y': str(title_label.location_y),
        'COLOR': str(title_label.color),
        'FONTID': str(title_label.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': title_label.unique_id
    }
    doc.objects.append(title_label)
    modifications.append("타이틀 라벨 추가")
    print("  ✓ 타이틀 추가됨")

    # 2. 날짜/버전 정보 추가
    print("\n[2/3] 버전 정보 추가...")
    version_label = Label()
    version_label.index = len(doc.objects)
    version_label.text = "Modified: 2025-11-10 | v1.1"
    version_label.location_x = 400
    version_label.location_y = 9200
    version_label.color = 0x808080  # 회색
    version_label.font_id = 2
    version_label.unique_id = "MOD00002"
    version_label.owner_part_id = -1
    version_label.properties = {
        'RECORD': '4',
        'TEXT': version_label.text,
        'LOCATION.X': str(version_label.location_x),
        'LOCATION.Y': str(version_label.location_y),
        'COLOR': str(version_label.color),
        'FONTID': str(version_label.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': version_label.unique_id
    }
    doc.objects.append(version_label)
    modifications.append("버전 정보 추가")
    print("  ✓ 버전 정보 추가됨")

    # 3. 주요 파워 네트에 주석 추가
    print("\n[3/3] 파워 네트 주석 추가...")
    power_annotations = {
        'VCC': 'Main Power Supply',
        'GND': 'Ground Reference',
    }

    added_annotations = 0
    for port in doc.get_power_ports():
        if port.text in power_annotations:
            annotation = Label()
            annotation.index = len(doc.objects)
            annotation.text = power_annotations[port.text]
            annotation.location_x = port.location_x + 100
            annotation.location_y = port.location_y + 50
            annotation.color = 0x008000  # 녹색
            annotation.font_id = 1
            annotation.unique_id = f"ANN{added_annotations:05d}"
            annotation.owner_part_id = -1
            annotation.properties = {
                'RECORD': '4',
                'TEXT': annotation.text,
                'LOCATION.X': str(annotation.location_x),
                'LOCATION.Y': str(annotation.location_y),
                'COLOR': str(annotation.color),
                'FONTID': str(annotation.font_id),
                'OWNERPARTID': '-1',
                'UNIQUEID': annotation.unique_id
            }
            doc.objects.append(annotation)
            added_annotations += 1

    if added_annotations > 0:
        modifications.append(f"{added_annotations}개 주석 추가")
        print(f"  ✓ {added_annotations}개 주석 추가됨")

    return modifications

def main():
    print("=" * 70)
    print("DI.schdoc 회로도 분석 및 개선")
    print("=" * 70)

    # 1. 파싱
    print("\n[단계 1] DI.schdoc 파싱 중...")
    parser = AltiumParser()
    doc = parser.parse_file("DI.SchDoc")
    print(f"✓ 파싱 완료: {len(doc.objects)}개 객체")

    # 2. 분석
    print("\n[단계 2] 회로도 분석 중...")
    analysis = analyze_schematic(doc)

    # 3. 개선점 제안
    print("\n[단계 3] 개선점 제안...")
    improvements = suggest_improvements(analysis)

    # 4. 개선사항 적용
    print("\n[단계 4] 개선사항 적용...")
    modifications = apply_improvements(doc, analysis, improvements)

    # 5. 저장 시도
    print("\n[단계 5] DI_modified.schdoc 저장 중...")

    from altium_serializer import AltiumSerializer
    serializer = AltiumSerializer()

    try:
        serializer.serialize_file(doc, "DI_modified.SchDoc", template_file="DI.SchDoc")
        print("✓ 저장 완료: DI_modified.SchDoc")
    except Exception as e:
        print(f"⚠ 저장 실패: {e}")
        print("\n대체 방법: 레코드만 저장...")
        records = serializer._build_records(doc)
        with open("DI_modified_records.bin", 'wb') as f:
            f.write(b''.join(records))
        print("✓ 레코드 저장 완료: DI_modified_records.bin")

    # 최종 요약
    print("\n" + "=" * 70)
    print("✅ 작업 완료")
    print("=" * 70)
    print(f"\n📝 적용된 수정사항:")
    for i, mod in enumerate(modifications, 1):
        print(f"  {i}. {mod}")

    print(f"\n📊 최종 통계:")
    print(f"  - 원본 객체 수: 1,586")
    print(f"  - 수정 후 객체 수: {len(doc.objects)}")
    print(f"  - 추가된 객체: {len(doc.objects) - 1586}")

    print(f"\n📁 생성된 파일:")
    import os
    if os.path.exists("DI_modified.SchDoc"):
        size = os.path.getsize("DI_modified.SchDoc")
        print(f"  - DI_modified.SchDoc ({size:,} bytes)")
    if os.path.exists("DI_modified_records.bin"):
        size = os.path.getsize("DI_modified_records.bin")
        print(f"  - DI_modified_records.bin ({size:,} bytes)")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
