#!/usr/bin/env python3
"""
DI.SchDoc 파일 상세 분석 및 문제점 진단
"""

from altium_editor import SchematicEditor
from altium_parser import AltiumParser
from altium_objects import *
import json

def analyze_in_detail():
    """상세 분석"""
    print("="*80)
    print("DI.SchDoc 파일 상세 분석")
    print("="*80)

    parser = AltiumParser()
    doc = parser.parse_file("DI.SchDoc")

    print(f"\n✓ 파싱 완료: {len(doc.objects)} 객체")

    # 1. 헤더 확인
    print("\n" + "="*80)
    print("1. 파일 헤더 분석")
    print("="*80)
    if doc.header:
        print(f"버전: {doc.header.version}")
        print(f"Weight: {doc.header.weight}")
        print(f"MinorVersion: {doc.header.minor_version}")
        print(f"UniqueID: {doc.header.unique_id}")
    else:
        print("⚠️ 경고: 헤더 없음")

    # 2. 시트 정보 확인
    print("\n" + "="*80)
    print("2. 시트 정보 분석")
    print("="*80)
    if doc.sheet:
        print(f"폰트 개수: {len(doc.sheet.fonts)}")
        for i, font in enumerate(doc.sheet.fonts[:3], 1):
            print(f"  폰트 {i}: {font['name']} {font['size']}pt")
        print(f"그리드: {doc.sheet.snap_grid_size} units")
        print(f"용지 색상: 0x{doc.sheet.area_color:06X}")
    else:
        print("⚠️ 경고: 시트 정보 없음")

    # 3. 부품 상세 분석
    print("\n" + "="*80)
    print("3. 부품 상세 분석")
    print("="*80)
    components = doc.get_components()
    print(f"총 부품 개수: {len(components)}")

    # 부품별 상세 정보
    for i, comp in enumerate(components[:3], 1):
        print(f"\n부품 {i}:")
        print(f"  Library: {comp.library_reference}")
        print(f"  위치: ({comp.location_x}, {comp.location_y})")
        print(f"  방향: {comp.orientation.name} ({comp.orientation.value}°)")
        print(f"  파트 수: {comp.part_count}")
        print(f"  현재 파트: {comp.current_part_id}")
        print(f"  자식 객체 수: {len(comp.children)}")

        # 자식 객체 분석
        pins = [c for c in comp.children if isinstance(c, Pin)]
        params = [c for c in comp.children if isinstance(c, Parameter)]

        print(f"    핀: {len(pins)}개")
        for pin in pins[:3]:
            print(f"      - {pin.designator}: {pin.name} ({pin.electrical.name})")

        print(f"    파라미터: {len(params)}개")
        for param in params[:5]:
            print(f"      - {param.name}: {param.text}")

    # 4. 배선 분석
    print("\n" + "="*80)
    print("4. 배선 분석")
    print("="*80)
    wires = doc.get_wires()
    print(f"총 배선 개수: {len(wires)}")

    # 배선 통계
    total_points = sum(len(w.points) for w in wires)
    avg_points = total_points / len(wires) if wires else 0
    print(f"총 연결점: {total_points}")
    print(f"평균 점 개수: {avg_points:.1f}")

    # 배선 길이별 분포
    wire_lengths = {}
    for wire in wires:
        length = len(wire.points)
        wire_lengths[length] = wire_lengths.get(length, 0) + 1

    print(f"\n배선 점 개수 분포:")
    for length in sorted(wire_lengths.keys())[:10]:
        count = wire_lengths[length]
        print(f"  {length}점: {count}개 {'█' * min(count, 50)}")

    # 샘플 배선 상세 정보
    print(f"\n첫 3개 배선 상세:")
    for i, wire in enumerate(wires[:3], 1):
        print(f"\n배선 {i}:")
        print(f"  점 개수: {len(wire.points)}")
        print(f"  색상: 0x{wire.color:06X}")
        print(f"  선 너비: {wire.line_width}")
        print(f"  좌표:")
        for j, (x, y) in enumerate(wire.points):
            print(f"    {j}: ({x}, {y})")

    # 5. 넷 라벨 분석
    print("\n" + "="*80)
    print("5. 넷 라벨 분석")
    print("="*80)
    labels = doc.get_net_labels()
    print(f"총 넷 라벨 개수: {len(labels)}")

    # 넷 별로 그룹화
    nets = {}
    for label in labels:
        if label.text:
            if label.text not in nets:
                nets[label.text] = []
            nets[label.text].append({
                'x': label.location_x,
                'y': label.location_y,
                'orientation': label.orientation.name
            })

    print(f"고유 넷 이름: {len(nets)}개")
    print(f"\n상위 10개 넷:")
    for net_name in sorted(nets.keys())[:10]:
        locations = nets[net_name]
        print(f"  {net_name}: {len(locations)}개 위치")
        for loc in locations[:2]:
            print(f"    - ({loc['x']}, {loc['y']}) {loc['orientation']}")

    # 6. 전원 포트 분석
    print("\n" + "="*80)
    print("6. 전원 포트 분석")
    print("="*80)
    ports = doc.get_power_ports()
    print(f"총 전원 포트: {len(ports)}")

    power_nets = {}
    for port in ports:
        if port.text not in power_nets:
            power_nets[port.text] = []
        power_nets[port.text].append({
            'x': port.location_x,
            'y': port.location_y,
            'style': port.style.name,
            'orientation': port.orientation.name
        })

    for net_name, locations in power_nets.items():
        print(f"\n{net_name}: {len(locations)}개 위치")
        for loc in locations:
            print(f"  - ({loc['x']}, {loc['y']}) {loc['style']} {loc['orientation']}")

    # 7. 정션 분석
    print("\n" + "="*80)
    print("7. 정션 분석")
    print("="*80)
    junctions = doc.get_junctions()
    print(f"총 정션: {len(junctions)}개")

    # 정션 위치 분포
    if junctions:
        x_coords = [j.location_x for j in junctions]
        y_coords = [j.location_y for j in junctions]
        print(f"X 범위: {min(x_coords)} ~ {max(x_coords)}")
        print(f"Y 범위: {min(y_coords)} ~ {max(y_coords)}")

        print(f"\n첫 10개 정션 위치:")
        for i, j in enumerate(junctions[:10], 1):
            print(f"  {i}. ({j.location_x}, {j.location_y})")

    # 8. 파싱되지 않은 객체 확인
    print("\n" + "="*80)
    print("8. 파싱 문제 확인")
    print("="*80)

    generic_objects = [obj for obj in doc.objects if type(obj).__name__ == 'AltiumObject']
    print(f"⚠️ Generic AltiumObject (파싱 안됨): {len(generic_objects)}개")

    if generic_objects:
        # RECORD 타입별 분류
        record_types = {}
        for obj in generic_objects[:20]:
            record_type = obj.properties.get('RECORD', 'UNKNOWN')
            if record_type not in record_types:
                record_types[record_type] = []
            record_types[record_type].append(obj)

        print(f"\n파싱 안된 레코드 타입:")
        for record_type, objs in sorted(record_types.items()):
            print(f"  RECORD={record_type}: {len(objs)}개")
            # 첫 번째 객체의 속성 샘플
            if objs:
                sample = objs[0]
                print(f"    샘플 속성: {list(sample.properties.keys())[:10]}")

    # 9. 객체 타입 분포
    print("\n" + "="*80)
    print("9. 객체 타입 분포")
    print("="*80)

    type_counts = {}
    for obj in doc.objects:
        type_name = type(obj).__name__
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    for type_name in sorted(type_counts.keys()):
        count = type_counts[type_name]
        bar = '█' * min(count // 5, 50)
        print(f"  {type_name:30s}: {count:4d} {bar}")

    # 10. 좌표 범위 분석
    print("\n" + "="*80)
    print("10. 회로도 좌표 범위")
    print("="*80)

    all_x = []
    all_y = []

    for comp in components:
        all_x.append(comp.location_x)
        all_y.append(comp.location_y)

    for wire in wires:
        for x, y in wire.points:
            all_x.append(x)
            all_y.append(y)

    for label in labels:
        all_x.append(label.location_x)
        all_y.append(label.location_y)

    if all_x and all_y:
        print(f"X 범위: {min(all_x)} ~ {max(all_x)} (폭: {max(all_x) - min(all_x)} units)")
        print(f"Y 범위: {min(all_y)} ~ {max(all_y)} (높이: {max(all_y) - min(all_y)} units)")
        print(f"크기 (mm): {(max(all_x) - min(all_x)) * 0.254:.1f} x {(max(all_y) - min(all_y)) * 0.254:.1f}")

    return doc, generic_objects

def find_issues(doc, generic_objects):
    """문제점 분석"""
    print("\n" + "="*80)
    print("🔍 문제점 진단")
    print("="*80)

    issues = []
    warnings = []

    # 1. 파싱되지 않은 객체
    if generic_objects:
        issues.append(f"파싱되지 않은 객체 {len(generic_objects)}개 발견")

    # 2. 부품에 designator가 없는 경우
    components = doc.get_components()
    no_designator = []
    for comp in components:
        has_designator = False
        for child in comp.children:
            if isinstance(child, Parameter) and child.name == "Designator":
                has_designator = True
                break
        if not has_designator:
            no_designator.append(comp.library_reference)

    if no_designator:
        warnings.append(f"{len(no_designator)}개 부품에 Designator 없음: {no_designator[:3]}")

    # 3. 고립된 배선 (넷 라벨 없음)
    wires = doc.get_wires()
    labels = doc.get_net_labels()

    if len(wires) > 0 and len(labels) == 0:
        warnings.append("배선은 있지만 넷 라벨이 전혀 없음")

    # 4. 중복 위치 확인
    junctions = doc.get_junctions()
    junction_positions = {}
    for j in junctions:
        pos = (j.location_x, j.location_y)
        junction_positions[pos] = junction_positions.get(pos, 0) + 1

    duplicates = {pos: count for pos, count in junction_positions.items() if count > 1}
    if duplicates:
        warnings.append(f"{len(duplicates)}개 위치에 중복 정션: {list(duplicates.items())[:3]}")

    # 5. 부품 핀 개수 확인
    for comp in components[:5]:
        pins = [c for c in comp.children if isinstance(c, Pin)]
        if len(pins) == 0:
            warnings.append(f"부품 {comp.library_reference}에 핀 없음")

    # 결과 출력
    if issues:
        print("\n❌ 심각한 문제:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("\n✅ 심각한 문제 없음")

    if warnings:
        print("\n⚠️  경고:")
        for warning in warnings:
            print(f"  • {warning}")
    else:
        print("\n✅ 경고 없음")

    return issues, warnings

if __name__ == "__main__":
    doc, generic_objects = analyze_in_detail()
    issues, warnings = find_issues(doc, generic_objects)

    print("\n" + "="*80)
    print("분석 완료")
    print("="*80)
    print(f"\n총 객체: {len(doc.objects)}")
    print(f"심각한 문제: {len(issues)}개")
    print(f"경고: {len(warnings)}개")
    print()
