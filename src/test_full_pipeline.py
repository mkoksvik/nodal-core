"""
NODAL Full Pipeline Test
Tests: Parser → Geometry → Rules → Report
"""

from parser import parse_ifc
from geometry import check_multiple_spaces
from rules import BFS2024ComplianceChecker, generate_compliance_report

def main():
    print("=" * 80)
    print("NODAL FULL PIPELINE TEST")
    print("=" * 80)
    print()
    
    # Initialize compliance checker
    checker = BFS2024ComplianceChecker()
    
    # Step 1: Parse IFC
    print("Step 1: Parsing IFC file...")
    parsed_data = parse_ifc("tests/sample.ifc")
    spaces = parsed_data.get("spaces", [])
    print(f"✓ Found {len(spaces)} spaces")
    print()
    
    # Step 2: Check geometry
    print("Step 2: Running geometry checks...")
    geometry_results = check_multiple_spaces(spaces)
    print(f"✓ Geometry checks complete")
    print()
    
    # Step 3: Check compliance rules
    print("Step 3: Running BFS 2024:1 compliance checks...")
    compliance_results = []
    for i, space in enumerate(spaces):
        geometry_result = geometry_results[i]
        compliance_result = checker.check_compliance(space, geometry_result)
        compliance_results.append(compliance_result)
    
    print(f"✓ Compliance checks complete")
    print()
    
    # Step 4: Generate report
    print("=" * 80)
    report = generate_compliance_report(compliance_results)
    print(report)
    
    print()
    print("=" * 80)
    print("FULL PIPELINE TEST COMPLETE")
    print("IFC → Parser → Geometry → Rules → Compliance Report ✓")
    print("=" * 80)

if __name__ == "__main__":
    main()