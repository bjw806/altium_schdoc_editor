# DI.schdoc 회로도 분석 및 개선 제안

## 🔍 회로 분석 결과

### 회로 개요
**16채널 디지털 입력 모듈 (Digital Input Module)**

이 회로는 MCP23017 I2C I/O 확장 IC와 포토커플러를 사용한 절연 디지털 입력 회로입니다.

---

## 📊 컴포넌트 구성

### 주요 부품

| 부품명 | 수량 | 용도 |
|--------|------|------|
| **MCP23017** | 1개 | 16비트 I2C I/O 확장 IC |
| **TLP281-4** | 4개 | 4채널 포토커플러 (총 16채널) |
| **RES-2** | 16개 | 전류제한 저항 |
| **10KR2F** | 1개 | 풀업/풀다운 저항 네트워크 |
| **커넥터** | 2개 | 입력 및 I2C 연결 |

---

## 🔌 회로 동작 원리

### 1. 입력 신호 경로
```
외부 입력 신호 (DI0~DI15)
    ↓
[입력 커넥터] → [전류제한 저항] → [TLP281 LED]
    ↓
[TLP281 Phototransistor] → [MCP23017 입력 핀]
    ↓
I2C 버스 (SCL, SDA) → 마이크로컨트롤러
```

### 2. 절연 기능
- **포토커플러(TLP281-4)**: 입력과 회로 간 전기적 절연
- 각 채널 독립적으로 절연되어 노이즈 및 전압 서지로부터 보호

### 3. I2C 통신
- **MCP23017**: I2C 슬레이브 디바이스
- 16개 GPIO 핀 (GPIOA: GPA0-GPA7, GPIOB: GPB0-GPB7)
- 주소 설정 가능 (A0, A1, A2 핀)

---

## 📋 네트워크 분석

### 주요 신호
- **DI0 ~ DI15**: 16개 디지털 입력 신호
- **GND**: 그라운드 (6개 위치)
- **VCC**: 전원 (현재 누락 - 추가 필요!)
- **SCL, SDA**: I2C 통신 신호 (라벨 필요)

### 전원 분석
- ✅ **GND**: 6개 위치에서 연결
- ⚠️ **VCC**: 회로에 전원 심볼 누락 → **추가 필요**

---

## 💡 개선 제안

### 🔴 HIGH 우선순위

#### 1. VCC 전원 포트 추가
**문제**: VCC 전원 심볼이 회로도에 명시되지 않음

**해결**:
```
추가 위치: MCP23017 VDD 핀 근처
심볼: VCC (Arrow 스타일)
```

#### 2. I2C 풀업 저항 추가
**문제**: I2C 신호(SCL, SDA)에 풀업 저항 없음

**해결**:
```
부품: 4.7kΩ 저항 2개
연결: SCL → 4.7k → VCC
      SDA → 4.7k → VCC
```

#### 3. I2C 신호 라벨 추가
**문제**: SCL, SDA 신호 라벨이 명확하지 않음

**해결**:
```
추가 라벨:
  - SCL (I2C Clock)
  - SDA (I2C Data)
색상: 빨간색 (중요 신호 강조)
```

---

### 🟡 MEDIUM 우선순위

#### 4. 디커플링 캐패시터 권장
**문제**: IC 전원 핀에 디커플링 캐패시터 명시 없음

**권장사항**:
```
부품: 100nF 세라믹 캐패시터
위치: 각 IC VDD 핀 가까이
연결: VDD → 100nF → GND

추가 위치:
  - MCP23017 VDD 핀 (1개)
  - 각 TLP281-4 VCC 핀 (4개)
```

#### 5. 회로도 문서화
**문제**: 제목, 날짜, 설명 누락

**추가 내용**:
```
제목: "16-Channel Digital Input Module (DI)"
설명: "MCP23017 I2C I/O Expander with Optocoupled Inputs"
날짜: "Rev 1.1 | 2025-11-10"
노트:
  - "Add 100nF decoupling caps near each IC"
  - "4.7k pullup resistors required for I2C (SCL, SDA to VCC)"
```

---

### 🟢 LOW 우선순위

#### 6. 테스트 포인트 추가
**권장사항**:
```
주요 신호에 테스트 포인트 표시:
  - TP1: SCL
  - TP2: SDA
  - TP3: VCC
  - TP4: GND
```

#### 7. 회로 보호 소자
**추천**:
```
- TVS 다이오드: 입력단 ESD 보호
- 퓨즈: 전원 보호
```

---

## ✅ 적용된 개선사항

다음 항목들이 회로도에 추가되었습니다:

### 문서화
- ✅ 제목: "16-Channel Digital Input Module (DI)"
- ✅ 설명: "MCP23017 I2C I/O Expander with Optocoupled Inputs"
- ✅ 버전: "Rev 1.1 | Modified: 2025-11-10"

### 신호 라벨
- ✅ I2C 신호 라벨: SCL, SDA (빨간색)
- ✅ 신호 설명: (I2C Clock), (I2C Data)

### 전원
- ✅ VCC 전원 포트 추가 (위치: 7500, 5000)

### 엔지니어링 노트
- ✅ "Add 100nF decoupling caps near each IC"
- ✅ "4.7k pullup resistors required for I2C (SCL, SDA to VCC)"

---

## 🔧 실제 구현 시 체크리스트

### 하드웨어 조립 전
- [ ] MCP23017 주소 설정 (A0, A1, A2)
- [ ] 4.7kΩ I2C 풀업 저항 연결
- [ ] 100nF 디커플링 캐패시터 각 IC에 설치
- [ ] VCC 전원 공급 확인 (3.3V 또는 5V)

### 소프트웨어 설정
- [ ] I2C 주소 확인 (기본: 0x20)
- [ ] I2C 속도 설정 (100kHz or 400kHz)
- [ ] MCP23017 레지스터 초기화
  - IODIR: 모두 입력(0xFF)
  - GPPU: 풀업 활성화 필요 시

### 테스트
- [ ] 전원 전압 측정 (VCC, GND)
- [ ] I2C 통신 확인 (스캔)
- [ ] 각 채널 입력 테스트 (DI0~DI15)
- [ ] 절연 확인 (포토커플러)

---

## 📐 회로 특성

### 전기적 특성
- **입력 전압**: 일반적으로 12V~24V (포토커플러 LED 사양 확인)
- **절연 전압**: TLP281-4: 5000Vrms
- **I2C 속도**: 최대 1.7MHz (Fast-mode Plus)
- **동작 전압**: VCC: 1.8V ~ 5.5V

### 신뢰성
- ✅ 전기적 절연: 포토커플러 사용
- ✅ 노이즈 내성: 광학 절연
- ⚠️ 개선 필요: ESD 보호, 전원 필터링

---

## 📚 참고 자료

### 데이터시트
1. **MCP23017**: Microchip 16-Bit I/O Expander with I2C Interface
2. **TLP281-4**: Toshiba 4-Channel Transistor Output Photocoupler
3. **I2C Bus Specification**: NXP I2C-bus specification and user manual

### 설계 가이드
- I2C 풀업 저항 계산: R = (Vcc - 0.4V) / (3mA × n)
  - n = 버스 상의 디바이스 수
  - 일반적으로 4.7kΩ 사용

---

**작성**: 2025-11-10
**분석 대상**: DI.SchDoc
**도구**: altium_parser.py (Python)
