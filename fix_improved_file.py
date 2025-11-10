#!/usr/bin/env python3
"""
Fix DI_improved.SchDoc by using template copying
"""

import shutil
import struct
import olefile
from altium_parser import AltiumParser
from altium_serializer import AltiumSerializer


def create_working_improved_file():
    """
    Create a working improved file using a safer method:
    Just create a new file from the original without modifications,
    then verify it works.
    """

    print("방법 1: 원본 파일 단순 복사로 테스트")
    print("=" * 60)

    # Step 1: Just copy the original
    shutil.copy2("DI.SchDoc", "DI_test_copy.SchDoc")

    # Step 2: Verify it can be opened
    try:
        parser = AltiumParser()
        doc = parser.parse_file("DI_test_copy.SchDoc")
        print(f"✅ 복사본 검증 성공: {len(doc.objects)} 객체")
    except Exception as e:
        print(f"❌ 복사본 검증 실패: {e}")
        return False

    print("\n방법 2: FileHeader를 원본 크기에 맞춰서 패딩")
    print("=" * 60)

    # Parse original
    parser = AltiumParser()
    doc_original = parser.parse_file("DI.SchDoc")

    # Get original FileHeader size
    ole_original = olefile.OleFileIO("DI.SchDoc")
    original_fileheader_size = 0
    for entry in ole_original.direntries:
        if entry and entry.name == 'FileHeader':
            original_fileheader_size = entry.size
            break
    ole_original.close()

    print(f"원본 FileHeader 크기: {original_fileheader_size} bytes")

    # Build new FileHeader
    serializer = AltiumSerializer()
    records = serializer._build_records(doc_original)
    new_fileheader = b''.join(records)

    print(f"새로운 FileHeader 크기: {len(new_fileheader)} bytes")

    # Calculate size difference
    size_diff = len(new_fileheader) - original_fileheader_size
    print(f"크기 차이: {size_diff:+d} bytes")

    if len(new_fileheader) > original_fileheader_size:
        print(f"⚠️  새로운 파일이 {size_diff} bytes 더 큽니다.")
        print(f"   원본 크기로 맞추려면 데이터를 잘라내야 하므로 불가능합니다.")
        print(f"   대신 크기를 늘려야 하므로 OLE 구조를 완전히 재구성해야 합니다.")
    else:
        print(f"✓ 새로운 파일이 더 작으므로 패딩 가능합니다.")

        # Pad to original size
        padded_fileheader = new_fileheader + b'\x00' * size_diff

        # Now try to replace FileHeader in the copy
        # This requires binary-level OLE manipulation
        print("\n원본 파일 구조 분석 중...")

        with open("DI.SchDoc", 'rb') as f:
            original_bytes = f.read()

        # Find FileHeader location
        ole = olefile.OleFileIO("DI.SchDoc")
        fileheader_start_sector = None
        for entry in ole.direntries:
            if entry and entry.name == 'FileHeader':
                fileheader_start_sector = entry.isectStart
                break
        ole.close()

        if fileheader_start_sector is not None:
            print(f"FileHeader 시작 섹터: {fileheader_start_sector}")

            # Copy original to new file
            with open("DI_improved_v2.SchDoc", 'wb') as f:
                f.write(original_bytes)

            # Replace FileHeader data
            SECTOR_SIZE = 512
            with open("DI_improved_v2.SchDoc", 'r+b') as f:
                offset = 512 + (fileheader_start_sector * SECTOR_SIZE)
                f.seek(offset)
                f.write(padded_fileheader)

            print(f"✓ FileHeader 데이터 교체 완료")

            # Verify
            try:
                doc2 = parser.parse_file("DI_improved_v2.SchDoc")
                print(f"✅ 검증 성공: {len(doc2.objects)} 객체")
                return True
            except Exception as e:
                print(f"❌ 검증 실패: {e}")
                return False

    return False


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║     DI_improved.SchDoc 파일 수정 테스트                    ║
╚════════════════════════════════════════════════════════════╝
    """)

    success = create_working_improved_file()

    if success:
        print("\n" + "=" * 60)
        print("✅ 성공! DI_improved_v2.SchDoc 파일이 생성되었습니다.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 파일 생성 실패")
        print("=" * 60)
        print("\n대안:")
        print("1. JSON으로 내보내서 분석: python3 json_parser.py DI.SchDoc DI.json")
        print("2. 분석 보고서 확인: cat 회로도_분석_및_개선_보고서.md")
        print("3. Altium Designer에서 수동 수정")
