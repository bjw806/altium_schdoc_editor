"""
HoneyPot 라이브러리를 Device 라이브러리로 변환하는 스크립트
Round-trip 테스트용
"""
import sys
from pathlib import Path


def convert_to_device_lib(input_file: str, output_file: str):
    """HoneyPot 라이브러리를 Device 표준 라이브러리로 변환"""
    
    # 파일 읽기
    content = Path(input_file).read_text(encoding='utf-8')
    
    # 모든 HoneyPot 라이브러리를 교체
    # CAP로 시작하는 것은 C로, 나머지는 R로 교체
    import re
    
    def replace_lib_id(match):
        lib_id = match.group(1)
        
        # GND or VCC power symbols
        if 'GND' in lib_id or 'GROUND' in lib_id:
            return 'lib_id="power:GND"'
        elif 'VCC' in lib_id or 'POWER' in lib_id:
            return 'lib_id="power:VCC"'
        # Capacitors
        elif 'CAP' in lib_id:
            return 'lib_id="Device:C"'
        # Everything else becomes resistor
        else:
            return 'lib_id="Device:R"'
    
    # lib_id="HoneyPot:..." or lib_id="altium2kicad-altium-import:..." 패턴을 찾아서 교체
    content = re.sub(r'lib_id="(HoneyPot:[^"]+)"', replace_lib_id, content)
    content = re.sub(r'lib_id="(altium2kicad-altium-import:[^"]+)"', replace_lib_id, content)
    
    # 파일 쓰기
    Path(output_file).write_text(content, encoding='utf-8')
    
    print(f"✅ Converted: {input_file} → {output_file}")
    print("   All custom libraries replaced with standard Device/power libraries")


def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_to_device_lib.py <input.py> <output.py>")
        print("\nExample:")
        print("  python convert_to_device_lib.py DI_complete.py DI_device.py")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    convert_to_device_lib(input_file, output_file)


if __name__ == "__main__":
    main()
