"""
NODAL - BFS 2024:1 Compliance Engine
IFC Parser Module

Extracts space data from IFC files for Swedish construction compliance checking.
Focuses on bathroom identification and space boundary extraction.

Production-ready version with:
- Unit normalization (meters ↔ millimeters)
- Model health pre-flight checks
- IfcBuildingElementProxy detection and classification
- Robust property extraction (no crashes on missing data)
- Geometry validation
- Enhanced error reporting
- Structured logging
"""

import ifcopenshell
import ifcopenshell.geom
import logging
import os
import json
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unit detection
# ---------------------------------------------------------------------------

def detect_length_unit_scale(ifc_file: Any) -> float:
    """
    Detect the length unit scale factor from IfcUnitAssignment.

    Reads the IFC file's unit assignments and determines the conversion
    factor needed to produce millimeters from native IFC coordinates.

    Returns:
        float: Scale factor to multiply native coordinates by to get millimeters.
               1000.0 if units are METRE (default/fallback),
               1.0    if units are MILLIMETRE.
    """
    try:
        unit_assignments = ifc_file.by_type("IfcUnitAssignment")
        if not unit_assignments:
            logger.warning("No IfcUnitAssignment found — assuming METRE (scale=1000.0)")
            return 1000.0

        for assignment in unit_assignments:
            units = getattr(assignment, "Units", None) or []
            for unit in units:
                if not getattr(unit, "is_a", lambda _: False)("IfcSIUnit"):
                    continue
                unit_type = getattr(unit, "UnitType", None)
                if unit_type != "LENGTHUNIT":
                    continue

                name = getattr(unit, "Name", None)
                prefix = getattr(unit, "Prefix", None)

                if name == "METRE":
                    base_scale_m = 1.0
                elif name == "FOOT":
                    base_scale_m = 0.3048
                elif name == "INCH":
                    base_scale_m = 0.0254
                else:
                    base_scale_m = 1.0

                prefix_map = {
                    "MILLI": 1e-3,
                    "CENTI": 1e-2,
                    "DECI":  1e-1,
                    "KILO":  1e3,
                    None:    1.0,
                    "":      1.0,
                }
                prefix_scale = prefix_map.get(prefix, 1.0)
                effective_m = base_scale_m * prefix_scale

                if abs(effective_m - 1.0) < 1e-9:
                    logger.info("Detected units: METRE, applying 1000x scale")
                    return 1000.0
                elif abs(effective_m - 0.001) < 1e-9:
                    logger.info("Detected units: MILLIMETRE, applying 1x scale")
                    return 1.0
                else:
                    scale = effective_m * 1000.0
                    logger.info(f"Detected units: {name} (prefix={prefix}), applying {scale}x scale")
                    return scale

    except Exception as e:
        logger.warning(f"Unit detection failed: {e} — assuming METRE (scale=1000.0)")

    return 1000.0


def convert_to_millimeters(
    coordinates: List[List[float]], unit_scale: float = 1000.0
) -> List[List[float]]:
    """
    Convert IFC coordinates to millimeters using the detected unit scale.
    """
    if unit_scale == 1.0:
        return [[x, y] for x, y in coordinates]
    return [[x * unit_scale, y * unit_scale] for x, y in coordinates]


# ---------------------------------------------------------------------------
# Model health pre-flight check
# ---------------------------------------------------------------------------

def _validate_ifc_model(ifc_file: Any) -> Tuple[bool, List[str], List[str]]:
    """
    Check if IFC file is usable before expensive processing.

    Returns:
        (is_valid, errors, warnings)
        is_valid is False if any error prevents meaningful parsing.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check 1: IfcSpace objects
    try:
        spaces = ifc_file.by_type("IfcSpace")
        if len(spaces) == 0:
            errors.append("No IfcSpace objects found in this file.")
            errors.append("FIX (Revit): File → Export → IFC → check 'Export Rooms as IfcSpace'")
            errors.append("FIX (ArchiCAD): File → Save As → IFC → Translation Settings → Export Zones as Spaces")
        elif len(spaces) >= 10_000:
            warnings.append(
                f"File contains {len(spaces)} spaces — processing may be slow. "
                "Consider filtering by storey or using batch mode."
            )
        else:
            logger.info(f"Detected {len(spaces)} IfcSpace objects")
    except Exception as e:
        errors.append(f"Could not query IfcSpace objects: {e}")

    # Check 2: Units defined
    try:
        units = ifc_file.by_type("IfcUnitAssignment")
        if len(units) == 0:
            warnings.append("No IfcUnitAssignment found — assuming meters (scale=1000)")
    except Exception:
        warnings.append("Could not query IfcUnitAssignment — assuming meters")

    # Check 3: IFC version
    try:
        schema = ifc_file.schema
        if schema not in ("IFC2X3", "IFC4", "IFC4X3"):
            warnings.append(f"Uncommon IFC schema version: {schema} — results may vary")
    except Exception:
        warnings.append("Could not determine IFC schema version")

    # Check 4: Proxy objects present
    try:
        proxies = ifc_file.by_type("IfcBuildingElementProxy")
        if len(proxies) > 0:
            warnings.append(
                f"File contains {len(proxies)} IfcBuildingElementProxy objects — "
                "these will be classified by name/description keywords."
            )
    except Exception:
        pass

    return (len(errors) == 0, errors, warnings)


# ---------------------------------------------------------------------------
# Element type classification (spaces AND proxies)
# ---------------------------------------------------------------------------

def _classify_element_type(element: Any) -> str:
    """
    Classify any IFC element (IfcSpace or IfcBuildingElementProxy) by type.

    Uses Name, Description, and LongName for keyword matching.
    Supports English and Swedish terminology.

    Returns:
        One of: "bathroom", "corridor", "ramp", "elevator", "stair",
                "parking", "emergency_exit", "other"
    """
    name      = (getattr(element, "Name",      "") or "").lower()
    desc      = (getattr(element, "Description","") or "").lower()
    longname  = (getattr(element, "LongName",  "") or "").lower()
    text = f"{name} {desc} {longname}"

    if any(kw in text for kw in ["bath", "wc", "toilet", "restroom", "badrum", "toalett"]):
        return "bathroom"
    if any(kw in text for kw in ["corridor", "korridor", "hallway", "passage", "circulation", "gang", "gång"]):
        return "corridor"
    if any(kw in text for kw in ["ramp", "rampway", "skena", "rampe"]):
        return "ramp"
    if any(kw in text for kw in ["elevator", "lift", "hiss", "elevatorer"]):
        return "elevator"
    if any(kw in text for kw in ["stair", "stairs", "trappa", "trappor", "trappehus", "staircase"]):
        return "stair"
    if any(kw in text for kw in ["parking", "parkering", "parkeringsplats", "p-plats", "parker", "garage"]):
        return "parking"
    if any(kw in text for kw in ["emergency", "exit", "nödutgång", "utgång", "evacuation", "nöd"]):
        return "emergency_exit"

    return "other"


# Thin wrapper used by _extract_space_data for IfcSpace (keeps old name working too)
def _classify_space_type(space_name: str) -> str:
    """Classify by name string only (legacy helper, kept for compatibility)."""

    class _Fake:
        Name = space_name
        Description = ""
        LongName = ""

    return _classify_element_type(_Fake())


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_ifc(file_path: str) -> Dict[str, Any]:
    """
    Parse IFC file and extract all space entities with bathroom identification.

    Args:
        file_path: Path to the IFC file

    Returns:
        Dictionary containing spaces list and summary statistics
    """
    logger.info(f"Parsing IFC file: {file_path}")

    # Validate file existence
    if not os.path.exists(file_path):
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "corridors": 0,
                "ramps": 0,
                "elevators": 0,
                "stairs": 0,
                "parking": 0,
                "other": 0,
                "errors": [f"File not found: {file_path}"],
                "warnings": [],
                "model_health": {
                    "has_spaces": False,
                    "has_units": False,
                    "ifc_version": "unknown",
                    "unit_scale_applied": 1000.0,
                },
                "proxies_reclassified": 0,
            },
        }

    try:
        ifc_file = ifcopenshell.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open IFC file: {e}")
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "corridors": 0,
                "ramps": 0,
                "elevators": 0,
                "stairs": 0,
                "parking": 0,
                "other": 0,
                "errors": [f"Failed to open IFC file: {str(e)}"],
                "warnings": [],
                "model_health": {
                    "has_spaces": False,
                    "has_units": False,
                    "ifc_version": "unknown",
                    "unit_scale_applied": 1000.0,
                },
                "proxies_reclassified": 0,
            },
        }

    # -------------------------------------------------------------------------
    # Pre-flight model health check
    # -------------------------------------------------------------------------
    is_valid, preflight_errors, preflight_warnings = _validate_ifc_model(ifc_file)

    # Determine model health metadata
    try:
        ifc_version = ifc_file.schema
    except Exception:
        ifc_version = "unknown"

    has_units = len(ifc_file.by_type("IfcUnitAssignment")) > 0

    if not is_valid:
        logger.error(f"IFC model validation failed: {preflight_errors}")
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "corridors": 0,
                "ramps": 0,
                "elevators": 0,
                "stairs": 0,
                "parking": 0,
                "other": 0,
                "errors": preflight_errors,
                "warnings": preflight_warnings,
                "model_health": {
                    "has_spaces": False,
                    "has_units": has_units,
                    "ifc_version": ifc_version,
                    "unit_scale_applied": 1000.0,
                },
                "proxies_reclassified": 0,
            },
        }

    for w in preflight_warnings:
        logger.warning(w)

    # -------------------------------------------------------------------------
    # Unit normalisation
    # -------------------------------------------------------------------------
    unit_scale: float = detect_length_unit_scale(ifc_file)

    # -------------------------------------------------------------------------
    # Extract IfcSpace objects
    # -------------------------------------------------------------------------
    try:
        spaces = ifc_file.by_type("IfcSpace")
    except Exception as e:
        logger.error(f"Failed to extract spaces: {e}")
        return {
            "spaces": [],
            "summary": {
                "total_spaces": 0,
                "bathrooms": 0,
                "corridors": 0,
                "ramps": 0,
                "elevators": 0,
                "stairs": 0,
                "parking": 0,
                "other": 0,
                "errors": [f"Failed to extract spaces: {str(e)}"],
                "warnings": preflight_warnings,
                "model_health": {
                    "has_spaces": False,
                    "has_units": has_units,
                    "ifc_version": ifc_version,
                    "unit_scale_applied": unit_scale,
                },
                "proxies_reclassified": 0,
            },
        }

    logger.info(f"Detected {len(spaces)} IfcSpace objects")

    # Also collect IfcBuildingElementProxy objects
    try:
        proxies = ifc_file.by_type("IfcBuildingElementProxy")
    except Exception:
        proxies = []

    parsed_spaces = []
    type_counts: Dict[str, int] = {
        "bathroom": 0,
        "corridor": 0,
        "ramp": 0,
        "elevator": 0,
        "stair": 0,
        "parking": 0,
        "emergency_exit": 0,
        "other": 0,
    }
    proxies_reclassified = 0
    runtime_errors: List[str] = []

    # Process IfcSpace objects
    for space in spaces:
        space_data = _extract_space_data(space, ifc_file, unit_scale)
        if space_data:
            parsed_spaces.append(space_data)
            t = space_data.get("type", "other")
            type_counts[t] = type_counts.get(t, 0) + 1

    # Process IfcBuildingElementProxy objects
    for proxy in proxies:
        proxy_type = _classify_element_type(proxy)
        if proxy_type != "other":
            proxy_data = _extract_space_data(proxy, ifc_file, unit_scale)
            if proxy_data:
                proxy_data["type"] = proxy_type  # override with proxy classification
                proxy_data["source"] = "IfcBuildingElementProxy"
                parsed_spaces.append(proxy_data)
                type_counts[proxy_type] = type_counts.get(proxy_type, 0) + 1
                proxies_reclassified += 1
                logger.info(
                    f"Proxy reclassified as '{proxy_type}': {proxy_data.get('name', 'unnamed')}"
                )

    result = {
        "spaces": parsed_spaces,
        "summary": {
            "total_spaces": len(parsed_spaces),
            "bathrooms": type_counts["bathroom"],
            "corridors": type_counts["corridor"],
            "ramps": type_counts["ramp"],
            "elevators": type_counts["elevator"],
            "stairs": type_counts["stair"],
            "parking": type_counts["parking"],
            "emergency_exits": type_counts["emergency_exit"],
            "other": type_counts["other"],
            "errors": runtime_errors,
            "warnings": preflight_warnings,
            "model_health": {
                "has_spaces": len(spaces) > 0,
                "has_units": has_units,
                "ifc_version": ifc_version,
                "unit_scale_applied": unit_scale,
            },
            "proxies_reclassified": proxies_reclassified,
            # Legacy key kept for backward compatibility
            "unit_scale_to_mm": unit_scale,
        },
    }

    logger.info(
        f"Parsing complete: {len(parsed_spaces)} spaces "
        f"({proxies_reclassified} from proxies), "
        f"bathrooms={type_counts['bathroom']}"
    )

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_property_value(space: Any, *property_names: str) -> Optional[Any]:
    """
    Get first matching IfcPropertySingleValue from space's property sets.

    Searches IsDefinedBy -> IfcRelDefinesByProperties -> IfcPropertySet -> HasProperties.
    Fully exception-safe — always returns None rather than raising.
    """
    try:
        for rel in getattr(space, "IsDefinedBy", []) or []:
            try:
                if not getattr(rel, "is_a", lambda _: False)("IfcRelDefinesByProperties"):
                    continue
                pset = getattr(rel, "RelatingPropertyDefinition", None)
                if pset is None:
                    continue
                if not getattr(pset, "is_a", lambda _: False)("IfcPropertySet"):
                    continue
                for prop in getattr(pset, "HasProperties", []) or []:
                    try:
                        if not getattr(prop, "is_a", lambda _: False)("IfcPropertySingleValue"):
                            continue
                        if getattr(prop, "Name", None) in property_names:
                            nv = getattr(prop, "NominalValue", None)
                            if nv is None:
                                return None
                            return getattr(nv, "wrappedValue", nv)
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Property extraction failed for {property_names}: {e}")

    return None


def _get_property_as_mm(
    space: Any, *property_names: str, unit_scale: float = 1000.0
) -> Optional[float]:
    """
    Get numeric property and convert to millimeters using unit_scale.
    Returns None for missing, negative, or non-numeric values.
    """
    try:
        val = _get_property_value(space, *property_names)
        if val is None:
            return None
        n = float(val)
        if n < 0:
            return None
        return round(n * unit_scale)
    except (TypeError, ValueError):
        return None
    except Exception as e:
        logger.debug(f"_get_property_as_mm failed for {property_names}: {e}")
        return None


def _get_property_bool(space: Any, *property_names: str) -> Optional[bool]:
    """Get boolean property from space."""
    try:
        val = _get_property_value(space, *property_names)
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.upper() in ("TRUE", "YES", "1", "OUTWARD")
        return bool(val)
    except (TypeError, ValueError):
        return None


def _get_dimensions_from_boundary(
    boundary: List[List[float]],
) -> Dict[str, float]:
    """Compute width_mm and depth_mm/length_mm from boundary already in mm."""
    if not boundary or len(boundary) < 3:
        return {}
    try:
        xs = [p[0] for p in boundary]
        ys = [p[1] for p in boundary]
        w_x = max(xs) - min(xs)
        w_y = max(ys) - min(ys)
        min_dim = min(w_x, w_y)
        max_dim = max(w_x, w_y)
        return {"width_mm": min_dim, "depth_mm": max_dim, "length_mm": max_dim}
    except Exception:
        return {}


def _get_door_swing_and_width(
    space: Any, ifc_file: Any, unit_scale: float = 1000.0
) -> Tuple[Optional[bool], Optional[float]]:
    """
    From space's BoundedBy, find IfcDoor and get SwingDirection (outward=True)
    and width in mm.  Returns (opens_outward, width_mm).
    """
    opens_outward = None
    width_mm = None
    try:
        for rel in getattr(space, "BoundedBy", []) or []:
            try:
                if not getattr(rel, "is_a", lambda _: False)("IfcRelSpaceBoundary"):
                    continue
                elem = getattr(rel, "RelatedBuildingElement", None)
                if elem is not None and getattr(elem, "is_a", lambda _: False)("IfcDoor"):
                    swing = _get_property_value(elem, "SwingDirection", "OperationType")
                    if swing is not None:
                        s = str(swing).upper()
                        opens_outward = "OUTWARD" in s or "OUT" in s
                    w = _get_property_as_mm(
                        elem, "Width", "ClearWidth", "OverallWidth", unit_scale=unit_scale
                    )
                    if w is not None:
                        width_mm = w
                    if opens_outward is not None and width_mm is not None:
                        return (opens_outward, width_mm)
            except Exception:
                continue
    except Exception:
        pass
    return (opens_outward, width_mm)


def _extract_boundary_safe(
    space: Any, ifc_file: Any, unit_scale: float = 1000.0
) -> Optional[List[List[float]]]:
    """
    Extract boundary with full validation.

    Returns list of [x, y] coords in mm, or None if invalid/missing.
    Replaces direct calls to _extract_boundary in production paths.
    """
    try:
        boundary = _extract_boundary(space, ifc_file, unit_scale)

        if not boundary or len(boundary) < 3:
            return None

        # Sanity check: all coordinates within ±1 km (1,000,000 mm)
        for x, y in boundary:
            if abs(x) > 1_000_000 or abs(y) > 1_000_000:
                space_id = getattr(space, "GlobalId", str(id(space)))
                logger.warning(
                    f"Suspicious coordinate ({x}, {y}) in space {space_id} — "
                    "boundary discarded"
                )
                return None

        boundary = _remove_duplicate_points(boundary)

        if len(boundary) < 3:
            return None

        return boundary

    except Exception as e:
        space_id = getattr(space, "GlobalId", str(id(space)))
        logger.error(f"Boundary extraction failed for space {space_id}: {e}")
        return None


def _extract_space_data(
    space: Any, ifc_file: Any, unit_scale: float = 1000.0
) -> Optional[Dict[str, Any]]:
    """
    Extract data from a single IfcSpace (or compatible proxy) entity.

    Args:
        space:      IfcSpace or IfcBuildingElementProxy entity
        ifc_file:   Opened IFC file object
        unit_scale: Multiplier to convert native IFC lengths → mm

    Returns:
        Dictionary with space data or None if extraction fails
    """
    try:
        space_id = (
            space.GlobalId if hasattr(space, "GlobalId") else str(space.id())
        )
        space_name = (
            space.Name
            if hasattr(space, "Name") and space.Name
            else "Unknown"
        )

        # Use full element classifier (checks Name + Description + LongName)
        space_type = _classify_element_type(space)
        floor_level = _get_floor_level(space, ifc_file, unit_scale)

        space_data: Dict[str, Any] = {
            "id": space_id,
            "name": space_name,
            "type": space_type,
            "floor_level": floor_level,
        }

        # Use safe boundary extraction with validation
        boundary = _extract_boundary_safe(space, ifc_file, unit_scale)
        if boundary:
            space_data["boundary"] = boundary

        # --- Rule-related properties (all lengths converted to mm via unit_scale) ---

        # Corridor width (3:22)
        v = _get_property_as_mm(space, "Width", "ClearWidth", unit_scale=unit_scale)
        if v is not None:
            space_data["corridor_width_mm"] = v

        # Ramp slope (3:231) — dimensionless ratio, no unit conversion
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
        v = _get_property_as_mm(space, "HandrailHeight", unit_scale=unit_scale)
        if v is not None:
            space_data["handrail_height_mm"] = v

        # Bathroom door opens outward (3:241)
        door_swing, _ = _get_door_swing_and_width(space, ifc_file, unit_scale)
        if door_swing is not None:
            space_data["door_opens_outward"] = door_swing

        # Elevator dimensions (3:143, 3:144)
        ew = _get_property_as_mm(space, "Width", "CabWidth", unit_scale=unit_scale)
        ed = _get_property_as_mm(space, "Depth", "CabDepth", "Length", unit_scale=unit_scale)
        if boundary and (ew is None or ed is None):
            dims = _get_dimensions_from_boundary(boundary)
            if (
                space_type == "elevator"
                or "elevator" in space_name.lower()
                or "hiss" in space_name.lower()
            ):
                if ew is None and dims.get("width_mm") is not None:
                    ew = dims["width_mm"]
                if ed is None and dims.get("depth_mm") is not None:
                    ed = dims["depth_mm"]
        if ew is not None:
            space_data["elevator_width_mm"] = ew
        if ed is not None:
            space_data["elevator_depth_mm"] = ed

        # Elevator door width (3:144)
        _, door_w = _get_door_swing_and_width(space, ifc_file, unit_scale)
        if door_w is not None and (
            space_type == "elevator"
            or "elevator" in space_name.lower()
            or "hiss" in space_name.lower()
        ):
            space_data["elevator_door_width_mm"] = door_w

        # Emergency exit width (3:51)
        v = _get_property_as_mm(
            space, "ExitWidth", "Width", "ClearWidth", unit_scale=unit_scale
        )
        if v is not None:
            space_data["emergency_exit_width_mm"] = v

        # Emergency exit door opens outward (3:52)
        if space_type == "emergency_exit" or "exit" in space_name.lower() or "nöd" in space_name.lower():
            door_swing_ex, _ = _get_door_swing_and_width(space, ifc_file, unit_scale)
            if door_swing_ex is not None:
                space_data["emergency_exit_door_opens_outward"] = door_swing_ex

        # Stair rise and run (3:421)
        rise = _get_property_as_mm(
            space, "RiserHeight", "Rise", "StepRise", unit_scale=unit_scale
        )
        if rise is not None:
            space_data["stair_rise_mm"] = rise
        run = _get_property_as_mm(
            space, "TreadDepth", "Run", "Tread", "StepRun", unit_scale=unit_scale
        )
        if run is not None:
            space_data["stair_run_mm"] = run

        # Parking dimensions (3:131, 3:132)
        pw = _get_property_as_mm(
            space, "Width", "ParkingWidth", "ClearWidth", unit_scale=unit_scale
        )
        pl = _get_property_as_mm(
            space, "Length", "ParkingLength", "Depth", unit_scale=unit_scale
        )
        if boundary and (pw is None or pl is None):
            dims = _get_dimensions_from_boundary(boundary)
            if (
                space_type == "parking"
                or "parking" in space_name.lower()
                or "parker" in space_name.lower()
            ):
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
        v = _get_property_as_mm(
            space, "StairWidth", "Width", "ClearWidth", unit_scale=unit_scale
        )
        if v is not None:
            space_data["stair_width_mm"] = v
        elif boundary and space_type == "stair":
            dims = _get_dimensions_from_boundary(boundary)
            if dims.get("width_mm") is not None:
                space_data["stair_width_mm"] = dims["width_mm"]

        # Window sill height (3:531)
        v = _get_property_as_mm(
            space, "SillHeight", "WindowSillHeight", "SillHeightAboveFloor",
            unit_scale=unit_scale,
        )
        if v is not None:
            space_data["window_sill_height_mm"] = v

        # Window opening size (3:532)
        wo_w = _get_property_as_mm(
            space, "OpeningWidth", "Width", "WindowWidth", unit_scale=unit_scale
        )
        wo_h = _get_property_as_mm(
            space, "OpeningHeight", "Height", "WindowHeight", unit_scale=unit_scale
        )
        if wo_w is not None:
            space_data["window_opening_width_mm"] = wo_w
        if wo_h is not None:
            space_data["window_opening_height_mm"] = wo_h

        # Tactile guidance (3:611)
        tg = _get_property_bool(
            space, "TactileGuidance", "TactileFloorGuidance", "TactileGuidancePresent"
        )
        if tg is not None:
            space_data["tactile_guidance_present"] = tg

        return space_data

    except Exception as e:
        space_id = getattr(space, "GlobalId", "unknown")
        logger.error(f"Failed to extract space data for {space_id}: {e}")
        return None


def _get_floor_level(
    space: Any, ifc_file: Any, unit_scale: float = 1000.0
) -> int:
    """
    Extract floor level from space's building storey.
    """
    three_metres_native = 3000.0 / unit_scale

    try:
        import re

        def _storey_level(storey: Any) -> Optional[int]:
            if hasattr(storey, "Elevation") and storey.Elevation is not None:
                return int(round(storey.Elevation / three_metres_native)) + 1
            if hasattr(storey, "Name") and storey.Name:
                match = re.search(r"\d+", storey.Name)
                if match:
                    return int(match.group())
            return None

        if hasattr(space, "Decomposes") and space.Decomposes:
            for rel in space.Decomposes:
                try:
                    if hasattr(rel, "RelatingObject"):
                        storey = rel.RelatingObject
                        if storey.is_a("IfcBuildingStorey"):
                            lvl = _storey_level(storey)
                            if lvl is not None:
                                return lvl
                except Exception:
                    continue

        if hasattr(space, "ContainedInStructure") and space.ContainedInStructure:
            for rel in space.ContainedInStructure:
                try:
                    if hasattr(rel, "RelatingStructure"):
                        storey = rel.RelatingStructure
                        if storey.is_a("IfcBuildingStorey"):
                            lvl = _storey_level(storey)
                            if lvl is not None:
                                return lvl
                except Exception:
                    continue

    except Exception:
        pass

    return 0


def _extract_boundary(
    space: Any, ifc_file: Any, unit_scale: float = 1000.0
) -> Optional[List[List[float]]]:
    """
    Extract boundary polygon coordinates from space and return them in mm.
    """
    try:
        # Primary: space boundary relationships
        if hasattr(space, "BoundedBy") and space.BoundedBy:
            boundary_points: List[List[float]] = []

            for boundary_rel in space.BoundedBy:
                try:
                    if hasattr(boundary_rel, "RelatedBuildingElement"):
                        boundary = boundary_rel.RelatedBuildingElement
                        if hasattr(boundary, "ConnectionGeometry"):
                            conn_geom = boundary.ConnectionGeometry
                            if hasattr(conn_geom, "SurfaceOnRelatingElement"):
                                surface = conn_geom.SurfaceOnRelatingElement
                                points = _extract_points_from_surface(surface)
                                if points:
                                    boundary_points.extend(points)
                except Exception:
                    continue

            if boundary_points:
                unique_points = _remove_duplicate_points(boundary_points)
                if len(unique_points) >= 3:
                    return convert_to_millimeters(unique_points, unit_scale)

        # Fallback: geometry kernel
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        try:
            shape = ifcopenshell.geom.create_shape(settings, space)
            if shape:
                verts = shape.geometry.verts
                points = []
                for i in range(0, len(verts), 3):
                    x, y = verts[i], verts[i + 1]
                    points.append([round(x, 3), round(y, 3)])

                if points:
                    unique_points = _remove_duplicate_points(points)
                    if len(unique_points) >= 3:
                        # Geometry kernel always outputs metres → always ×1000
                        return convert_to_millimeters(unique_points[:50], unit_scale=1000.0)
        except Exception:
            pass

        return None

    except Exception as e:
        space_id = getattr(space, "GlobalId", str(id(space)))
        logger.error(f"Failed to extract boundary for space {space_id}: {e}")
        return None


def _extract_points_from_surface(surface: Any) -> List[List[float]]:
    """
    Extract coordinate points from an IFC surface geometry.
    Returns points in native IFC units (caller applies unit_scale).
    """
    points: List[List[float]] = []
    try:
        if hasattr(surface, "OuterBoundary"):
            curve = surface.OuterBoundary
            if hasattr(curve, "Points"):
                for point in curve.Points:
                    try:
                        if hasattr(point, "Coordinates"):
                            coords = point.Coordinates
                            if len(coords) >= 2:
                                points.append([round(coords[0], 3), round(coords[1], 3)])
                    except Exception:
                        continue
    except Exception:
        pass
    return points


def _remove_duplicate_points(
    points: List[List[float]], tolerance: float = 0.01
) -> List[List[float]]:
    """Remove duplicate points from a list of [x, y] coordinate pairs."""
    if not points:
        return []
    unique = [points[0]]
    for point in points[1:]:
        is_duplicate = False
        for existing in unique:
            if (
                abs(point[0] - existing[0]) < tolerance
                and abs(point[1] - existing[1]) < tolerance
            ):
                is_duplicate = True
                break
        if not is_duplicate:
            unique.append(point)
    return unique


# ---------------------------------------------------------------------------
# CLI test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
    )

    print("=" * 70)
    print("NODAL IFC Parser - Test Run")
    print("=" * 70)
    print()

    test_file = sys.argv[1] if len(sys.argv) > 1 else "tests/sample.ifc"

    print(f"Parsing IFC file: {test_file}")
    print()

    result = parse_ifc(test_file)

    summary = result.get("summary", {})
    health  = summary.get("model_health", {})

    print("=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print(f"Total Spaces Found:     {summary.get('total_spaces', 0)}")
    print(f"  Bathrooms:            {summary.get('bathrooms', 0)}")
    print(f"  Corridors:            {summary.get('corridors', 0)}")
    print(f"  Ramps:                {summary.get('ramps', 0)}")
    print(f"  Elevators:            {summary.get('elevators', 0)}")
    print(f"  Stairs:               {summary.get('stairs', 0)}")
    print(f"  Parking:              {summary.get('parking', 0)}")
    print(f"  Emergency exits:      {summary.get('emergency_exits', 0)}")
    print(f"  Other:                {summary.get('other', 0)}")
    print(f"Proxies reclassified:   {summary.get('proxies_reclassified', 0)}")
    print()
    print(f"IFC version:            {health.get('ifc_version', 'N/A')}")
    print(f"Has units defined:      {health.get('has_units', False)}")
    print(f"Unit scale (→ mm):      {health.get('unit_scale_applied', 'N/A')}")

    errors = summary.get("errors", [])
    if errors:
        print()
        print("ERRORS:")
        for e in errors:
            print(f"  ✗ {e}")

    warnings = summary.get("warnings", [])
    if warnings:
        print()
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")

    print()

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
            pts = bathroom.get("boundary")
            if pts:
                print(f"  Boundary:     {len(pts)} points")
            else:
                print(f"  Boundary:     Not available")

    print()
    print("=" * 70)
    print("Test complete.")
    print("=" * 70)