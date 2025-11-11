"""
Compare original KiCad file with roundtrip file
"""
import sys
import hashlib
import sexpdata
from pathlib import Path


def compute_hash(file_path):
    """Compute SHA256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def normalize_sexp(sexp_data):
    """Normalize S-expression for comparison by sorting certain elements"""
    if not isinstance(sexp_data, list):
        return sexp_data
    
    # Recursively normalize nested lists
    normalized = [normalize_sexp(item) for item in sexp_data]
    
    return normalized


def compare_files(original_path, roundtrip_path):
    """Compare two KiCad files"""
    print(f"Comparing files:")
    print(f"  Original:   {original_path}")
    print(f"  Roundtrip:  {roundtrip_path}")
    print()
    
    # Compute file hashes
    original_hash = compute_hash(original_path)
    roundtrip_hash = compute_hash(roundtrip_path)
    
    print(f"File hashes:")
    print(f"  Original:   {original_hash}")
    print(f"  Roundtrip:  {roundtrip_hash}")
    print()
    
    if original_hash == roundtrip_hash:
        print("✅ FILES ARE IDENTICAL!")
        return True
    
    print("❌ Files are different. Analyzing differences...")
    print()
    
    # Load and parse both files
    with open(original_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    with open(roundtrip_path, 'r', encoding='utf-8') as f:
        roundtrip_content = f.read()
    
    # Parse S-expressions
    try:
        original_sexp = sexpdata.loads(original_content)
        roundtrip_sexp = sexpdata.loads(roundtrip_content)
    except Exception as e:
        print(f"Error parsing S-expressions: {e}")
        return False
    
    # Compare file sizes
    print(f"File sizes:")
    print(f"  Original:   {len(original_content):,} bytes")
    print(f"  Roundtrip:  {len(roundtrip_content):,} bytes")
    print(f"  Difference: {len(roundtrip_content) - len(original_content):+,} bytes")
    print()
    
    # Compare S-expression structure
    print("Analyzing S-expression differences...")
    
    # Get top-level keys
    def get_top_keys(sexp):
        keys = []
        if isinstance(sexp, list):
            for item in sexp:
                if isinstance(item, list) and len(item) > 0:
                    key = str(item[0]) if isinstance(item[0], sexpdata.Symbol) else str(item[0])
                    keys.append(key)
        return keys
    
    original_keys = get_top_keys(original_sexp)
    roundtrip_keys = get_top_keys(roundtrip_sexp)
    
    print(f"Top-level elements:")
    print(f"  Original:   {original_keys}")
    print(f"  Roundtrip:  {roundtrip_keys}")
    print()
    
    # Compare specific sections
    sections_to_check = ['lib_symbols', 'symbol', 'wire', 'junction', 'label']
    
    for section in sections_to_check:
        original_count = count_elements(original_sexp, section)
        roundtrip_count = count_elements(roundtrip_sexp, section)
        
        status = "✓" if original_count == roundtrip_count else "✗"
        print(f"{status} {section}: Original={original_count}, Roundtrip={roundtrip_count}")
    
    return False


def count_elements(sexp_data, element_name):
    """Count occurrences of elements with a specific name"""
    count = 0
    
    def traverse(node):
        nonlocal count
        if isinstance(node, list) and len(node) > 0:
            if isinstance(node[0], sexpdata.Symbol) and str(node[0]) == element_name:
                count += 1
            for item in node:
                if isinstance(item, list):
                    traverse(item)
    
    traverse(sexp_data)
    return count


def main():
    original = Path("altium2kicad/DI.kicad_sch")
    roundtrip = Path("schematics/DI_roundtrip.kicad_sch")
    
    if not original.exists():
        print(f"Error: Original file not found: {original}")
        sys.exit(1)
    
    if not roundtrip.exists():
        print(f"Error: Roundtrip file not found: {roundtrip}")
        sys.exit(1)
    
    result = compare_files(original, roundtrip)
    
    if not result:
        print()
        print("Next steps:")
        print("1. Review the differences above")
        print("2. Fix the kicad_to_code.py or code_to_kicad.py scripts")
        print("3. Re-run the roundtrip test")
        sys.exit(1)


if __name__ == "__main__":
    main()
