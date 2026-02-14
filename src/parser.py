"""
NODAL - BFS 2024:1 Compliance Engine
IFC Parser Module

Extracts space data from IFC files for Swedish construction compliance checking.
Focuses on bathroom identification and space boundary extraction.
"""

import ifcopenshell
import ifcopenshell.geom
import os
import json
from typing import Dict, List, Optional, Tuple, Any


def parse_ifc(file_path: str) -> Dict[str, Any]:
    """
    Parse IFC file and extract all space entities with bathroom identification.
    
    Args:
        file_path: Path to the IFC file
        
    Returns:
        Dictionary containing spaces list and summary statistics
    """
    
    # Validate file existence
    if not os.path.exists(file_path):
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "other": 0,
                "error": f"File not found: {file_path}"
            }
        }
    
    try:
        # Open IFC file
        ifc_file = ifcopenshell.open(file_path)
    except Exception as e:
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "other": 0,
                "error": f"Failed to open IFC file: {str(e)}"
            }
        }
    
    # Extract all IfcSpace entities
    try:
        spaces = ifc_file.by_type("IfcSpace")
    except Exception as e:
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "other": 0,
                "error": f"Failed to extract spaces: {str(e)}"
            }
        }
    
    parsed_spaces = []
    bathroom_count = 0
    other_count = 0
    
    # Process each space
    for space in spaces:
        space_data = _extract_space_data(space, ifc_file)
        
        if space_data:
            parsed_spaces.append(space_data)
            
            # Count space types
            if space_data["type"] == "bathroom":
                bathroom_count += 1
            else:
                other_count += 1
    
    # Build result dictionary
    result = {
        "spaces": parsed_spaces,
        "summary": {
            "total_spaces": len(parsed_spaces),
            "bathrooms": bathroom_count,
            "other": other_count
        }
    }
    
    return result


def _extract_space_data(space: Any, ifc_file: Any) -> Optional[Dict[str, Any]]:
    """
    Extract data from a single IfcSpace entity.
    
    Args:
        space: IfcSpace entity
        ifc_file: Opened IFC file object
        
    Returns:
        Dictionary with space data or None if extraction fails
    """
    try:
        # Extract space ID
        space_id = space.GlobalId if hasattr(space, 'GlobalId') else str(space.id())
        
        # Extract space name
        space_name = space.Name if hasattr(space, 'Name') and space.Name else "Unknown"
        
        # Determine space type (bathroom detection)
        space_type = _classify_space_type(space_name)
        
        # Extract floor level
        floor_level = _get_floor_level(space, ifc_file)
        
        # Build base space data
        space_data = {
            "id": space_id,
            "name": space_name,
            "type": space_type,
            "floor_level": floor_level
        }
        
        # Extract boundary polygon if available
        boundary = _extract_boundary(space, ifc_file)
        if boundary:
            space_data["boundary"] = boundary
        
        return space_data
        
    except Exception as e:
        # Skip spaces that fail to parse
        return None


def _classify_space_type(space_name: str) -> str:
    """
    Classify space as bathroom or other based on name.
    
    Args:
        space_name: Name of the space
        
    Returns:
        "bathroom" or "other"
    """
    bathroom_keywords = ["bath", "wc", "toilet", "restroom", "badrum"]
    
    space_name_lower = space_name.lower()
    
    for keyword in bathroom_keywords:
        if keyword in space_name_lower:
            return "bathroom"
    
    return "other"


def _get_floor_level(space: Any, ifc_file: Any) -> int:
    """
    Extract floor level from space's building storey.
    
    Args:
        space: IfcSpace entity
        ifc_file: Opened IFC file object
        
    Returns:
        Floor level number (defaults to 0 if not found)
    """
    try:
        # Get the building storey containing this space
        if hasattr(space, 'Decomposes') and space.Decomposes:
            for rel in space.Decomposes:
                if hasattr(rel, 'RelatingObject'):
                    storey = rel.RelatingObject
                    if storey.is_a('IfcBuildingStorey'):
                        # Try to extract elevation or name-based level
                        if hasattr(storey, 'Elevation') and storey.Elevation is not None:
                            # Convert elevation to floor number (assuming 3m per floor)
                            return int(round(storey.Elevation / 3000.0)) + 1
                        elif hasattr(storey, 'Name') and storey.Name:
                            # Try to extract number from name
                            import re
                            match = re.search(r'\d+', storey.Name)
                            if match:
                                return int(match.group())
        
        # Alternative: check ContainedInStructure
        if hasattr(space, 'ContainedInStructure') and space.ContainedInStructure:
            for rel in space.ContainedInStructure:
                if hasattr(rel, 'RelatingStructure'):
                    storey = rel.RelatingStructure
                    if storey.is_a('IfcBuildingStorey'):
                        if hasattr(storey, 'Elevation') and storey.Elevation is not None:
                            return int(round(storey.Elevation / 3000.0)) + 1
                        elif hasattr(storey, 'Name') and storey.Name:
                            import re
                            match = re.search(r'\d+', storey.Name)
                            if match:
                                return int(match.group())
        
        return 0
        
    except Exception:
        return 0


def _extract_boundary(space: Any, ifc_file: Any) -> Optional[List[List[float]]]:
    """
    Extract boundary polygon coordinates from space.
    
    Args:
        space: IfcSpace entity
        ifc_file: Opened IFC file object
        
    Returns:
        List of [x, y] coordinate pairs or None if boundary not available
    """
    try:
        # Try to get 2nd level space boundaries (most accurate for compliance)
        if hasattr(space, 'BoundedBy') and space.BoundedBy:
            boundary_points = []
            
            for boundary_rel in space.BoundedBy:
                if hasattr(boundary_rel, 'RelatedBuildingElement'):
                    boundary = boundary_rel.RelatedBuildingElement
                    
                    # Try to extract geometry
                    if hasattr(boundary, 'ConnectionGeometry'):
                        conn_geom = boundary.ConnectionGeometry
                        if hasattr(conn_geom, 'SurfaceOnRelatingElement'):
                            surface = conn_geom.SurfaceOnRelatingElement
                            points = _extract_points_from_surface(surface)
                            if points:
                                boundary_points.extend(points)
            
            if boundary_points:
                # Remove duplicates and return unique points
                unique_points = _remove_duplicate_points(boundary_points)
                if len(unique_points) >= 3:  # Valid polygon needs at least 3 points
                    return unique_points
        
        # Fallback: try to get shape geometry
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        
        try:
            shape = ifcopenshell.geom.create_shape(settings, space)
            if shape:
                # Extract vertices from the shape geometry
                verts = shape.geometry.verts
                # Group into [x, y, z] triplets and project to 2D
                points = []
                for i in range(0, len(verts), 3):
                    x, y = verts[i], verts[i+1]
                    points.append([round(x, 3), round(y, 3)])
                
                if points:
                    # Get convex hull or boundary outline
                    unique_points = _remove_duplicate_points(points)
                    if len(unique_points) >= 3:
                        return unique_points[:50]  # Limit to 50 points for performance
        except Exception:
            pass
        
        return None
        
    except Exception:
        return None


def _extract_points_from_surface(surface: Any) -> List[List[float]]:
    """
    Extract coordinate points from an IFC surface geometry.
    
    Args:
        surface: IFC surface geometry object
        
    Returns:
        List of [x, y] coordinate pairs
    """
    points = []
    
    try:
        if hasattr(surface, 'OuterBoundary'):
            curve = surface.OuterBoundary
            if hasattr(curve, 'Points'):
                for point in curve.Points:
                    if hasattr(point, 'Coordinates'):
                        coords = point.Coordinates
                        if len(coords) >= 2:
                            points.append([round(coords[0], 3), round(coords[1], 3)])
    except Exception:
        pass
    
    return points


def _remove_duplicate_points(points: List[List[float]], tolerance: float = 0.01) -> List[List[float]]:
    """
    Remove duplicate points from a list of coordinates.
    
    Args:
        points: List of [x, y] coordinate pairs
        tolerance: Distance tolerance for considering points as duplicates
        
    Returns:
        List of unique coordinate pairs
    """
    if not points:
        return []
    
    unique = [points[0]]
    
    for point in points[1:]:
        is_duplicate = False
        for existing in unique:
            if abs(point[0] - existing[0]) < tolerance and abs(point[1] - existing[1]) < tolerance:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique.append(point)
    
    return unique


if __name__ == "__main__":
    """
    Test the IFC parser with a sample file.
    """
    print("=" * 70)
    print("NODAL IFC Parser - Test Run")
    print("=" * 70)
    print()
    
    # Test file path
    test_file = "tests/sample.ifc"
    
    print(f"Parsing IFC file: {test_file}")
    print()
    
    # Parse the IFC file
    result = parse_ifc(test_file)
    
    # Pretty print results
    print("RESULTS:")
    print("-" * 70)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    # Display summary statistics
    print("=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    summary = result.get("summary", {})
    print(f"Total Spaces Found:    {summary.get('total_spaces', 0)}")
    print(f"Bathrooms:            {summary.get('bathrooms', 0)}")
    print(f"Other Spaces:         {summary.get('other', 0)}")
    
    if "error" in summary:
        print(f"\nERROR: {summary['error']}")
    
    print()
    
    # Display bathroom details if any found
    bathrooms = [s for s in result.get("spaces", []) if s["type"] == "bathroom"]
    if bathrooms:
        print("=" * 70)
        print("BATHROOM DETAILS")
        print("=" * 70)
        for i, bathroom in enumerate(bathrooms, 1):
            print(f"\nBathroom {i}:")
            print(f"  ID:           {bathroom['id']}")
            print(f"  Name:         {bathroom['name']}")
            print(f"  Floor Level:  {bathroom['floor_level']}")
            if "boundary" in bathroom:
                print(f"  Boundary:     {len(bathroom['boundary'])} points")
            else:
                print(f"  Boundary:     Not available")
    
    print()
    print("=" * 70)
    print("Test complete.")
    print("=" * 70)
