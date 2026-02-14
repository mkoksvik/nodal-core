"""
NODAL Integration Test
Tests parser → geometry pipeline
"""

from parser import parse_ifc
from geometry import check_multiple_spaces, generate_report

def main():
    print("=" * 70)
    print("NODAL INTEGRATION TEST: PARSER → GEOMETRY")
    print("=" * 70)
    print()
    
    # Parse IFC file
    print("Step 1: Parsing IFC file...")
    parsed_data = parse_ifc("tests/sample.ifc")
    
    spaces = parsed_data.get("spaces", [])
    print(f"✓ Found {len(spaces)} spaces")
    print()
    
    # Check geometry on all spaces
    print(f"Step 2: Checking turning circles for all spaces...")
    print()
    
    results = check_multiple_spaces(spaces)
    report = generate_report(results)
    print(report)
    
    print()
    print("=" * 70)
    print("INTEGRATION TEST COMPLETE")
    print("Pipeline: IFC → Parser → Geometry → Report ✓")
    print("=" * 70)

if __name__ == "__main__":
    main()