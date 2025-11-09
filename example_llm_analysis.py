#!/usr/bin/env python3
"""
LLM이 회로도를 분석하고 수정하는 예제
"""

from altium_editor import SchematicEditor
from altium_objects import Orientation

def analyze_schematic():
    """회로도 분석 - LLM이 모든 정보를 읽을 수 있음"""
    print("=== 회로도 분석 ===\n")

    editor = SchematicEditor()
    editor.load("DI.SchDoc")

    # 1. 모든 부품 위치 확인
    print("📍 부품 위치:")
    for i, comp in enumerate(editor.get_components()[:5], 1):
        # 부품 이름 찾기
        designator = "?"
        for child in comp.children:
            if hasattr(child, 'name') and child.name == "Designator":
                designator = child.text
                break

        print(f"{i}. {designator}: {comp.library_reference}")
        print(f"   위치: X={comp.location_x}, Y={comp.location_y}")
        print(f"   방향: {comp.orientation.name} ({comp.orientation.value}도)")

    # 2. 배선 정보 확인
    print(f"\n🔌 총 배선 개수: {len(editor.get_wires())}")
    print("첫 5개 배선 정보:")
    for i, wire in enumerate(editor.get_wires()[:5], 1):
        print(f"{i}. {len(wire.points)}개 점으로 구성:")
        print(f"   시작: {wire.points[0]}")
        print(f"   끝: {wire.points[-1]}")

    # 3. 넷 라벨 확인
    print(f"\n🏷️  넷 라벨:")
    nets = {}
    for label in editor.get_net_labels():
        if label.text:
            if label.text not in nets:
                nets[label.text] = []
            nets[label.text].append((label.location_x, label.location_y))

    for net_name, locations in sorted(nets.items())[:10]:
        print(f"  {net_name}: {len(locations)}개 위치")
        for loc in locations[:2]:
            print(f"    - {loc}")

    # 4. 전원 포트 확인
    print(f"\n⚡ 전원 포트:")
    for port in editor.get_power_ports():
        print(f"  {port.text} ({port.style.name})")
        print(f"    위치: ({port.location_x}, {port.location_y})")
        print(f"    방향: {port.orientation.name}")


def modify_layout():
    """배치 수정 - LLM이 부품 위치를 수정할 수 있음"""
    print("\n\n=== 배치 수정 ===\n")

    editor = SchematicEditor()
    editor.load("DI.SchDoc")

    original_count = len(editor.get_components())
    print(f"원본 부품 개수: {original_count}")

    # 수정 1: 모든 저항을 오른쪽으로 50 units 이동
    print("\n📝 수정 1: 모든 RES 부품을 오른쪽으로 50 units 이동")
    res_count = 0
    for comp in editor.get_components():
        if "RES" in comp.library_reference:
            old_x = comp.location_x
            comp.location_x += 50
            res_count += 1
            print(f"  {comp.library_reference}: X {old_x} → {comp.location_x}")
    print(f"  총 {res_count}개 저항 이동됨")

    # 수정 2: 특정 부품 회전
    print("\n📝 수정 2: 첫 번째 부품 90도 회전")
    first_comp = editor.get_components()[0]
    old_orient = first_comp.orientation
    if first_comp.orientation == Orientation.RIGHT:
        first_comp.orientation = Orientation.UP
    print(f"  {first_comp.library_reference}: {old_orient.name} → {first_comp.orientation.name}")

    # 수정 3: 새 부품 추가
    print("\n📝 수정 3: 새 부품 추가")
    new_comp = editor.add_component(
        library_reference="NEW_IC",
        x=3000,
        y=3000,
        designator="U100",
        orientation=Orientation.RIGHT
    )
    print(f"  추가됨: U100 at ({new_comp.location_x}, {new_comp.location_y})")

    # 수정 4: 새 배선 추가
    print("\n📝 수정 4: 새 배선 추가")
    new_wire = editor.add_wire([(3000, 3000), (3500, 3000), (3500, 3500)])
    print(f"  배선 추가: {len(new_wire.points)}개 점")

    # 저장
    output_file = "DI_modified_layout.SchDoc"
    print(f"\n💾 수정된 회로도 저장: {output_file}")
    editor.save(output_file)

    # 검증
    editor2 = SchematicEditor()
    editor2.load(output_file)
    print(f"✓ 검증 완료: {len(editor2.get_components())}개 부품 ({original_count} → {len(editor2.get_components())})")


def find_and_move_components():
    """특정 조건의 부품 찾아서 이동"""
    print("\n\n=== 조건부 배치 수정 ===\n")

    editor = SchematicEditor()
    editor.load("DI.SchDoc")

    # 예: 특정 Y 좌표 아래에 있는 모든 부품을 위로 이동
    threshold_y = 400
    move_distance = 100

    print(f"Y < {threshold_y}인 부품을 위로 {move_distance} units 이동:")
    moved_count = 0

    for comp in editor.get_components():
        if comp.location_y < threshold_y:
            old_y = comp.location_y
            comp.location_y += move_distance
            moved_count += 1
            print(f"  {comp.library_reference}: Y {old_y} → {comp.location_y}")

    print(f"\n총 {moved_count}개 부품 이동됨")

    if moved_count > 0:
        editor.save("DI_repositioned.SchDoc")
        print("✓ 저장 완료: DI_repositioned.SchDoc")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("LLM을 위한 Altium 회로도 분석 및 수정 예제")
    print("="*70 + "\n")

    # 1. 회로도 분석
    analyze_schematic()

    # 2. 배치 수정
    modify_layout()

    # 3. 조건부 수정
    find_and_move_components()

    print("\n" + "="*70)
    print("✅ 모든 작업 완료!")
    print("="*70 + "\n")
