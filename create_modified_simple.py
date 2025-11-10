#!/usr/bin/env python3
"""
간단한 방법으로 수정된 파일 생성
====================================
원본 파일을 복사하고 FileHeader 섹터를 직접 교체
"""

import struct
import shutil
from altium_parser import AltiumParser, RecordReader
from altium_serializer import AltiumSerializer
from altium_objects import Label

def create_modified_schematic():
    """DI.schdoc을 수정하여 새 파일 생성"""

    print("=" * 70)
    print("DI_modified.SchDoc 생성 (템플릿 기반)")
    print("=" * 70)

    # 1. 원본 파싱
    print("\n[1/5] 원본 파일 파싱...")
    parser = AltiumParser()
    doc = parser.parse_file("DI.SchDoc")
    print(f"✓ {len(doc.objects)}개 객체 파싱됨")

    # 2. 수정사항 적용
    print("\n[2/5] 수정사항 적용...")

    modifications = []

    # 타이틀 추가
    title = Label()
    title.index = len(doc.objects)
    title.text = "DI Schematic - Modified"
    title.location_x = 400
    title.location_y = 9400
    title.color = 0x0000FF
    title.font_id = 3
    title.unique_id = "MOD00001"
    title.owner_part_id = -1
    title.properties = {
        'RECORD': '4',
        'TEXT': title.text,
        'LOCATION.X': str(title.location_x),
        'LOCATION.Y': str(title.location_y),
        'COLOR': str(title.color),
        'FONTID': str(title.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': title.unique_id
    }
    doc.objects.append(title)
    modifications.append("Title")

    # 버전 정보
    version = Label()
    version.index = len(doc.objects)
    version.text = "v1.1 - 2025-11-10"
    version.location_x = 400
    version.location_y = 9200
    version.color = 0x808080
    version.font_id = 2
    version.unique_id = "MOD00002"
    version.owner_part_id = -1
    version.properties = {
        'RECORD': '4',
        'TEXT': version.text,
        'LOCATION.X': str(version.location_x),
        'LOCATION.Y': str(version.location_y),
        'COLOR': str(version.color),
        'FONTID': str(version.font_id),
        'OWNERPARTID': '-1',
        'UNIQUEID': version.unique_id
    }
    doc.objects.append(version)
    modifications.append("Version")

    print(f"✓ {len(modifications)}개 항목 추가됨")

    # 3. 레코드 직렬화
    print("\n[3/5] 레코드 직렬화...")
    serializer = AltiumSerializer()
    records = serializer._build_records(doc)
    new_fileheader_data = b''.join(records)
    print(f"✓ {len(records)}개 레코드, {len(new_fileheader_data)} bytes")

    # 4. 원본 파일 복사
    print("\n[4/5] 템플릿 파일 복사...")
    shutil.copy2("DI.SchDoc", "DI_modified.SchDoc")
    print("✓ DI.SchDoc → DI_modified.SchDoc 복사됨")

    # 5. FileHeader 교체 (바이너리 레벨)
    print("\n[5/5] FileHeader 스트림 교체...")

    with open("DI_modified.SchDoc", 'rb') as f:
        file_data = bytearray(f.read())

    # 원본 FileHeader 크기 확인
    import olefile
    ole_orig = olefile.OleFileIO("DI.SchDoc")
    orig_fh_data = ole_orig.openstream('FileHeader').read()
    ole_orig.close()

    print(f"  원본 FileHeader: {len(orig_fh_data)} bytes")
    print(f"  새 FileHeader: {len(new_fileheader_data)} bytes")
    print(f"  차이: {len(new_fileheader_data) - len(orig_fh_data):+d} bytes")

    # 크기가 비슷한지 확인
    size_diff = abs(len(new_fileheader_data) - len(orig_fh_data))
    size_diff_percent = (size_diff / len(orig_fh_data)) * 100

    if size_diff_percent < 15:  # 15% 이내 차이면 패딩으로 해결
        print(f"  → 크기 차이 {size_diff_percent:.1f}% - 패딩 가능")

        # 섹터 크기에 맞춰 패딩
        sector_size = 512
        target_sectors = (len(orig_fh_data) + sector_size - 1) // sector_size
        target_size = target_sectors * sector_size

        if len(new_fileheader_data) < target_size:
            new_fileheader_data = new_fileheader_data + b'\x00' * (target_size - len(new_fileheader_data))
            print(f"  → {len(new_fileheader_data)} bytes로 패딩됨")

        # FileHeader 섹터 위치 찾기
        first_dir_sector = struct.unpack('<i', file_data[48:52])[0]
        dir_offset = 512 + (first_dir_sector * sector_size)

        # FileHeader entry 찾기 (보통 entry 1)
        for entry_idx in range(10):
            entry_offset = dir_offset + (entry_idx * 128)
            name_bytes = file_data[entry_offset:entry_offset+64]
            name_len = struct.unpack('<H', file_data[entry_offset+64:entry_offset+66])[0]

            if 0 < name_len <= 64:
                name = name_bytes[:name_len-2].decode('utf-16le', errors='ignore')

                if name == 'FileHeader':
                    start_sector = struct.unpack('<i', file_data[entry_offset+116:entry_offset+120])[0]
                    print(f"  → FileHeader 발견: entry {entry_idx}, sector {start_sector}")

                    # 섹터에 데이터 쓰기
                    offset = 0
                    current_sector = start_sector

                    # FAT에서 섹터 체인 따라가기
                    first_fat = struct.unpack('<i', file_data[76:80])[0]
                    fat_offset = 512 + (first_fat * sector_size)

                    while offset < len(new_fileheader_data) and current_sector >= 0:
                        sector_file_offset = 512 + (current_sector * sector_size)
                        to_write = min(sector_size, len(new_fileheader_data) - offset)

                        # 데이터 쓰기
                        file_data[sector_file_offset:sector_file_offset+to_write] = \
                            new_fileheader_data[offset:offset+to_write]

                        # 패딩
                        if to_write < sector_size:
                            file_data[sector_file_offset+to_write:sector_file_offset+sector_size] = \
                                b'\x00' * (sector_size - to_write)

                        offset += to_write

                        # 다음 섹터
                        fat_entry = fat_offset + (current_sector * 4)
                        next_sector = struct.unpack('<i', file_data[fat_entry:fat_entry+4])[0]
                        if next_sector == -2:  # ENDOFCHAIN
                            break
                        current_sector = next_sector

                    # 크기 업데이트
                    struct.pack_into('<Q', file_data, entry_offset + 120, len(new_fileheader_data))

                    print(f"  ✓ FileHeader 교체 완료")
                    break
    else:
        print(f"  ✗ 크기 차이가 너무 큼 ({size_diff_percent:.1f}%)")
        print(f"  → 이 방법으로는 불가능, 다른 접근 필요")
        return False

    # 파일 저장
    with open("DI_modified.SchDoc", 'wb') as f:
        f.write(file_data)

    print("\n" + "=" * 70)
    print("✅ DI_modified.SchDoc 생성 완료")
    print("=" * 70)

    # 검증
    print("\n검증 중...")
    try:
        test_doc = parser.parse_file("DI_modified.SchDoc")
        print(f"✓ 파싱 성공: {len(test_doc.objects)}개 객체")
        print(f"  - 원본: 1586개")
        print(f"  - 수정: {len(test_doc.objects)}개")
        print(f"  - 추가: +{len(test_doc.objects) - 1586}개")
        return True
    except Exception as e:
        print(f"✗ 파싱 실패: {e}")
        return False

if __name__ == "__main__":
    success = create_modified_schematic()
    import sys
    sys.exit(0 if success else 1)
