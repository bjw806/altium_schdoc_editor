"""
Python Code to KiCad Schematic Converter
=========================================
Python API 형식의 회로도 코드를 실행하여 .kicad_sch 파일로 export합니다.

사용법:
    python code_to_kicad.py circuit_code.py output.kicad_sch
"""

import sys
import importlib.util
import tempfile
import copy
from collections import defaultdict
from pathlib import Path

import sexpdata
import kicad_sch_api as ksa


CUSTOM_LIBRARY_VERSION = "20250114"


def load_circuit_from_file(python_file: str):
    """Python 파일에서 회로도 로드"""
    print(f"Loading circuit code from: {python_file}")
    
    # Python 파일을 모듈로 로드
    spec = importlib.util.spec_from_file_location("circuit_module", python_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {python_file}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # create_schematic 함수 찾기
    if not hasattr(module, 'create_schematic'):
        raise AttributeError(
            f"Module {python_file} does not have a 'create_schematic' function"
        )
    
    # lib_symbols 데이터 확인
    lib_symbols_sexp = None
    if hasattr(module, 'LIB_SYMBOLS_SEXP'):
        lib_symbols_sexp = module.LIB_SYMBOLS_SEXP
        print("  Found custom lib_symbols data")
        prepare_custom_symbol_libraries(lib_symbols_sexp)
    
    # other_elements 데이터 확인
    other_elements = None
    if hasattr(module, 'OTHER_ELEMENTS'):
        other_elements = module.OTHER_ELEMENTS
        print(f"  Found {len(other_elements)} other elements to preserve")
    
    # 회로도 생성
    schematic = module.create_schematic()
    
    return schematic, lib_symbols_sexp, other_elements


def export_to_kicad(schematic, output_file: str, lib_symbols_sexp=None, other_elements=None):
    """회로도를 KiCad 파일로 export"""
    print(f"Exporting to KiCad schematic: {output_file}")
    
    # KiCad 파일로 저장
    schematic.save(output_file)
    
    # lib_symbols가 있으면 KiCad 파일에 삽입
    if lib_symbols_sexp:
        print("  Inserting custom lib_symbols...")
        insert_lib_symbols(output_file, lib_symbols_sexp)
    
    # other_elements가 있으면 KiCad 파일에 삽입
    if other_elements:
        print(f"  Inserting {len(other_elements)} other elements...")
        insert_other_elements(output_file, other_elements)
    
    print(f"✅ Successfully exported to: {output_file}")


def insert_lib_symbols(kicad_file: str, lib_symbols_sexp: str):
    """KiCad 파일에 lib_symbols 삽입"""
    # KiCad 파일 읽기
    with open(kicad_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # S-expression 파싱
    sexp_data = sexpdata.loads(content)
    
    # lib_symbols 파싱
    custom_lib_symbols = sexpdata.loads(lib_symbols_sexp.strip())
    
    # 기존 lib_symbols 찾아서 교체
    if isinstance(sexp_data, list):
        for i, item in enumerate(sexp_data):
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol) and str(item[0]) == 'lib_symbols':
                    # 기존 lib_symbols를 custom으로 교체
                    sexp_data[i] = custom_lib_symbols
                    break
        else:
            # lib_symbols가 없으면 추가 (kicad_sch 다음에)
            sexp_data.insert(7, custom_lib_symbols)  # paper 다음 위치
    
    # 다시 S-expression 문자열로 변환
    new_content = sexpdata.dumps(sexp_data)
    
    # 파일에 쓰기
    with open(kicad_file, 'w', encoding='utf-8') as f:
        f.write(new_content)


def insert_other_elements(kicad_file: str, other_elements: list):
    """KiCad 파일에 other elements (bus, no_connect, etc.) 삽입"""
    # KiCad 파일 읽기
    with open(kicad_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # S-expression 파싱
    sexp_data = sexpdata.loads(content)
    
    # other_elements를 S-expression으로 파싱하여 삽입
    if isinstance(sexp_data, list):
        # lib_symbols 뒤에 삽입 (또는 적절한 위치 찾기)
        insert_index = None
        for i, item in enumerate(sexp_data):
            if isinstance(item, list) and len(item) > 0:
                if isinstance(item[0], sexpdata.Symbol) and str(item[0]) == 'lib_symbols':
                    insert_index = i + 1
                    break
        
        if insert_index is None:
            # lib_symbols를 못 찾으면 paper 다음에 삽입
            for i, item in enumerate(sexp_data):
                if isinstance(item, list) and len(item) > 0:
                    if isinstance(item[0], sexpdata.Symbol) and str(item[0]) == 'paper':
                        insert_index = i + 1
                        break
        
        if insert_index is not None:
            # 각 other_element를 파싱해서 삽입
            for elem_sexp_str in other_elements:
                try:
                    elem = sexpdata.loads(elem_sexp_str.strip())
                    sexp_data.insert(insert_index, elem)
                    insert_index += 1
                except Exception as e:
                    print(f"  Warning: Failed to parse other element: {e}")
    
    # 다시 S-expression 문자열로 변환
    new_content = sexpdata.dumps(sexp_data)
    
    # 파일에 쓰기
    with open(kicad_file, 'w', encoding='utf-8') as f:
        f.write(new_content)


def prepare_custom_symbol_libraries(lib_symbols_sexp: str):
    """lib_symbols 정의를 임시 KiCad 라이브러리로 변환하여 로드."""
    if not lib_symbols_sexp:
        return []

    try:
        parsed = sexpdata.loads(lib_symbols_sexp.strip())
    except Exception as exc:  # pragma: no cover - defensive logging only
        print(f"  Warning: Failed to parse LIB_SYMBOLS_SEXP: {exc}")
        return []

    if not parsed or not isinstance(parsed, list) or str(parsed[0]) != 'lib_symbols':
        print("  Warning: Unexpected lib_symbols format; skipping custom library generation")
        return []

    libraries = defaultdict(list)

    for entry in parsed[1:]:
        if not isinstance(entry, list) or len(entry) < 2:
            continue

        raw_name = entry[1]
        if isinstance(raw_name, sexpdata.Symbol):
            raw_name = str(raw_name)

        if not isinstance(raw_name, str) or ':' not in raw_name:
            continue

        library_name, symbol_name = raw_name.split(':', 1)
        symbol_entry = _normalize_symbol_entry(entry, symbol_name)
        libraries[library_name].append(symbol_entry)

    if not libraries:
        return []

    temp_dir = Path(tempfile.mkdtemp(prefix="kicad_sym_"))
    created_paths = []

    for library_name, symbols in libraries.items():
        library_path = temp_dir / f"{library_name}.kicad_sym"
        try:
            library_content = _build_symbol_library_content(symbols)
            library_path.write_text(library_content, encoding='utf-8')
        except Exception as exc:  # pragma: no cover - defensive logging only
            print(f"  Warning: Could not write library {library_name}: {exc}")
            continue

        created_paths.append(library_path)

    if not created_paths:
        return []

    cache = ksa.get_symbol_cache()
    for library_path in created_paths:
        cache.add_library_path(library_path)

    print(f"  Registered {len(created_paths)} custom symbol library files")
    return created_paths


def _normalize_symbol_entry(entry, local_symbol_name: str):
    """Remove 라이브러리 prefix가 포함된 심볼 이름을 정규화."""
    symbol_entry = copy.deepcopy(entry)

    if isinstance(symbol_entry[1], sexpdata.Symbol):
        symbol_entry[1] = sexpdata.Symbol(local_symbol_name)
    else:
        symbol_entry[1] = local_symbol_name

    for idx in range(2, len(symbol_entry)):
        item = symbol_entry[idx]
        if (
            isinstance(item, list)
            and item
            and item[0] == sexpdata.Symbol('symbol')
            and len(item) > 1
        ):
            nested_name = item[1]
            if isinstance(nested_name, sexpdata.Symbol):
                nested_name = str(nested_name)

            if isinstance(nested_name, str) and ':' in nested_name:
                local_name = nested_name.split(':', 1)[1]
                item[1] = sexpdata.Symbol(local_name) if isinstance(item[1], sexpdata.Symbol) else local_name

    return symbol_entry


def _build_symbol_library_content(symbols):
    """Generate KiCad symbol library S-expression 텍스트."""
    lines = ["(kicad_symbol_lib", f"\t(version {CUSTOM_LIBRARY_VERSION})", '\t(generator "altium_schdoc_editor")']
    lines.append('\t(generator_version "1.0")')

    for symbol in symbols:
        lines.append('\t' + sexpdata.dumps(symbol))

    lines.append(')')
    return '\n'.join(lines) + '\n'


def main():
    if len(sys.argv) < 3:
        print("Usage: python code_to_kicad.py <circuit_code.py> <output.kicad_sch>")
        print("\nExample:")
        print("  python code_to_kicad.py circuit_code.py modified_circuit.kicad_sch")
        sys.exit(1)
    
    python_path = Path(sys.argv[1])
    output_candidate = Path(sys.argv[2])

    if not python_path.exists():
        print(f"Error: Python file not found: {python_path}")
        sys.exit(1)

    if len(output_candidate.parts) == 1:
        output_path = Path("schematics") / output_candidate
    else:
        output_path = output_candidate

    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Python 코드에서 회로도 로드
        schematic, lib_symbols_sexp, other_elements = load_circuit_from_file(str(python_path))
        
        # KiCad 파일로 export
        export_to_kicad(schematic, str(output_path), lib_symbols_sexp, other_elements)
        
        print("\n다음 단계:")
        print(f"1. KiCad에서 {output_path} 파일을 열어서 확인")
        print("2. 필요하면 Altium Designer로 import")
        
    except Exception as e:
        print(f"Error during export: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
