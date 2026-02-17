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
from typing import Any, Dict, List, Optional, Tuple


def convert_to_millimeters(coordinates: List[List[float]]) -> List[List[float]]:
    """
    Convert IFC coordinates from meters to millimeters.
    IFC files typically use meters, but BFS 2024:1 uses millimeters.
    
    Args:
        coordinates: List of [x, y] coordinate pairs in meters
        
    Returns:
        List of [x, y] coordinate pairs in millimeters
    """
    return [[x * 1000, y * 1000] for x, y in coordinates]


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


def _get_property_value(space: Any, *property_names: str) -> Optional[Any]:
    """
    Get first matching IfcPropertySingleValue from space's property sets.
    Searches IsDefinedBy -> IfcRelDefinesByProperties -> IfcPropertySet -> HasProperties.
    
    Args:
        space: IfcSpace or other entity with IsDefinedBy
        property_names: One or more property names to try (e.g. "Width", "ClearWidth")
        
    Returns:
        Raw NominalValue (number/string) or None if not found
    """
    try:
        for rel in getattr(space, "IsDefinedBy", []) or []:
            if getattr(rel, "is_a", lambda _: False)("IfcRelDefinesByProperties"):
                pset = getattr(rel, "RelatingPropertyDefinition", None)
                if pset is None:
                    continue
                if getattr(pset, "is_a", lambda _: False)("IfcPropertySet"):
                    for prop in getattr(pset, "HasProperties", []) or []:
                        if getattr(prop, "is_a", lambda _: False)("IfcPropertySingleValue"):
                            if getattr(prop, "Name", None) in property_names:
                                nv = getattr(prop, "NominalValue", None)
                                if nv is None:
                                    return None
                                return getattr(nv, "wrappedValue", nv)
    except Exception:
        pass
    return None


def _get_property_as_mm(space: Any, *property_names: str) -> Optional[float]:
    """
    Get numeric property and convert to millimeters if value looks like meters (< 100).
    """
    val = _get_property_value(space, *property_names)
    if val is None:
        return None
    try:
        n = float(val)
        if n < 0:
            return None
        if n < 100:
            return round(n * 1000.0)
        return round(n)
    except (TypeError, ValueError):
        return None


def _get_property_bool(space: Any, *property_names: str) -> Optional[bool]:
    """Get boolean property from space."""
    val = _get_property_value(space, *property_names)
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.upper() in ("TRUE", "YES", "1", "OUTWARD")
    try:
        return bool(val)
    except (TypeError, ValueError):
        return None


def _get_dimensions_from_boundary(boundary: List[List[float]]) -> Dict[str, float]:
    """Compute width_mm (min dimension) and depth_mm/length_mm (max dimension) from boundary in mm."""
    if not boundary or len(boundary) < 3:
        return {}
    xs = [p[0] for p in boundary]
    ys = [p[1] for p in boundary]
    w_x = max(xs) - min(xs)
    w_y = max(ys) - min(ys)
    min_dim = min(w_x, w_y)
    max_dim = max(w_x, w_y)
    return {"width_mm": min_dim, "depth_mm": max_dim, "length_mm": max_dim}


def _get_door_swing_and_width(space: Any, ifc_file: Any) -> Tuple[Optional[bool], Optional[float]]:
    """
    From space's BoundedBy, find IfcDoor and get SwingDirection (outward=True) and width in mm.
    Returns (opens_outward, width_mm).
    """
    opens_outward = None
    width_mm = None
    try:
        for rel in getattr(space, "BoundedBy", []) or []:
            if getattr(rel, "is_a", lambda _: False)("IfcRelSpaceBoundary"):
                elem = getattr(rel, "RelatedBuildingElement", None)
                if elem is not None and getattr(elem, "is_a", lambda _: False)("IfcDoor"):
                    swing = _get_property_value(elem, "SwingDirection", "OperationType")
                    if swing is not None:
                        s = str(swing).upper()
                        opens_outward = "OUTWARD" in s or "OUT" in s
                    w = _get_property_as_mm(elem, "Width", "ClearWidth", "OverallWidth")
                    if w is not None:
                        width_mm = w
                    if opens_outward is not None and width_mm is not None:
                        return (opens_outward, width_mm)
    except Exception:
        pass
    return (opens_outward, width_mm)


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
        
        # --- Rule-related properties from IFC (add only if present) ---
        
        # Corridor width (3:22)
        v = _get_property_as_mm(space, "Width", "ClearWidth")
        if v is not None:
            space_data["corridor_width_mm"] = v
        
        # Ramp slope (3:231) - ratio e.g. 0.0833 for 1:12
        slope_val = _get_property_value(space, "Slope", "Gradient")
        if slope_val is not None:
            try:
                r = float(slope_val)
                if r > 1 and r <= 100:
                    r = r / 100.0
                if 0 <= r <= 1:
                    space_data["ramp_slope_ratio"] = r
            except (TypeError, ValueError):
                pass
        
        # Handrail height (3:232)
        v = _get_property_as_mm(space, "HandrailHeight")
        if v is not None:
            space_data["handrail_height_mm"] = v
        
        # Bathroom door opens outward (3:241) - from door in space
        door_swing, _ = _get_door_swing_and_width(space, ifc_file)
        if door_swing is not None:
            space_data["door_opens_outward"] = door_swing
        
        # Elevator dimensions (3:143, 3:144) - from space dimensions or properties
        ew = _get_property_as_mm(space, "Width", "CabWidth")
        ed = _get_property_as_mm(space, "Depth", "CabDepth", "Length")
        if boundary and (ew is None or ed is None):
            dims = _get_dimensions_from_boundary(boundary)
            if space_type in ("elevator", "lift", "hiss") or "elevator" in space_name.lower() or "hiss" in space_name.lower():
                if ew is None and dims.get("width_mm") is not None:
                    ew = dims["width_mm"]
                if ed is None and dims.get("depth_mm") is not None:
                    ed = dims["depth_mm"]
        if ew is not None:
            space_data["elevator_width_mm"] = ew
        if ed is not None:
            space_data["elevator_depth_mm"] = ed
        
        # Elevator door width (3:144) - from door in space
        _, door_w = _get_door_swing_and_width(space, ifc_file)
        if door_w is not None and (space_type in ("elevator", "lift", "hiss") or "elevator" in space_name.lower() or "hiss" in space_name.lower()):
            space_data["elevator_door_width_mm"] = door_w
        
        # Emergency exit width (3:51)
        v = _get_property_as_mm(space, "ExitWidth", "Width", "ClearWidth")
        if v is not None:
            space_data["emergency_exit_width_mm"] = v
        
        # Emergency exit door opens outward (3:52) - from door when space is exit type
        if space_type in ("emergency_exit", "exit", "evacuation", "nödutgång", "utgång", "emergency") or "exit" in space_name.lower() or "nöd" in space_name.lower():
            door_swing_ex, _ = _get_door_swing_and_width(space, ifc_file)
            if door_swing_ex is not None:
                space_data["emergency_exit_door_opens_outward"] = door_swing_ex
        
        # Stair rise and run (3:421)
        rise = _get_property_as_mm(space, "RiserHeight", "Rise", "StepRise")
        if rise is not None:
            space_data["stair_rise_mm"] = rise
        run = _get_property_as_mm(space, "TreadDepth", "Run", "Tread", "StepRun")
        if run is not None:
            space_data["stair_run_mm"] = run
        
        # Parking dimensions (3:131, 3:132) - from space or boundary
        pw = _get_property_as_mm(space, "Width", "ParkingWidth", "ClearWidth")
        pl = _get_property_as_mm(space, "Length", "ParkingLength", "Depth")
        if boundary and (pw is None or pl is None):
            dims = _get_dimensions_from_boundary(boundary)
            if space_type in ("parking", "parking_space", "parkeringsplats", "accessible_parking") or "parking" in space_name.lower() or "parker" in space_name.lower():
                if pw is None and dims.get("width_mm") is not None:
                    pw = dims["width_mm"]
                if pl is None and dims.get("length_mm") is not None:
                    pl = dims["length_mm"]
        if pw is not None:
            space_data["parking_width_mm"] = pw
        if pl is not None:
            space_data["parking_length_mm"] = pl
        
        # Stair handrail both sides (3:411)
        both = _get_property_bool(space, "HandrailBothSides", "HandrailsBothSides")
        if both is not None:
            space_data["stair_handrail_both_sides"] = both
        
        # Stair width (3:412)
        v = _get_property_as_mm(space, "StairWidth", "Width", "ClearWidth")
        if v is not None:
            space_data["stair_width_mm"] = v
        elif boundary and space_type in ("stair", "stairs", "trappa"):
            dims = _get_dimensions_from_boundary(boundary)
            if dims.get("width_mm") is not None:
                space_data["stair_width_mm"] = dims["width_mm"]
        
        # Window sill height (3:531)
        v = _get_property_as_mm(space, "SillHeight", "WindowSillHeight", "SillHeightAboveFloor")
        if v is not None:
            space_data["window_sill_height_mm"] = v
        
        # Window opening size (3:532)
        wo_w = _get_property_as_mm(space, "OpeningWidth", "Width", "WindowWidth")
        wo_h = _get_property_as_mm(space, "OpeningHeight", "Height", "WindowHeight")
        if wo_w is not None:
            space_data["window_opening_width_mm"] = wo_w
        if wo_h is not None:
            space_data["window_opening_height_mm"] = wo_h
        
        # Tactile guidance (3:611)
        tg = _get_property_bool(space, "TactileGuidance", "TactileFloorGuidance", "TactileGuidancePresent")
        if tg is not None:
            space_data["tactile_guidance_present"] = tg
        
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
    CRITICAL: Converts from meters (IFC default) to millimeters (BFS 2024:1).
    
    Args:
        space: IfcSpace entity
        ifc_file: Opened IFC file object
        
    Returns:
        List of [x, y] coordinate pairs in MILLIMETERS or None if boundary not available
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
                    return convert_to_millimeters(unique_points)
        
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
                        return convert_to_millimeters(unique_points[:50])  # Limit to 50 points for performance
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
        List of [x, y] coordinate pairs IN METERS (will be converted later)
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