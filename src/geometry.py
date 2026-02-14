"""
NODAL Geometry Checking Module
Validates accessibility requirements for spaces
"""

from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points
import numpy as np
from typing import Dict, List, Tuple, Optional


def check_turning_circle(space_dict: Dict) -> Dict:
    """
    Check if a 1500mm diameter turning circle can fit inside a space.
    
    Args:
        space_dict: Dictionary containing space data from parser
                   Must have 'id', 'name', and 'boundary' keys
    
    Returns:
        Dictionary with check results including pass/fail status,
        circle center coordinates if passed, or collision details if failed
    """
    
    # Initialize result structure
    result = {
        "space_id": space_dict.get("id", "unknown"),
        "space_name": space_dict.get("name", "unknown"),
        "passed": False,
        "circle_diameter_mm": 1500,
        "circle_center": None,
        "collision_details": None
    }
    
    # Error handling: Check if boundary exists
    if "boundary" not in space_dict:
        result["collision_details"] = "ERROR: No boundary data provided"
        return result
    
    boundary = space_dict["boundary"]
    
    # Error handling: Check minimum points
    if len(boundary) < 3:
        result["collision_details"] = f"ERROR: Boundary has only {len(boundary)} points (minimum 3 required)"
        return result
    
    # Convert boundary to Shapely Polygon
    try:
        polygon = Polygon(boundary)
        
        # Check if polygon is valid
        if not polygon.is_valid:
            result["collision_details"] = "ERROR: Invalid polygon geometry (self-intersecting or malformed)"
            return result
            
    except Exception as e:
        result["collision_details"] = f"ERROR: Failed to create polygon - {str(e)}"
        return result
    
    # Get polygon bounds
    minx, miny, maxx, maxy = polygon.bounds
    
    # Circle parameters
    radius_mm = 750  # 1500mm diameter = 750mm radius
    grid_spacing = 100  # Test points every 100mm
    
    # Generate grid of test points
    x_points = np.arange(minx + radius_mm, maxx - radius_mm + grid_spacing, grid_spacing)
    y_points = np.arange(miny + radius_mm, maxy - radius_mm + grid_spacing, grid_spacing)
    
    # Track best attempt (closest to fitting)
    best_center = None
    min_collision_distance = float('inf')
    
    # Test each grid point
    for x in x_points:
        for y in y_points:
            center_point = Point(x, y)
            
            # Skip if center is not inside polygon
            if not polygon.contains(center_point):
                continue
            
            # Create circle at this point
            circle = center_point.buffer(radius_mm)
            
            # Check if circle fits entirely inside polygon
            if polygon.contains(circle):
                # SUCCESS - Circle fits!
                result["passed"] = True
                result["circle_center"] = [float(x), float(y)]
                result["collision_details"] = f"Turning circle successfully fits with center at ({x:.1f}, {y:.1f})"
                return result
            
            # Track how close we got (for failure reporting)
            if center_point.within(polygon):
                # Calculate how far the circle extends outside
                collision_distance = circle.difference(polygon).area
                if collision_distance < min_collision_distance:
                    min_collision_distance = collision_distance
                    best_center = (x, y)
    
    # If we reach here, no valid position was found
    if best_center:
        result["collision_details"] = (
            f"FAIL: No valid turning circle position found. "
            f"Closest attempt at ({best_center[0]:.1f}, {best_center[1]:.1f}) "
            f"extends {min_collision_distance:.1f} mm² outside boundary. "
            f"Space may be too narrow or obstructed."
        )
    else:
        # Calculate space dimensions for helpful error message
        width = maxx - minx
        height = maxy - miny
        result["collision_details"] = (
            f"FAIL: Space dimensions ({width:.1f} x {height:.1f} mm) "
            f"are too small for 1500mm turning circle. "
            f"Minimum required: 1500mm in at least one direction."
        )
    
    return result


def check_multiple_spaces(spaces_list: List[Dict]) -> List[Dict]:
    """
    Check turning circles for multiple spaces.
    
    Args:
        spaces_list: List of space dictionaries from parser output
    
    Returns:
        List of check results for each space
    """
    results = []
    for space in spaces_list:
        result = check_turning_circle(space)
        results.append(result)
    return results


def generate_report(results: List[Dict]) -> str:
    """
    Generate a human-readable report from check results.
    
    Args:
        results: List of check result dictionaries
    
    Returns:
        Formatted report string
    """
    report_lines = ["=" * 70]
    report_lines.append("NODAL GEOMETRY CHECK REPORT - TURNING CIRCLE VALIDATION")
    report_lines.append("=" * 70)
    report_lines.append("")
    
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    report_lines.append(f"Total spaces checked: {len(results)}")
    report_lines.append(f"Passed: {passed_count}")
    report_lines.append(f"Failed: {failed_count}")
    report_lines.append("")
    report_lines.append("-" * 70)
    
    for result in results:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        report_lines.append(f"\n{status} | {result['space_name']} (ID: {result['space_id']})")
        report_lines.append(f"  {result['collision_details']}")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    
    return "\n".join(report_lines)


# ============================================================================
# TEST CODE
# ============================================================================

if __name__ == "__main__":
    print("NODAL GEOMETRY CHECKER - TEST SUITE")
    print("=" * 70)
    print()
    
    # TEST CASE 1: Large bathroom - SHOULD PASS
    test_space_pass = {
        "id": "space_001",
        "name": "Master Bathroom",
        "type": "bathroom",
        "boundary": [
            [0, 0],
            [3000, 0],
            [3000, 2500],
            [0, 2500]
        ]
    }
    
    # TEST CASE 2: Small powder room - SHOULD FAIL (too narrow)
    test_space_fail_small = {
        "id": "space_002",
        "name": "Powder Room",
        "type": "bathroom",
        "boundary": [
            [0, 0],
            [1200, 0],
            [1200, 1800],
            [0, 1800]
        ]
    }
    
    # TEST CASE 3: L-shaped bathroom - SHOULD PASS (non-convex polygon)
    test_space_l_shape = {
        "id": "space_003",
        "name": "L-Shaped Bathroom",
        "type": "bathroom",
        "boundary": [
            [0, 0],
            [3000, 0],
            [3000, 1500],
            [1500, 1500],
            [1500, 3000],
            [0, 3000]
        ]
    }
    
    # TEST CASE 4: Narrow corridor - SHOULD FAIL
    test_space_corridor = {
        "id": "space_004",
        "name": "Hallway",
        "type": "circulation",
        "boundary": [
            [0, 0],
            [5000, 0],
            [5000, 1000],
            [0, 1000]
        ]
    }
    
    # TEST CASE 5: Exactly 1500mm square - SHOULD PASS (edge case)
    test_space_exact = {
        "id": "space_005",
        "name": "Minimal Bathroom",
        "type": "bathroom",
        "boundary": [
            [0, 0],
            [1600, 0],
            [1600, 1600],
            [0, 1600]
        ]
    }
    
    # TEST CASE 6: Missing boundary - ERROR HANDLING
    test_space_error = {
        "id": "space_006",
        "name": "Invalid Space",
        "type": "bathroom"
        # No boundary key
    }
    
    # TEST CASE 7: Insufficient points - ERROR HANDLING
    test_space_invalid = {
        "id": "space_007",
        "name": "Invalid Polygon",
        "type": "bathroom",
        "boundary": [[0, 0], [1000, 0]]  # Only 2 points
    }
    
    # TEST CASE 8: Complex non-convex shape - bathroom with alcove
    test_space_alcove = {
        "id": "space_008",
        "name": "Bathroom with Alcove",
        "type": "bathroom",
        "boundary": [
            [0, 0],
            [2500, 0],
            [2500, 1000],
            [2000, 1000],
            [2000, 2000],
            [2500, 2000],
            [2500, 3000],
            [0, 3000]
        ]
    }
    
    # Collect all test cases
    test_spaces = [
        test_space_pass,
        test_space_fail_small,
        test_space_l_shape,
        test_space_corridor,
        test_space_exact,
        test_space_error,
        test_space_invalid,
        test_space_alcove
    ]
    
    # Run checks on all test spaces
    print("Running geometry checks on test spaces...")
    print()
    
    all_results = []
    for i, space in enumerate(test_spaces, 1):
        print(f"Testing {i}/{len(test_spaces)}: {space.get('name', 'Unknown')}...")
        result = check_turning_circle(space)
        all_results.append(result)
    
    print()
    print("=" * 70)
    print()
    
    # Generate and print report
    report = generate_report(all_results)
    print(report)
    
    # Print detailed individual results
    print("\n" + "=" * 70)
    print("DETAILED RESULTS")
    print("=" * 70)
    
    for result in all_results:
        print(f"\nSpace: {result['space_name']}")
        print(f"  ID: {result['space_id']}")
        print(f"  Status: {'PASSED' if result['passed'] else 'FAILED'}")
        print(f"  Circle Diameter: {result['circle_diameter_mm']}mm")
        if result['circle_center']:
            print(f"  Circle Center: ({result['circle_center'][0]:.1f}, {result['circle_center'][1]:.1f})")
        print(f"  Details: {result['collision_details']}")
    
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)