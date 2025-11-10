#!/usr/bin/env python3
"""
DI.SchDoc 분석 및 개선 스크립트
================================

1. DI.SchDoc 파일을 파싱하여 완전한 회로도 구조 분석
2. 개선 가능한 부분 식별
3. 개선점을 적용한 새로운 회로도 생성
"""

from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer
from altium_editor import SchematicEditor
from altium_objects import *
from typing import Dict, List, Tuple, Set
import json


class SchematicAnalyzer:
    """회로도 분석 클래스"""

    def __init__(self, doc: SchDoc):
        self.doc = doc
        self.issues = []
        self.suggestions = []

    def analyze(self):
        """전체 회로도 분석"""
        print("=" * 80)
        print("회로도 상세 분석 시작")
        print("=" * 80)

        self.analyze_basic_info()
        self.analyze_components()
        self.analyze_nets()
        self.analyze_connections()
        self.analyze_power_distribution()
        self.analyze_layout()

        return self.issues, self.suggestions

    def analyze_basic_info(self):
        """기본 정보 분석"""
        print("\n📋 기본 정보:")
        print(f"  헤더: {self.doc.header.version if self.doc.header else 'N/A'}")
        print(f"  전체 객체 수: {len(self.doc.objects)}")

        components = self.doc.get_components()
        wires = self.doc.get_wires()
        nets = self.doc.get_net_labels()
        power_ports = self.doc.get_power_ports()
        junctions = self.doc.get_junctions()

        print(f"  - 부품: {len(components)}개")
        print(f"  - 배선: {len(wires)}개")
        print(f"  - 네트 레이블: {len(nets)}개")
        print(f"  - 전원 포트: {len(power_ports)}개")
        print(f"  - 접속점: {len(junctions)}개")

    def analyze_components(self):
        """부품 분석"""
        print("\n🔧 부품 상세 분석:")

        components = self.doc.get_components()
        comp_types = {}
        designators = set()
        duplicate_designators = []

        for comp in components:
            # 부품 타입 집계
            lib_ref = comp.library_reference
            if lib_ref not in comp_types:
                comp_types[lib_ref] = []
            comp_types[lib_ref].append(comp)

            # 지정자 확인
            designator = None
            value = None
            for child in comp.children:
                if isinstance(child, Parameter):
                    if child.name == "Designator":
                        designator = child.text
                    elif child.name == "Value":
                        value = child.text

            if designator:
                if designator in designators:
                    duplicate_designators.append(designator)
                    self.issues.append(f"중복된 지정자: {designator}")
                designators.add(designator)

            # 핀 정보 추출
            pins = [child for child in comp.children if isinstance(child, Pin)]

            print(f"\n  {designator or '???'}: {lib_ref}")
            if value:
                print(f"    값: {value}")
            print(f"    위치: ({comp.location_x}, {comp.location_y})")
            print(f"    방향: {comp.orientation.name}")
            print(f"    핀 수: {len(pins)}")

            # 핀 상세 정보
            for pin in pins:
                print(f"      Pin {pin.designator}: {pin.name} ({pin.electrical.name})")

        print(f"\n  부품 타입별 집계:")
        for lib_ref, comps in sorted(comp_types.items()):
            print(f"    {lib_ref}: {len(comps)}개")

        if duplicate_designators:
            print(f"\n  ⚠️  중복 지정자 발견: {duplicate_designators}")

    def analyze_nets(self):
        """네트 분석"""
        print("\n🔌 네트 분석:")

        net_labels = self.doc.get_net_labels()
        wires = self.doc.get_wires()

        # 네트별로 그룹화
        nets = {}
        for label in net_labels:
            if label.text not in nets:
                nets[label.text] = {
                    'labels': [],
                    'wires': [],
                    'components': []
                }
            nets[label.text]['labels'].append(label)

        # 각 네트에 연결된 배선 찾기
        for net_name, net_info in nets.items():
            for label in net_info['labels']:
                for wire in wires:
                    for point in wire.points:
                        dist = ((point[0] - label.location_x)**2 +
                               (point[1] - label.location_y)**2)**0.5
                        if dist < 100:  # 100 mils 이내
                            if wire not in net_info['wires']:
                                net_info['wires'].append(wire)

        print(f"\n  네트 목록 ({len(nets)}개):")
        for net_name, net_info in sorted(nets.items()):
            print(f"\n    '{net_name}':")
            print(f"      레이블: {len(net_info['labels'])}개")
            print(f"      연결된 배선: {len(net_info['wires'])}개")

            # 배선 길이 계산
            total_length = 0
            for wire in net_info['wires']:
                for i in range(len(wire.points) - 1):
                    x1, y1 = wire.points[i]
                    x2, y2 = wire.points[i + 1]
                    total_length += ((x2 - x1)**2 + (y2 - y1)**2)**0.5

            if total_length > 0:
                print(f"      총 길이: {int(total_length)} mils ({int(total_length * 0.254)} mm)")

    def analyze_connections(self):
        """연결성 분석"""
        print("\n🔗 연결성 분석:")

        wires = self.doc.get_wires()
        junctions = self.doc.get_junctions()
        components = self.doc.get_components()

        # 접속점이 필요한 위치 찾기
        wire_intersections = self.find_wire_intersections(wires)

        missing_junctions = 0
        for intersection in wire_intersections:
            # 해당 위치에 접속점이 있는지 확인
            has_junction = False
            for junction in junctions:
                dist = ((junction.location_x - intersection[0])**2 +
                       (junction.location_y - intersection[1])**2)**0.5
                if dist < 10:  # 10 mils 이내
                    has_junction = True
                    break

            if not has_junction:
                missing_junctions += 1
                self.issues.append(f"접속점 누락 가능: ({intersection[0]}, {intersection[1]})")

        print(f"  배선 교차점: {len(wire_intersections)}개")
        print(f"  접속점: {len(junctions)}개")
        if missing_junctions > 0:
            print(f"  ⚠️  접속점이 필요할 수 있는 위치: {missing_junctions}개")
            self.suggestions.append(f"{missing_junctions}개 위치에 접속점 추가 권장")

    def analyze_power_distribution(self):
        """전원 분배 분석"""
        print("\n⚡ 전원 분배 분석:")

        power_ports = self.doc.get_power_ports()
        power_nets = {}

        for port in power_ports:
            if port.text not in power_nets:
                power_nets[port.text] = []
            power_nets[port.text].append(port)

        print(f"\n  전원 네트 ({len(power_nets)}개):")
        for net_name, ports in sorted(power_nets.items()):
            print(f"    {net_name}: {len(ports)}개 연결")

            # 스타일별 집계
            styles = {}
            for port in ports:
                style = port.style.name
                styles[style] = styles.get(style, 0) + 1

            for style, count in styles.items():
                print(f"      {style}: {count}개")

        # 전원 연결성 확인
        if 'GND' not in power_nets and 'GNDD' not in power_nets:
            self.issues.append("GND 전원이 정의되지 않음")
            print(f"  ⚠️  GND 전원이 없습니다")

    def analyze_layout(self):
        """레이아웃 분석"""
        print("\n📐 레이아웃 분석:")

        components = self.doc.get_components()

        if not components:
            return

        # 부품 위치 범위 계산
        min_x = min(comp.location_x for comp in components)
        max_x = max(comp.location_x for comp in components)
        min_y = min(comp.location_y for comp in components)
        max_y = max(comp.location_y for comp in components)

        width = max_x - min_x
        height = max_y - min_y

        print(f"  회로도 범위:")
        print(f"    X: {min_x} ~ {max_x} ({width} mils)")
        print(f"    Y: {min_y} ~ {max_y} ({height} mils)")
        print(f"    크기: {int(width * 0.254)}mm × {int(height * 0.254)}mm")

        # 부품 밀집도 확인
        area = width * height if width > 0 and height > 0 else 1
        density = len(components) / (area / 1000000)  # per million sq mils

        print(f"    부품 밀집도: {density:.2f} 부품/제곱인치")

        if density > 50:
            self.suggestions.append("부품이 밀집되어 있습니다. 간격을 넓히는 것을 권장합니다.")

    def find_wire_intersections(self, wires: List[Wire]) -> List[Tuple[int, int]]:
        """배선 교차점 찾기"""
        intersections = []

        # 모든 배선 세그먼트 쌍을 검사
        for i, wire1 in enumerate(wires):
            for j, wire2 in enumerate(wires):
                if i >= j:
                    continue

                # wire1의 각 세그먼트와 wire2의 각 세그먼트 비교
                for k in range(len(wire1.points) - 1):
                    for l in range(len(wire2.points) - 1):
                        intersection = self.segment_intersection(
                            wire1.points[k], wire1.points[k+1],
                            wire2.points[l], wire2.points[l+1]
                        )
                        if intersection:
                            intersections.append(intersection)

        return intersections

    def segment_intersection(self, p1, p2, p3, p4) -> Tuple[int, int] or None:
        """두 선분의 교차점 계산"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            x = int(x1 + t * (x2 - x1))
            y = int(y1 + t * (y2 - y1))
            return (x, y)

        return None


class SchematicImprover:
    """회로도 개선 클래스"""

    def __init__(self, editor: SchematicEditor, issues: List[str], suggestions: List[str]):
        self.editor = editor
        self.issues = issues
        self.suggestions = suggestions
        self.improvements_applied = []

    def apply_improvements(self):
        """개선사항 적용"""
        print("\n" + "=" * 80)
        print("개선사항 적용")
        print("=" * 80)

        self.add_missing_junctions()
        self.add_decoupling_capacitors()
        self.improve_power_distribution()
        self.add_documentation()

        return self.improvements_applied

    def add_missing_junctions(self):
        """누락된 접속점 추가"""
        print("\n🔴 접속점 추가:")

        # 이슈에서 누락된 접속점 찾기
        junction_count = 0
        for issue in self.issues:
            if "접속점 누락" in issue:
                # 좌표 추출
                try:
                    coords = issue.split("(")[1].split(")")[0]
                    x, y = map(int, coords.split(","))

                    # 접속점 추가
                    self.editor.add_junction(x, y)
                    junction_count += 1
                    print(f"  ✓ 접속점 추가: ({x}, {y})")

                except:
                    pass

        if junction_count > 0:
            self.improvements_applied.append(f"{junction_count}개 접속점 추가")
        else:
            print("  추가할 접속점 없음")

    def add_decoupling_capacitors(self):
        """디커플링 커패시터 추가"""
        print("\n🔋 디커플링 커패시터 추가:")

        # IC 부품 찾기 (U로 시작하는 지정자)
        components = self.editor.get_components()
        ic_components = []

        for comp in components:
            for child in comp.children:
                if isinstance(child, Parameter) and child.name == "Designator":
                    if child.text.startswith("U"):
                        ic_components.append((comp, child.text))
                        break

        if not ic_components:
            print("  IC 부품이 없어 디커플링 커패시터를 추가하지 않습니다.")
            return

        cap_count = 0
        for comp, designator in ic_components:
            # IC 근처에 디커플링 커패시터 추가
            cap_x = comp.location_x + 300
            cap_y = comp.location_y + 200

            cap_designator = f"C_DEC_{designator}"

            # 커패시터 추가
            cap = self.editor.add_capacitor(
                cap_x, cap_y,
                value="100nF",
                designator=cap_designator,
                orientation=Orientation.DOWN
            )

            # 전원 연결
            # VCC 연결
            vcc = self.editor.add_power_port(
                cap_x, cap_y + 150,
                text="VCC",
                style=PowerPortStyle.ARROW,
                orientation=Orientation.UP
            )

            wire1 = self.editor.add_wire([
                (cap_x, cap_y + 150),
                (cap_x, cap_y)
            ])

            # GND 연결
            gnd = self.editor.add_power_port(
                cap_x, cap_y - 150,
                text="GND",
                style=PowerPortStyle.POWER_GROUND,
                orientation=Orientation.DOWN
            )

            wire2 = self.editor.add_wire([
                (cap_x, cap_y - 150),
                (cap_x, cap_y)
            ])

            cap_count += 1
            print(f"  ✓ {designator} 근처에 디커플링 커패시터 추가: {cap_designator}")

        self.improvements_applied.append(f"{cap_count}개 디커플링 커패시터 추가")

    def improve_power_distribution(self):
        """전원 분배 개선"""
        print("\n⚡ 전원 분배 개선:")

        # 전원 심볼 추가 (회로도 좌측 상단)
        power_x = 1000
        power_y = 5000

        # VCC 전원 심볼
        vcc = self.editor.add_power_port(
            power_x, power_y,
            text="VCC",
            style=PowerPortStyle.ARROW,
            orientation=Orientation.DOWN
        )

        vcc_label = self.editor.add_label(
            power_x + 100, power_y,
            "+5V",
            color=rgb_to_color(255, 0, 0)
        )

        # GND 전원 심볼
        gnd = self.editor.add_power_port(
            power_x, power_y - 300,
            text="GND",
            style=PowerPortStyle.POWER_GROUND,
            orientation=Orientation.DOWN
        )

        print(f"  ✓ 전원 심볼 추가 (VCC, GND)")
        self.improvements_applied.append("전원 심볼 정리")

    def add_documentation(self):
        """문서화 추가"""
        print("\n📝 문서화 추가:")

        # 제목 추가
        title_x = 1000
        title_y = 6000

        title = self.editor.add_label(
            title_x, title_y,
            "Improved Schematic",
            color=rgb_to_color(0, 0, 128),
            font_id=1
        )

        # 개선 내용 표시
        note_y = title_y - 200
        for i, improvement in enumerate(self.improvements_applied):
            note = self.editor.add_label(
                title_x, note_y - i * 100,
                f"✓ {improvement}",
                color=rgb_to_color(0, 128, 0),
                font_id=1
            )

        print(f"  ✓ 제목 및 개선 내용 레이블 추가")
        self.improvements_applied.append("문서화 추가")


def main():
    """메인 함수"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                  DI.SchDoc 분석 및 개선 시스템                             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)

    input_file = "DI.SchDoc"
    output_file = "DI_improved.SchDoc"
    report_file = "DI_analysis_report.json"

    # 1. 파일 파싱
    print(f"\n📂 파일 로드: {input_file}")
    parser = AltiumParser()
    doc = parser.parse_file(input_file)
    print(f"✓ 파싱 완료: {len(doc.objects)}개 객체")

    # 2. 분석
    analyzer = SchematicAnalyzer(doc)
    issues, suggestions = analyzer.analyze()

    # 3. 분석 결과 요약
    print("\n" + "=" * 80)
    print("분석 결과 요약")
    print("=" * 80)

    if issues:
        print(f"\n⚠️  발견된 이슈 ({len(issues)}개):")
        for i, issue in enumerate(issues[:10], 1):  # 최대 10개만 표시
            print(f"  {i}. {issue}")
        if len(issues) > 10:
            print(f"  ... 외 {len(issues) - 10}개")
    else:
        print("\n✓ 이슈 없음")

    if suggestions:
        print(f"\n💡 개선 제안 ({len(suggestions)}개):")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print("\n✓ 개선 제안 없음")

    # 4. 개선사항 적용
    print("\n" + "=" * 80)
    print("개선된 회로도 생성")
    print("=" * 80)

    editor = SchematicEditor()
    editor.load(input_file)

    print(f"\n원본 회로도:")
    editor.print_summary()

    improver = SchematicImprover(editor, issues, suggestions)
    improvements = improver.apply_improvements()

    # 5. 저장
    print(f"\n💾 저장 중: {output_file}")
    editor.save(output_file)
    print(f"✓ 저장 완료!")

    print(f"\n개선된 회로도:")
    editor.print_summary()

    # 6. 보고서 생성
    report = {
        "input_file": input_file,
        "output_file": output_file,
        "analysis": {
            "total_objects": len(doc.objects),
            "components": len(doc.get_components()),
            "wires": len(doc.get_wires()),
            "net_labels": len(doc.get_net_labels()),
            "power_ports": len(doc.get_power_ports()),
            "junctions": len(doc.get_junctions())
        },
        "issues": issues,
        "suggestions": suggestions,
        "improvements_applied": improvements
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📊 분석 보고서 저장: {report_file}")

    # 7. 최종 요약
    print("\n" + "=" * 80)
    print("✨ 작업 완료!")
    print("=" * 80)
    print(f"\n생성된 파일:")
    print(f"  📄 {output_file} - 개선된 회로도 (Altium에서 열 수 있음)")
    print(f"  📄 {report_file} - 상세 분석 보고서 (JSON)")

    print(f"\n적용된 개선사항:")
    for improvement in improvements:
        print(f"  ✓ {improvement}")

    print(f"\n이제 Altium Designer에서 '{output_file}'을 열어 개선사항을 확인할 수 있습니다!")


if __name__ == "__main__":
    main()
