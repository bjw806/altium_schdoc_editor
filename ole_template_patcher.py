"""
OLE Template-based Patcher
===========================
원본 OLE 파일을 템플릿으로 사용하여 새 파일을 생성합니다.
FileHeader 스트림만 교체하고 나머지는 원본 구조를 유지합니다.
"""

import struct
import shutil
import olefile

def patch_ole_file_simple(template_file: str, output_file: str, new_fileheader_data: bytes):
    """
    템플릿 기반으로 OLE 파일 생성

    간단한 접근: 원본을 복사하고 FileHeader 스트림 섹터만 덮어쓰기
    """
    # 1. 템플릿 복사
    shutil.copy2(template_file, output_file)

    # 2. 원본 파일에서 FileHeader 위치 찾기
    ole = olefile.OleFileIO(template_file)

    # FileHeader 스트림 정보 가져오기
    if not ole.exists('FileHeader'):
        raise ValueError("Template file doesn't have FileHeader stream")

    # 3. 바이너리 레벨에서 스트림 교체
    # OLE 파일을 바이너리로 열어서 직접 수정
    with open(output_file, 'rb') as f:
        file_data = bytearray(f.read())

    # 헤더 파싱
    sector_size = 512

    # First directory sector 찾기
    first_dir_sector = struct.unpack('<i', file_data[48:52])[0]

    # Directory에서 FileHeader 엔트리 찾기
    dir_offset = 512 + (first_dir_sector * sector_size)

    # FileHeader는 일반적으로 entry 1 (Additional이 있으면 다를 수 있음)
    # 모든 엔트리 스캔
    fileheader_entry_idx = None
    fileheader_start_sector = None
    fileheader_size = None

    for entry_idx in range(4):  # 처음 4개 엔트리 확인
        entry_offset = dir_offset + (entry_idx * 128)

        # 이름 읽기
        name_bytes = file_data[entry_offset:entry_offset+64]
        name_len = struct.unpack('<H', file_data[entry_offset+64:entry_offset+66])[0]

        if name_len > 0 and name_len <= 64:
            name = name_bytes[:name_len-2].decode('utf-16le', errors='ignore')

            if name == 'FileHeader':
                fileheader_entry_idx = entry_idx
                fileheader_start_sector = struct.unpack('<i', file_data[entry_offset+116:entry_offset+120])[0]
                fileheader_size = struct.unpack('<Q', file_data[entry_offset+120:entry_offset+128])[0]
                break

    if fileheader_entry_idx is None:
        raise ValueError("Could not find FileHeader entry in directory")

    ole.close()

    # 4. 새 데이터 크기 확인
    old_sectors = (fileheader_size + sector_size - 1) // sector_size
    new_sectors = (len(new_fileheader_data) + sector_size - 1) // sector_size

    if new_sectors != old_sectors:
        # 크기가 다르면 섹터 재배치 필요 - 복잡함
        # 일단 같은 크기일 때만 지원
        print(f"Warning: Size mismatch (old={old_sectors} sectors, new={new_sectors} sectors)")
        print(f"         Old size: {fileheader_size} bytes, New size: {len(new_fileheader_data)} bytes")

        # 크기가 작으면 패딩해서 맞춤
        if new_sectors < old_sectors:
            # 패딩 추가
            padded_size = old_sectors * sector_size
            new_fileheader_data = new_fileheader_data + b'\x00' * (padded_size - len(new_fileheader_data))
            new_sectors = old_sectors
            print(f"         Padded new data to {len(new_fileheader_data)} bytes")
        else:
            # 크기가 더 크면 현재 방식으로는 불가능
            print(f"Error: New data is larger than template. Cannot patch.")
            return False

    # 5. FileHeader 섹터에 새 데이터 쓰기
    # FAT 읽기
    first_fat_sector = struct.unpack('<i', file_data[76:80])[0]
    fat_offset = 512 + (first_fat_sector * sector_size)

    # FileHeader 섹터 체인 따라가면서 데이터 쓰기
    current_sector = fileheader_start_sector
    data_offset = 0

    for i in range(new_sectors):
        if current_sector < 0:
            break

        # 섹터 파일 오프셋
        sector_file_offset = 512 + (current_sector * sector_size)

        # 쓸 데이터 크기
        remaining = len(new_fileheader_data) - data_offset
        to_write = min(remaining, sector_size)

        # 데이터 쓰기
        file_data[sector_file_offset:sector_file_offset+to_write] = new_fileheader_data[data_offset:data_offset+to_write]

        # 나머지 섹터는 0으로 패딩
        if to_write < sector_size:
            file_data[sector_file_offset+to_write:sector_file_offset+sector_size] = b'\x00' * (sector_size - to_write)

        data_offset += to_write

        # 다음 섹터 찾기 (FAT에서)
        fat_entry_offset = fat_offset + (current_sector * 4)
        next_sector = struct.unpack('<i', file_data[fat_entry_offset:fat_entry_offset+4])[0]

        if next_sector == -2:  # ENDOFCHAIN
            break

        current_sector = next_sector

    # 6. Directory entry의 크기 업데이트
    entry_offset = dir_offset + (fileheader_entry_idx * 128)
    struct.pack_into('<Q', file_data, entry_offset + 120, len(new_fileheader_data))

    # 7. 수정된 파일 저장
    with open(output_file, 'wb') as f:
        f.write(file_data)

    print(f"✓ Successfully patched {output_file}")
    return True


def verify_ole_file(filename: str):
    """OLE 파일이 유효한지 검증"""
    try:
        ole = olefile.OleFileIO(filename)
        streams = ole.listdir()
        ole.close()
        print(f"✓ {filename} is valid OLE file")
        print(f"  Streams: {streams}")
        return True
    except Exception as e:
        print(f"✗ {filename} is invalid: {e}")
        return False
