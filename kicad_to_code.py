"""
KiCad Schematic to Python Code Converter
=========================================
KiCad .kicad_sch 파일을 읽어서 Python API 형식의 회로도 코드로 변환합니다.

사용법:
    python kicad_to_code.py input.kicad_sch output.py
"""

import sys
from pathlib import Path
from typing import Any
import sexpdata


def parse_position(pos_data):
    """위치 데이터 파싱"""
    if isinstance(pos_data, list) and len(pos_data) >= 3:
        return (float(pos_data[1]), float(pos_data[2]))
    return (0.0, 0.0)


def extract_components_from_sexp(sexp_data):
    """S-expression에서 컴포넌트 추출"""
    components = []
    
    def traverse(node):
        if isinstance(node, list) and len(node) > 0:
            if isinstance(node[0], sexpdata.Symbol):
                if str(node[0]) == 'symbol':
                    # 심볼 인스턴스 찾기
                    comp_data = {}
                    for item in node[1:]:
                        if isinstance(item, list) and len(item) > 0:
                            key = str(item[0]) if isinstance(item[0], sexpdata.Symbol) else None
                            if key == 'lib_id':
                                lib_id = str(item[1])
                                # lib_id가 유효한지 확인 (Library:Symbol 형식)
                                if ':' not in lib_id:
                                    lib_id = f"Device:{lib_id}" if lib_id else "Device:Unknown"
                                comp_data['lib_id'] = lib_id
                            elif key == 'at':
                                comp_data['position'] = parse_position(item)
                            elif key == 'unit':
                                comp_data['unit'] = int(item[1]) if len(item) > 1 else 1
                            elif key == 'mirror':
                                # mirror x or mirror y
                                comp_data['mirror'] = str(item[1]) if len(item) > 1 else None
                            elif key == 'exclude_from_sim':
                                comp_data['exclude_from_sim'] = str(item[1]) == 'no'
                            elif key == 'in_bom':
                                comp_data['in_bom'] = str(item[1]) == 'yes'
                            elif key == 'on_board':
                                comp_data['on_board'] = str(item[1]) == 'yes'
                            elif key == 'dnp':
                                comp_data['dnp'] = str(item[1]) == 'yes'
                            elif key == 'property':
                                prop_name = str(item[1])
                                prop_value = str(item[2]) if len(item) > 2 else ""
                                if prop_name == 'Reference':
                                    comp_data['reference'] = prop_value
                                    # Reference property의 위치와 각도도 저장
                                    for prop_item in item[3:]:
                                        if isinstance(prop_item, list) and len(prop_item) > 0:
                                            if str(prop_item[0]) == 'at':
                                                comp_data['reference_at'] = parse_position(prop_item)
                                elif prop_name == 'Value':
                                    comp_data['value'] = prop_value
                                    # Value property의 위치와 각도도 저장
                                    for prop_item in item[3:]:
                                        if isinstance(prop_item, list) and len(prop_item) > 0:
                                            if str(prop_item[0]) == 'at':
                                                comp_data['value_at'] = parse_position(prop_item)
                                elif prop_name == 'Footprint':
                                    comp_data['footprint'] = prop_value
                    
                    # lib_id가 있고 유효한 컴포넌트만 추가
                    if comp_data and comp_data.get('lib_id'):
                        components.append(comp_data)
                    
            # 재귀적으로 탐색
            for item in node:
                if isinstance(item, list):
                    traverse(item)
    
    traverse(sexp_data)
    return components


def extract_wires_from_sexp(sexp_data):
    """S-expression에서 와이어 추출"""
    wires = []
    
    def traverse(node):
        if isinstance(node, list) and len(node) > 0:
            if isinstance(node[0], sexpdata.Symbol) and str(node[0]) == 'wire':
                wire_data = {}
                for item in node[1:]:
                    if isinstance(item, list) and len(item) > 0:
                        key = str(item[0]) if isinstance(item[0], sexpdata.Symbol) else None
                        if key == 'pts':
                            # pts 안에는 (xy x1 y1) (xy x2 y2) 형태
                            points = []
                            for pt in item[1:]:
                                if isinstance(pt, list) and str(pt[0]) == 'xy':
                                    points.append((float(pt[1]), float(pt[2])))
                            if len(points) >= 2:
                                wire_data['start'] = points[0]
                                wire_data['end'] = points[1]
                        elif key == 'uuid':
                            wire_data['uuid'] = str(item[1])
                
                if 'start' in wire_data and 'end' in wire_data:
                    wires.append(wire_data)
            
            # 재귀적으로 탐색
            for item in node:
                if isinstance(item, list):
                    traverse(item)
    
    traverse(sexp_data)
    return wires


def extract_junctions_from_sexp(sexp_data):
    """S-expression에서 정션 추출"""
    junctions = []
    
    def traverse(node):
        if isinstance(node, list) and len(node) > 0:
            if isinstance(node[0], sexpdata.Symbol) and str(node[0]) == 'junction':
                junction_data = {}
                for item in node[1:]:
                    if isinstance(item, list) and len(item) > 0:
                        key = str(item[0]) if isinstance(item[0], sexpdata.Symbol) else None
                        if key == 'at':
                            junction_data['position'] = parse_position(item)
                        elif key == 'uuid':
                            junction_data['uuid'] = str(item[1])
                
                if 'position' in junction_data:
                    junctions.append(junction_data)
            
            # 재귀적으로 탐색
            for item in node:
                if isinstance(item, list):
                    traverse(item)
    
    traverse(sexp_data)
    return junctions


def extract_labels_from_sexp(sexp_data):
    """S-expression에서 라벨 추출"""
    labels = []
    
    def traverse(node):
        if isinstance(node, list) and len(node) > 0:
            if isinstance(node[0], sexpdata.Symbol) and str(node[0]) == 'label':
                label_data = {}
                # 첫 번째 요소가 라벨 텍스트
                if len(node) > 1:
                    label_data['text'] = str(node[1])
                
                for item in node[1:]:
                    if isinstance(item, list) and len(item) > 0:
                        key = str(item[0]) if isinstance(item[0], sexpdata.Symbol) else None
                        if key == 'at':
                            label_data['position'] = parse_position(item)
                        elif key == 'uuid':
                            label_data['uuid'] = str(item[1])
                
                if 'text' in label_data and 'position' in label_data:
                    labels.append(label_data)
            
            # 재귀적으로 탐색
            for item in node:
                if isinstance(item, list):
                    traverse(item)
    
    traverse(sexp_data)
    return labels


def generate_component_code(comp: dict) -> str:
    """컴포넌트를 Python 코드로 변환"""
    lib_id = comp.get('lib_id', 'Device:Unknown')
    reference = comp.get('reference', 'REF?')
    value = comp.get('value', '')
    position = comp.get('position', (0.0, 0.0))
    footprint = comp.get('footprint', '')
    
    # reference가 비어있거나 ?로 끝나는 경우 처리
    if not reference or reference.endswith('?'):
        # ?를 제거하고 valid한 변수명으로 변환
        base_ref = reference.rstrip('?') if reference else 'COMP'
        reference = f"{base_ref}1"
    
    # 변수명 생성 (Python 변수명으로 valid하게)
    # #PWR1 → pwr_pwr1, #PWR1 (중복) → pwr_pwr1_1, pwr_pwr1_2 등으로 변환
    var_name = reference.lower().replace('#', 'pwr_').replace('?', 'x').replace('-', '_')
    
    # 변수명 중복 처리를 위한 카운터 (전역 변수 사용)
    if not hasattr(generate_component_code, 'var_counter'):
        generate_component_code.var_counter = {}
    
    if var_name in generate_component_code.var_counter:
        generate_component_code.var_counter[var_name] += 1
        unique_var_name = f"{var_name}_{generate_component_code.var_counter[var_name]}"
    else:
        generate_component_code.var_counter[var_name] = 0
        unique_var_name = var_name
    
    code = f'    # {reference}: {value}\n'
    code += f'    {unique_var_name} = sch.components.add(\n'
    code += f'        lib_id="{lib_id}",\n'
    code += f'        reference="{reference}",\n'
    code += f'        value="{value}",\n'
    code += f'        position=({position[0]:.2f}, {position[1]:.2f})'
    
    if footprint:
        code += f',\n        footprint="{footprint}"'
    
    code += '\n    )\n'
    
    return code


def generate_wire_code(wire: dict) -> str:
    """와이어를 Python 코드로 변환"""
    start = wire['start']
    end = wire['end']
    code = f'    sch.wires.add(start=({start[0]:.4f}, {start[1]:.4f}), end=({end[0]:.4f}, {end[1]:.4f}))\n'
    return code


def generate_junction_code(junction: dict) -> str:
    """정션을 Python 코드로 변환"""
    pos = junction['position']
    code = f'    sch.junctions.add(position=({pos[0]:.4f}, {pos[1]:.4f}))\n'
    return code


def generate_label_code(label: dict) -> str:
    """라벨을 Python 코드로 변환"""
    text = label['text']
    pos = label['position']
    # position이 (x, y) 또는 (x, y, angle) 형식일 수 있음
    if len(pos) == 2:
        code = f'    sch.labels.add(text="{text}", position=({pos[0]:.4f}, {pos[1]:.4f}))\n'
    else:
        code = f'    sch.labels.add(text="{text}", position=({pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.2f}))\n'
    return code


def convert_kicad_to_code(input_file: str, output_file: str):
    """KiCad 파일을 Python 코드로 변환"""
    print(f"Reading KiCad schematic: {input_file}")
    
    # S-expression 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Parsing S-expression data...")
    sexp_data = sexpdata.loads(content)
    
    # 모든 요소 추출
    print("Extracting components...")
    components = extract_components_from_sexp(sexp_data)
    print(f"  Found {len(components)} components")
    
    # Reference 중복 제거 및 invalid reference 처리
    reference_counter = {}
    for idx, comp in enumerate(components):
        ref = comp.get('reference', 'REF?')
        
        # ?로 끝나는 reference는 번호를 붙여서 유효하게 만듦
        if ref.endswith('?'):
            base_ref = ref.rstrip('?')
            if base_ref.startswith('#PWR'):
                # #PWR? → #PWR0001
                ref = f"#PWR{idx+1:04d}"
            else:
                # REF? → REF1
                ref = f"{base_ref}{idx+1}"
        
        if ref in reference_counter:
            reference_counter[ref] += 1
            # 중복된 reference를 고유하게 만듦
            new_ref = f"{ref}_{reference_counter[ref]}"
            comp['reference'] = new_ref
            comp['original_reference'] = ref
        else:
            reference_counter[ref] = 0
            comp['reference'] = ref
            comp['original_reference'] = ref
    
    print("Extracting wires...")
    wires = extract_wires_from_sexp(sexp_data)
    print(f"  Found {len(wires)} wires")
    
    print("Extracting junctions...")
    junctions = extract_junctions_from_sexp(sexp_data)
    print(f"  Found {len(junctions)} junctions")
    
    print("Extracting labels...")
    labels = extract_labels_from_sexp(sexp_data)
    print(f"  Found {len(labels)} labels")
    
    # Python 코드 생성
    code_lines = []
    code_lines.append('"""')
    code_lines.append(f'Generated from: {Path(input_file).name}')
    code_lines.append('KiCad schematic converted to Python code using kicad-sch-api')
    code_lines.append(f'Components: {len(components)}')
    code_lines.append(f'Wires: {len(wires)}')
    code_lines.append(f'Junctions: {len(junctions)}')
    code_lines.append(f'Labels: {len(labels)}')
    code_lines.append('')
    code_lines.append('Note: Duplicate references have been made unique for compatibility.')
    code_lines.append('      Original reference preserved in comments.')
    code_lines.append('"""')
    code_lines.append('')
    code_lines.append('import kicad_sch_api as ksa')
    code_lines.append('')
    code_lines.append('')
    code_lines.append('def create_schematic():')
    code_lines.append('    """회로도 생성"""')
    code_lines.append('    ')
    code_lines.append('    # Create schematic')
    code_lines.append('    sch = ksa.create_schematic("Converted Circuit")')
    code_lines.append('    ')
    
    # 컴포넌트 추가
    if components:
        code_lines.append('    # Add components')
        # var_counter를 사용하여 변수명 중복 방지
        var_counter = {}
        for component in components:
            var_base = component.get('reference', 'REF?').lower().replace('#', 'pwr_').replace('?', 'x').replace('-', '_')
            if var_base in var_counter:
                var_counter[var_base] += 1
                var_name = f"{var_base}_{var_counter[var_base]}"
            else:
                var_counter[var_base] = 0
                var_name = var_base
            
            lib_id = component.get('lib_id', 'Device:Unknown')
            reference = component.get('reference', 'REF?')
            original_ref = component.get('original_reference', reference)
            value = component.get('value', '')
            position = component.get('position', (0.0, 0.0, 0.0))
            footprint = component.get('footprint', '')
            unit = component.get('unit', 1)
            mirror = component.get('mirror', None)
            
            # 원본 reference가 다르면 주석에 표시
            if original_ref != reference:
                code_lines.append(f'    # {reference} (originally {original_ref}): {value}')
            else:
                code_lines.append(f'    # {reference}: {value}')
            
            # position이 (x, y) 또는 (x, y, angle) 형식일 수 있음
            if len(position) == 2:
                position = (position[0], position[1], 0.0)
            
            code_lines.append(f'    {var_name} = sch.components.add(')
            code_lines.append(f'        lib_id="{lib_id}",')
            code_lines.append(f'        reference="{reference}",')
            code_lines.append(f'        value="{value}",')
            code_lines.append(f'        position=({position[0]:.4f}, {position[1]:.4f}),')
            code_lines.append(f'        angle={position[2]:.1f},')
            code_lines.append(f'        unit={unit},')
            if mirror:
                code_lines.append(f'        mirror="{mirror}",')
            if footprint:
                code_lines.append(f'        footprint="{footprint}"')
            else:
                # 마지막 파라미터 뒤에 comma 제거
                last_line = code_lines[-1]
                if last_line.endswith(','):
                    code_lines[-1] = last_line[:-1]
            code_lines.append('    )')
            code_lines.append('')
    
    # 와이어 추가
    if wires:
        code_lines.append('    # Add wires')
        for wire in wires:
            start = wire['start']
            end = wire['end']
            code_lines.append(f'    sch.wires.add(start=({start[0]:.4f}, {start[1]:.4f}), end=({end[0]:.4f}, {end[1]:.4f}))')
            code_lines.append('')
    
    # 정션 추가
    if junctions:
        code_lines.append('    # Add junctions')
        for junction in junctions:
            pos = junction['position']
            code_lines.append(f'    sch.junctions.add(position=({pos[0]:.4f}, {pos[1]:.4f}))')
            code_lines.append('')
    
    # 라벨 추가
    if labels:
        code_lines.append('    # Add labels')
        for label in labels:
            text = label['text']
            # 빈 라벨은 제외
            if not text or text.strip() == '':
                continue
            pos = label['position']
            if len(pos) == 2:
                code_lines.append(f'    sch.labels.add(text="{text}", position=({pos[0]:.4f}, {pos[1]:.4f}))')
            else:
                code_lines.append(f'    sch.labels.add(text="{text}", position=({pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.2f}))')
            code_lines.append('')
    
    code_lines.append('    ')
    code_lines.append('    return sch')
    code_lines.append('')
    code_lines.append('')
    code_lines.append('if __name__ == "__main__":')
    code_lines.append('    # Create schematic')
    code_lines.append('    schematic = create_schematic()')
    code_lines.append('    ')
    code_lines.append('    # Save to file')
    code_lines.append('    output_file = "output_circuit.kicad_sch"')
    code_lines.append('    schematic.save(output_file)')
    code_lines.append('    print(f"Schematic saved to: {output_file}")')
    
    # 파일에 쓰기
    output_path = Path(output_file)
    output_path.write_text('\n'.join(code_lines), encoding='utf-8')
    
    print(f"\nPython code generated: {output_file}")
    print("Total elements extracted:")
    print(f"  - Components: {len(components)}")
    print(f"  - Wires: {len(wires)}")
    print(f"  - Junctions: {len(junctions)}")
    print(f"  - Labels: {len(labels)}")
    print(f"  - Total: {len(components) + len(wires) + len(junctions) + len(labels)}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python kicad_to_code.py <input.kicad_sch> <output.py>")
        print("\nExample:")
        print("  python kicad_to_code.py ./altium2kicad/DI.kicad_sch circuit_code.py")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    try:
        convert_kicad_to_code(input_file, output_file)
        print("\n✅ Conversion successful!")
        print("\n다음 단계:")
        print(f"1. {output_file} 파일을 LLM에 제공하여 회로도 분석")
        print("2. LLM이 수정한 코드를 받아서 다시 저장")
        print("3. python code_to_kicad.py <modified_code.py> <output.kicad_sch> 실행")
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
