## 명령어

### KiCad → Python 코드

```powershell
python kicad_to_code.py input.kicad_sch output.py
```

### Python 코드 → KiCad

```powershell
python code_to_kicad.py circuit_code.py output.kicad_sch
```


## 주요 기능

- `kicad_to_code.py`: KiCad 회로도를 파싱해 Python 코드로 변환하며 `lib_symbols` 블록을 그대로 포함.
- `code_to_kicad.py`: Python 코드를 실행해 KiCad 파일을 생성하고, `LIB_SYMBOLS_SEXP`가 있으면 임시 `.kicad_sym` 라이브러리를 만들어 `kicad_sch_api` 캐시에 등록한 뒤 저장.
- `code_to_kicad.py`는 필요 시 `lib_symbols`를 최종 `.kicad_sch`에 다시 삽입.


## 워크플로

```
.kicad_sch ── kicad_to_code.py ──> circuit.py ──(LLM 수정)──> modified.py ── code_to_kicad.py ──> output.kicad_sch
```


## 커스텀 라이브러리 처리

- `kicad_to_code.py`가 추출한 `LIB_SYMBOLS_SEXP`는 생성된 Python 코드에 문자열로 포함.
- `code_to_kicad.py`는 해당 문자열을 파싱해 라이브러리별 `.kicad_sym` 파일을 임시 디렉터리에 생성.
- 생성된 파일은 실행 중인 `kicad_sch_api` 심볼 캐시에 등록되어 HoneyPot 등 커스텀 심볼을 바로 사용할 수 있음.
- 내보낸 `.kicad_sch`에는 원본 `lib_symbols`가 그대로 유지.


## 알려진 제한 사항

1. 포지셔닝 규칙이 없는 커스텀 심볼은 기본 패턴으로 배치.
2. 동일한 Reference 명칭은 자동으로 고유 이름이 되며 주석에 원본 보존.
3. 빈 라벨은 KiCad API 제약으로 무시.

### KiCad 라이브러리 경로 설정
```powershell
# Windows
$env:KICAD_SYMBOL_DIR = "C:\Program Files\KiCad\share\kicad\symbols"

# Linux/Mac
export KICAD_SYMBOL_DIR=/usr/share/kicad/symbols
```


## 참고 리포지토리

- [kicad-sch-api](https://github.com/circuit-synth/kicad-sch-api)
- [circuit-synth](https://github.com/circuit-synth/circuit-synth)