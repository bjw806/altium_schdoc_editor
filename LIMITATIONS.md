# Known Limitations and Workarounds

## 현재 제한사항

### OLE 파일 생성 이슈

현재 `DI_improved.SchDoc` 파일이 생성되지만 Altium Designer에서 열리지 않는 문제가 있습니다.

**원인:**
- Altium SchDoc 파일은 OLE (Object Linking and Embedding) compound document 형식
- OLE 파일은 복잡한 내부 구조 (FAT, Directory, Red-Black Tree 등)를 가지고 있음
- 현재 구현된 OLE Writer가 완전한 OLE 스펙을 따르지 못함
- 특히 디렉토리 트리 구조와 FAT 섹터 체인이 원본과 다름

**분석 기능:**
- ✅ SchDoc 파일 **파싱** - 완벽하게 작동
- ✅ 회로도 구조 **분석** - 완벽하게 작동
- ✅ 개선점 **식별** - 완벽하게 작동
- ✅ Python 객체로 **수정** - 완벽하게 작동
- ❌ 수정된 내용을 SchDoc 파일로 **저장** - 제한적

## 해결 방법

### 방법 1: 분석 보고서 활용 (권장)

분석 보고서를 참고하여 Altium Designer에서 수동으로 수정:

1. `DI_analysis_report.json` 확인
2. `회로도_분석_및_개선_보고서.md` 읽기
3. Altium Designer에서 원본 `DI.SchDoc` 열기
4. 보고서의 권장사항대로 수동 수정:
   - 누락된 52개 접속점 추가
   - 전원 심볼 정리
   - 문서화 추가

**장점:**
- 확실하게 작동
- Altium Designer의 네이티브 기능 사용
- 결과 검증 가능

### 방법 2: Python 스크립트로 프로그래밍 방식 수정

SchematicEditor API를 사용하여 회로도를 프로그래밍 방식으로 수정:

```python
from altium_editor import SchematicEditor

# 새로운 회로도 생성 (저장 없이 분석만)
editor = SchematicEditor()
editor.load("DI.SchDoc")

# 수정 작업
editor.add_junction(510, 590)  # 접속점 추가
editor.add_power_port(1000, 5000, "VCC")  # 전원 추가
# ... 등등

# 데이터는 메모리에 있으나, 파일로 저장은 제한적
```

**장점:**
- 자동화 가능
- 반복 작업에 유용
- 분석과 수정을 프로그래밍으로 제어

**단점:**
- 파일 저장 시 OLE 구조 문제로 Altium에서 열리지 않을 수 있음

### 방법 3: JSON으로 내보내기

회로도를 JSON으로 내보내서 분석:

```bash
python3 json_parser.py DI.SchDoc DI.json
```

**용도:**
- 외부 도구로 분석
- 버전 관리 (text-based)
- 다른 형식으로 변환

## 향후 개선 계획

### 단기 (구현 가능)

1. **OLE 패칭 개선**
   - 원본 파일의 OLE 구조를 그대로 유지
   - FileHeader 스트림만 바이너리 레벨에서 교체
   - 크기가 같은 경우에만 작동

2. **템플릿 기반 생성**
   - 원본 DI.SchDoc을 템플릿으로 사용
   - 스트림 데이터만 교체
   - FAT와 디렉토리는 재계산

### 중기 (복잡함)

1. **완전한 OLE Writer 구현**
   - Microsoft의 OLE 스펙 완전 준수
   - Red-Black Tree 디렉토리 구조
   - 올바른 FAT 섹터 체인
   - Mini-stream 지원

2. **다른 OLE 라이브러리 사용**
   - `pywin32` (Windows 전용)
   - `olefile` fork 및 수정
   - C++ OLE 라이브러리 Python binding

### 장기 (대안)

1. **Altium API 사용**
   - Altium Designer의 COM API
   - 직접 회로도 조작
   - 가장 확실한 방법

2. **다른 형식 지원**
   - Altium ASCII format 변환
   - KiCad 형식 변환
   - SVG/PDF 렌더링

## 현재 사용 가능한 기능

### ✅ 완전히 작동하는 기능

1. **파싱 및 분석**
   ```python
   from altium_parser import AltiumParser

   parser = AltiumParser()
   doc = parser.parse_file("DI.SchDoc")

   # 모든 정보에 접근 가능
   components = doc.get_components()
   wires = doc.get_wires()
   nets = doc.get_net_labels()
   ```

2. **상세 분석**
   ```python
   from analyze_and_improve import SchematicAnalyzer

   analyzer = SchematicAnalyzer(doc)
   issues, suggestions = analyzer.analyze()
   ```

3. **메모리 내 수정**
   ```python
   from altium_editor import SchematicEditor

   editor = SchematicEditor()
   editor.load("DI.SchDoc")

   # 수정 작업
   editor.add_component("LM358", 1000, 2000, "U1")
   editor.add_wire([(1000, 2000), (1500, 2000)])

   # 메모리에는 존재하지만 파일 저장은 제한적
   ```

4. **JSON 내보내기**
   ```python
   import json
   from altium_parser import AltiumParser

   parser = AltiumParser()
   doc = parser.parse_file("DI.SchDoc")

   # JSON으로 변환하여 분석
   data = {
       "components": [comp.library_reference for comp in doc.get_components()],
       "wires": len(doc.get_wires()),
       # ... 등등
   }
   ```

## 참고 자료

### 비교: 다른 Altium 파서들

| 프로젝트 | 읽기 | 쓰기 | 특징 |
|----------|------|------|------|
| **vadmium/python-altium** | ✅ | ❌ | SVG 렌더링 전용 |
| **a3ng7n/Altium-Schematic-Parser** | ✅ | ❌ | JSON 변환 전용 |
| **본 프로젝트 (altium_schdoc_editor)** | ✅ | ⚠️ | 완전한 파싱 + 제한적 쓰기 |

### OLE 형식 참고 문서

- [Microsoft OLE Compound Document Format](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-cfb/)
- [olefile 라이브러리 문서](https://olefile.readthedocs.io/)
- [Altium Binary File Format](https://github.com/vadmium/python-altium/blob/master/format.md)

## 결론

**현재 상태:**
- ✅ 완벽한 파싱 및 분석 기능
- ✅ 프로그래밍 방식 수정 가능
- ⚠️ 파일 저장은 제한적 (OLE 구조 문제)

**권장 사용 방법:**
1. Python으로 분석하여 이슈 식별
2. 분석 보고서 확인
3. Altium Designer에서 수동으로 수정

또는:

1. Python으로 완전히 새로운 회로도 생성
2. 저장은 제한적이지만 메모리 내 작업은 가능
3. JSON 내보내기로 데이터 공유

**향후 개선:**
OLE 파일 저장 기능은 지속적으로 개선 중이며,
완전한 OLE Writer 구현이 완료되면 모든 기능이 정상 작동할 것입니다.
