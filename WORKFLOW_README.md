# KiCad 회로도 분석 및 수정 워크플로우

이 프로젝트는 KiCad 회로도 파일(.kicad_sch)을 Python 코드로 변환하고, LLM을 통해 분석 및 수정 후 다시 KiCad 형식으로 export하는 워크플로우를 제공합니다.

## 📋 목차

1. [설치](#설치)
2. [워크플로우 개요](#워크플로우-개요)
3. [사용법](#사용법)
4. [MCP 서버 설정](#mcp-서버-설정)
5. [예제](#예제)

## 🔧 설치

### 1. 필요한 패키지 설치

```powershell
pip install -r requirements.txt
```

### 2. 설치되는 패키지
- `olefile` - Altium 파일 파싱용
- `kicad-sch-api` - KiCad 회로도 파일 처리용 Python API
- `mcp-kicad-sch-api` - Model Context Protocol 서버

## 🔄 워크플로우 개요

```
┌─────────────────┐
│  .kicad_sch     │  ← KiCad 회로도 파일
│  (입력)         │
└────────┬────────┘
         │
         │ kicad_to_code.py
         ▼
┌─────────────────┐
│  circuit.py     │  ← Python API 코드
│  (회로도 코드)  │
└────────┬────────┘
         │
         │ LLM에 전달하여 분석
         │
         ▼
┌─────────────────┐
│  LLM 분석       │  ← 회로도 분석 및 수정
│  & 코드 수정    │     (사용자가 직접 수행)
└────────┬────────┘
         │
         │ 수정된 코드 저장
         ▼
┌─────────────────┐
│  modified.py    │  ← 수정된 Python 코드
│  (수정된 코드)  │
└────────┬────────┘
         │
         │ code_to_kicad.py
         ▼
┌─────────────────┐
│  output.kicad_  │  ← KiCad 회로도 파일
│  sch (출력)     │
└─────────────────┘
         │
         │ KiCad에서 열기
         ▼
┌─────────────────┐
│  KiCad Editor   │  ← 결과 확인
│                 │     필요시 Altium으로 import
└─────────────────┘
```

## 📖 사용법

### 1단계: KiCad → Python 코드 변환

```powershell
python kicad_to_code.py <input.kicad_sch> <output.py>
```

**예제:**
```powershell
python kicad_to_code.py ./altium2kicad/DI.kicad_sch circuit_code.py
```

**출력:**
- `circuit_code.py` - 회로도를 Python API 형식으로 변환한 코드
- 컴포넌트, 와이어, 라벨, 정션 정보 포함

### 2단계: LLM 분석 (수동)

생성된 `circuit_code.py` 파일을:
1. LLM(ChatGPT, Claude 등)에 제공
2. 회로도 분석 요청
3. 필요한 수정사항 반영
4. 수정된 코드를 새 파일로 저장

**분석 예시 프롬프트:**
```
이 회로도 코드를 분석해주세요:
- 사용된 컴포넌트 목록
- 주요 회로 블록
- 개선 가능한 부분
- 추가해야 할 컴포넌트
```

### 3단계: Python 코드 → KiCad 변환

```powershell
python code_to_kicad.py <modified_code.py> <output.kicad_sch>
```

**예제:**
```powershell
python code_to_kicad.py modified_circuit.py output.kicad_sch
```

**출력:**
- `output.kicad_sch` - 수정된 회로도 KiCad 파일

### 4단계: KiCad에서 확인

```powershell
# KiCad 에서 파일 열기
kicad output.kicad_sch
```

또는 KiCad 프로그램을 직접 실행하여 파일을 엽니다.

## 🤖 MCP 서버 설정

MCP(Model Context Protocol) 서버를 사용하면 AI 에이전트가 KiCad 회로도를 직접 조작할 수 있습니다.

### Claude Desktop 설정

`claude_desktop_config.json` 파일에 추가:

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

1. **create_schematic** - 새 회로도 생성
2. **add_component** - 컴포넌트 추가
3. **search_components** - KiCad 심볼 라이브러리 검색
4. **add_wire** - 와이어 연결 생성
5. **add_hierarchical_sheet** - 계층적 시트 추가
6. **add_sheet_pin** - 시트 핀 추가
7. **add_hierarchical_label** - 계층적 라벨 추가
8. **list_components** - 모든 컴포넌트 목록
9. **get_schematic_info** - 회로도 정보 조회

## 📝 예제

### 예제 1: 기본 워크플로우

```powershell
# 1. KiCad 파일을 Python 코드로 변환
python kicad_to_code.py ./altium2kicad/DI.kicad_sch circuit.py

# 2. circuit.py를 LLM에 제공하여 분석 및 수정
#    (수동으로 LLM과 상호작용)

# 3. 수정된 코드를 KiCad 파일로 변환
python code_to_kicad.py modified_circuit.py output.kicad_sch

# 4. KiCad에서 확인
kicad output.kicad_sch
```

### 예제 2: 생성된 Python 코드 구조

```python
"""
Generated from: DI.kicad_sch
KiCad schematic converted to Python code using kicad-sch-api
"""

import kicad_sch_api as ksa


def create_schematic():
    """회로도 생성"""
    
    # Create schematic
    sch = ksa.create_schematic("Converted Circuit")
    
    # Add components
    # U1: MCP23017
    u1 = sch.components.add(
        lib_id="Interface_Expansion:MCP23017",
        reference="U1",
        value="MCP23017",
        position=(100.00, 100.00),
        footprint="Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm"
    )
    
    # R1: 10k
    r1 = sch.components.add(
        lib_id="Device:R",
        reference="R1",
        value="10k",
        position=(120.00, 100.00),
        footprint="Resistor_SMD:R_0603_1608Metric"
    )
    
    return sch


if __name__ == "__main__":
    schematic = create_schematic()
    schematic.save("output_circuit.kicad_sch")
    print(f"Schematic saved to: output_circuit.kicad_sch")
```

## 🔗 관련 링크

- [kicad-sch-api GitHub](https://github.com/circuit-synth/kicad-sch-api)
- [circuit-synth GitHub](https://github.com/circuit-synth/circuit-synth)
- [mcp-kicad-sch-api GitHub](https://github.com/circuit-synth/mcp-kicad-sch-api)
- [KiCad 공식 웹사이트](https://www.kicad.org/)

## ⚠️ 주의사항

1. **중복 Reference**: 동일한 reference를 가진 컴포넌트는 자동으로 "_X"로 변환됩니다.
2. **Library 경로**: KiCad 심볼 라이브러리 경로가 올바르게 설정되어 있어야 합니다.
3. **백업**: 원본 파일은 항상 백업하세요.
4. **검증**: 변환 후 반드시 KiCad에서 회로도를 열어 확인하세요.

## 🐛 문제 해결

### kicad-sch-api를 찾을 수 없음

```powershell
pip install kicad-sch-api
```

### sexpdata를 찾을 수 없음

```powershell
pip install sexpdata
```

### KiCad 라이브러리 경로 설정

Windows 환경 변수 설정:
```powershell
$env:KICAD_SYMBOL_DIR = "C:\Program Files\KiCad\share\kicad\symbols"
```

## 📄 라이센스

MIT License - 자유롭게 사용 가능

## 👥 기여

기여는 언제나 환영합니다! Issue나 Pull Request를 통해 참여해주세요.
