# KiCad 회로도 ↔ Python 코드 변환 도구

KiCad 회로도 파일(.kicad_sch)과 Python 코드 간 양방향 변환을 지원하는 도구입니다.
LLM을 활용한 회로도 분석 및 수정 워크플로우를 제공합니다.

## ✨ 주요 기능

- 🔄 **양방향 변환**: KiCad ↔ Python 코드
  - ✅ Components (100% 보존)
  - ✅ Wires (100% 보존)
  - ✅ Junctions (100% 보존)
  - ✅ Labels (97.4% 보존, 빈 라벨 제외)
- 🤖 **LLM 통합**: Python 코드로 변환하여 LLM 분석 가능
- 📝 **자동 코드 생성**: 회로도를 readable한 Python 코드로
- 🔧 **MCP 서버**: AI 에이전트가 직접 회로도 조작 가능
- ✅ **Round-trip 검증**: DI.kicad_sch (12,043 lines) 테스트 완료
  - 29 components, 202 wires, 58 junctions, 38 labels
  - 99.7% 요소 보존 (327/328 요소)

## 📦 설치

```powershell
# 필요한 패키지 설치
pip install -r requirements.txt
```

**설치되는 패키지:**
- `olefile` - Altium 파일 파싱용
- `kicad-sch-api` - KiCad 회로도 API
- `mcp-kicad-sch-api` - MCP 서버
- `sexpdata` - S-expression 파서

## 🚀 빠른 시작

### 1. KiCad → Python 코드

```powershell
python kicad_to_code.py input.kicad_sch output.py
```

### 2. Python 코드 → KiCad

```powershell
python code_to_kicad.py circuit_code.py output.kicad_sch
```

### 3. 테스트 예제

```powershell
# 간단한 LED 회로 생성
python simple_example.py

# 변환 테스트
python kicad_to_code.py simple_led_circuit.kicad_sch test.py
python code_to_kicad.py test.py roundtrip.kicad_sch
```

## 📖 사용 예제

### 예제 1: 기본 변환

```powershell
# DI.kicad_sch를 Python 코드로 변환
python kicad_to_code.py ./altium2kicad/DI.kicad_sch circuit.py

# 생성된 circuit.py 확인
# - 컴포넌트 목록
# - 위치 정보
# - lib_id, reference, value, footprint 등
```

### 예제 2: LLM 분석 워크플로우

1. **변환**: KiCad → Python
   ```powershell
   python kicad_to_code.py my_circuit.kicad_sch circuit.py
   ```

2. **분석**: circuit.py를 LLM에 제공
   - "이 회로의 주요 컴포넌트는?"
   - "전원 회로 부분을 분석해줘"
   - "개선할 수 있는 부분은?"

3. **수정**: LLM이 수정한 코드를 modified.py로 저장

4. **Export**: Python → KiCad
   ```powershell
   python code_to_kicad.py modified.py output.kicad_sch
   ```

### 예제 3: 생성된 Python 코드 구조

```python
import kicad_sch_api as ksa

def create_schematic():
    """회로도 생성"""
    
    # Create schematic
    sch = ksa.create_schematic("Converted Circuit")
    
    # Add components
    # R1: 220R
    r1 = sch.components.add(
        lib_id="Device:R",
        reference="R1",
        value="220R",
        position=(100.33, 100.33)
    )

    # LED1: RED
    led1 = sch.components.add(
        lib_id="Device:LED",
        reference="LED1",
        value="RED",
        position=(119.38, 100.33)
    )
    
    return sch

if __name__ == "__main__":
    schematic = create_schematic()
    schematic.save("output_circuit.kicad_sch")
```

## 🔧 MCP 서버 설정

### Claude Desktop

`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "kicad-sch-api": {
      "command": "python",
      "args": ["-m", "mcp_kicad_sch_api"],
      "env": {}
    }
  }
}
```

### 사용 가능한 MCP 도구

1. `create_schematic` - 새 회로도 생성
2. `add_component` - 컴포넌트 추가
3. `search_components` - KiCad 심볼 검색
4. `add_wire` - 와이어 연결
5. `list_components` - 컴포넌트 목록
6. `get_schematic_info` - 회로도 정보

## 📂 프로젝트 구조

```
altium_schdoc_editor/
├── kicad_to_code.py          # KiCad → Python 변환기
├── code_to_kicad.py          # Python → KiCad 변환기
├── simple_example.py         # 간단한 LED 회로 예제
├── requirements.txt          # 패키지 의존성
├── WORKFLOW_README.md        # 상세 워크플로우 가이드
├── README.md                 # 이 파일
└── altium2kicad/
    └── DI.kicad_sch         # 테스트용 회로도 파일
```

## 🎯 주요 파일 설명

### kicad_to_code.py
- KiCad 회로도를 Python 코드로 변환
- S-expression 파서 사용
- 컴포넌트, 와이어, 라벨 추출

### code_to_kicad.py
- Python 코드를 실행하여 KiCad 파일 생성
- kicad-sch-api 사용
- 자동으로 reference 번호 할당

### simple_example.py
- 간단한 LED 회로 생성 예제
- 워크플로우 테스트용
- 학습 자료

## 🔄 워크플로우 다이어그램

```
┌─────────────┐
│ .kicad_sch  │ ─┐
└─────────────┘  │ kicad_to_code.py
                 ▼
┌─────────────┐
│ circuit.py  │ ─┐
└─────────────┘  │ LLM 분석
                 ▼
┌─────────────┐
│ modified.py │ ─┐
└─────────────┘  │ code_to_kicad.py
                 ▼
┌─────────────┐
│ output.     │
│ kicad_sch   │
└─────────────┘
```

## ⚠️ 알려진 제한사항

1. **커스텀 라이브러리**: HoneyPot 등 커스텀 라이브러리는 지원 안 됨
   - 해결: `convert_to_device_lib.py`로 표준 라이브러리 변환

2. **중복 Reference**: 동일한 reference는 자동으로 번호 추가
   - 예: #PWR1 → #PWR1, #PWR1_1, #PWR1_2...
   - 주석에 원본 reference 기록

3. **빈 라벨**: KiCad API 제약으로 빈 라벨 제외됨 (영향 극소)

4. **lib_symbols**: Custom 라이브러리 심볼 정의는 아직 추출되지 않음

## 📊 테스트 결과

### Simple LED Circuit
- ✅ 2 components
- ✅ 4 wires
- ✅ Round-trip 100% 성공

### DI.kicad_sch (복잡한 회로)
- ✅ 29 components
- ✅ 202 wires
- ✅ 58 junctions
- ✅ 38 labels (빈 라벨 1개 제외)
- ✅ Round-trip 99.7% 성공 (327/328 요소)

자세한 내용은 [ROUNDTRIP_TEST_RESULTS.md](ROUNDTRIP_TEST_RESULTS.md) 참조

## 🐛 문제 해결

### "kicad-sch-api를 찾을 수 없음"
```powershell
pip install kicad-sch-api
```

### "sexpdata를 찾을 수 없음"
```powershell
pip install sexpdata
```

### "Symbol not found in KiCAD libraries"
- 표준 KiCad 라이브러리의 심볼로 변경
- 또는 커스텀 라이브러리 경로 설정

### KiCad 라이브러리 경로 설정
```powershell
# Windows
$env:KICAD_SYMBOL_DIR = "C:\Program Files\KiCad\share\kicad\symbols"

# Linux/Mac
export KICAD_SYMBOL_DIR=/usr/share/kicad/symbols
```

## 📚 추가 문서

- [WORKFLOW_README.md](WORKFLOW_README.md) - 상세한 워크플로우 가이드
- [kicad-sch-api 문서](https://github.com/circuit-synth/kicad-sch-api)
- [circuit-synth 문서](https://github.com/circuit-synth/circuit-synth)

## 🤝 기여

기여는 언제나 환영합니다!

1. Fork the project
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 라이센스

MIT License - 자유롭게 사용 가능

## 🙏 감사

- [kicad-sch-api](https://github.com/circuit-synth/kicad-sch-api) - KiCad 파일 처리
- [circuit-synth](https://github.com/circuit-synth/circuit-synth) - 회로 설계 도구
- [KiCad](https://www.kicad.org/) - 오픈소스 EDA 도구

---

**Made with ❤️ for circuit design automation**
