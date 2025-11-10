"""
Python Code to KiCad Schematic Converter
=========================================
Python API 형식의 회로도 코드를 실행하여 .kicad_sch 파일로 export합니다.

사용법:
    python code_to_kicad.py circuit_code.py output.kicad_sch
"""

import sys
import importlib.util
from pathlib import Path


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
    
    # 회로도 생성
    schematic = module.create_schematic()
    
    return schematic


def export_to_kicad(schematic, output_file: str):
    """회로도를 KiCad 파일로 export"""
    print(f"Exporting to KiCad schematic: {output_file}")
    
    # KiCad 파일로 저장
    schematic.save(output_file)
    
    print(f"✅ Successfully exported to: {output_file}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python code_to_kicad.py <circuit_code.py> <output.kicad_sch>")
        print("\nExample:")
        print("  python code_to_kicad.py circuit_code.py modified_circuit.kicad_sch")
        sys.exit(1)
    
    python_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(python_file).exists():
        print(f"Error: Python file not found: {python_file}")
        sys.exit(1)
    
    try:
        # Python 코드에서 회로도 로드
        schematic = load_circuit_from_file(python_file)
        
        # KiCad 파일로 export
        export_to_kicad(schematic, output_file)
        
        print("\n다음 단계:")
        print(f"1. KiCad에서 {output_file} 파일을 열어서 확인")
        print("2. 필요하면 Altium Designer로 import")
        
    except Exception as e:
        print(f"Error during export: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
