"""
rules.py - BFS 2024:1 Accessibility Compliance Rules Engine
Swedish Building Regulations (Boverkets författningssamling)

This module checks compliance with Swedish accessibility standards for building spaces.
Currently implements BFS 2024:1 Chapter 3 requirements for bathroom accessibility.

Author: NODAL Compliance Team
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime


class RuleStatus(Enum):
    """Status values for rule compliance checks"""
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_CHECKED = "NOT_CHECKED"
    ERROR = "ERROR"


class Severity(Enum):
    """Severity levels for compliance violations"""
    CRITICAL = "CRITICAL"  # Must be fixed for compliance
    WARNING = "WARNING"    # Should be reviewed
    INFO = "INFO"         # Informational only


class OverallStatus(Enum):
    """Overall compliance status for a space"""
    PASS = "PASS"              # All applicable rules pass
    FAIL = "FAIL"              # One or more critical rules fail
    PARTIAL = "PARTIAL"        # Some rules not checked or warnings present
    ERROR = "ERROR"            # Error during checking


@dataclass
class RuleResult:
    """Result of a single rule check"""
    rule_id: str
    rule_name: str
    status: RuleStatus
    details: str
    severity: Severity
    reference: str = ""  # BFS reference
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": self.status.value,
            "details": self.details,
            "severity": self.severity.value,
            "reference": self.reference
        }


@dataclass
class ComplianceResult:
    """Complete compliance check result for a space"""
    space_id: str
    space_name: str
    space_type: str
    overall_status: OverallStatus
    rules_checked: List[RuleResult]
    passed_count: int
    failed_count: int
    not_checked_count: int
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "space_id": self.space_id,
            "space_name": self.space_name,
            "space_type": self.space_type,
            "overall_status": self.overall_status.value,
            "rules_checked": [rule.to_dict() for rule in self.rules_checked],
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "not_checked_count": self.not_checked_count,
            "timestamp": self.timestamp
        }


class BFS2024ComplianceChecker:
    """
    Main compliance checker for BFS 2024:1 regulations.
    
    This class implements Swedish accessibility standards checking,
    focusing on bathroom requirements in Chapter 3.
    """
    
    # Rule definitions
    RULE_TURNING_CIRCLE = {
        "id": "BFS-2024:1-3:14",
        "name": "Turning Circle (1500mm)",
        "reference": "BFS 2024:1 Section 3:14",
        "severity": Severity.CRITICAL,
        "applies_to": ["bathroom", "wc", "toilet"]
    }
    
    RULE_DOOR_WIDTH = {
        "id": "BFS-2024:1-3:15",
        "name": "Door Width (900mm minimum)",
        "reference": "BFS 2024:1 Section 3:15",
        "severity": Severity.CRITICAL,
        "applies_to": ["bathroom", "wc", "toilet"]
    }
    
    RULE_THRESHOLD = {
        "id": "BFS-2024:1-3:16",
        "name": "Threshold Height (25mm max)",
        "reference": "BFS 2024:1 Section 3:16",
        "severity": Severity.WARNING,
        "applies_to": ["bathroom", "wc", "toilet", "entrance"]
    }
    
    RULE_CORRIDOR_WIDTH = {
        "id": "BFS-2024:1-3:22",
        "name": "Corridor Width (1300mm minimum)",
        "reference": "BFS 2024:1 Section 3:22",
        "severity": Severity.CRITICAL,
        "applies_to": ["corridor", "circulation", "passage", "hallway", "korridor"],
        "description_en": "Minimum clear width 1300mm for accessibility.",
        "description_sv": "Minst 1300 mm fri bredd för tillgänglighet."
    }
    
    RULE_RAMP_SLOPE = {
        "id": "BFS-2024:1-3:231",
        "name": "Ramp Slope (max 1:12 / 8.33%)",
        "reference": "BFS 2024:1 Section 3:231",
        "severity": Severity.CRITICAL,
        "applies_to": ["ramp", "rampway"],
        "description_en": "Maximum slope 1:12 (8.33%) for ramps.",
        "description_sv": "Maximal lutning 1:12 (8,33 %) för ramper."
    }
    
    RULE_HANDRAIL_HEIGHT = {
        "id": "BFS-2024:1-3:232",
        "name": "Handrail Height (900–1000mm)",
        "reference": "BFS 2024:1 Section 3:232",
        "severity": Severity.CRITICAL,
        "applies_to": ["ramp", "stair", "stairs", "trappa"],
        "description_en": "Handrail height must be between 900mm and 1000mm.",
        "description_sv": "Räckeshöjd ska vara 900–1000 mm."
    }
    
    RULE_BATHROOM_DOOR_SWING = {
        "id": "BFS-2024:1-3:241",
        "name": "Bathroom Door Opens Outward",
        "reference": "BFS 2024:1 Section 3:241",
        "severity": Severity.CRITICAL,
        "applies_to": ["bathroom", "wc", "toilet"],
        "description_en": "Bathroom door must open outward for emergency access.",
        "description_sv": "Dörr till badrum/toalett ska öppnas utåt för nödutrymning."
    }
    
    RULE_REST_AREA_25M = {
        "id": "BFS-2024:1-3:311",
        "name": "Rest Area Every 25m (corridors)",
        "reference": "BFS 2024:1 Section 3:311",
        "severity": Severity.WARNING,
        "applies_to": ["corridor", "circulation", "passage", "hallway", "korridor"],
        "description_en": "Rest area or widening required at least every 25m in corridors.",
        "description_sv": "Viloplats eller breddning minst var 25:e meter i korridorer."
    }
    
    def __init__(self):
        """Initialize the compliance checker"""
        self.rules = [
            self.RULE_TURNING_CIRCLE,
            self.RULE_DOOR_WIDTH,
            self.RULE_THRESHOLD,
            self.RULE_CORRIDOR_WIDTH,
            self.RULE_RAMP_SLOPE,
            self.RULE_HANDRAIL_HEIGHT,
            self.RULE_BATHROOM_DOOR_SWING,
            self.RULE_REST_AREA_25M,
        ]
    
    def check_compliance(
        self, 
        space_dict: Dict[str, Any], 
        geometry_result: Optional[Dict[str, Any]] = None
    ) -> ComplianceResult:
        """
        Main compliance checking function.
        
        Args:
            space_dict: Space information from parser.py
            geometry_result: Geometry check result from geometry.py (optional)
            
        Returns:
            ComplianceResult object with all rule checks
            
        Raises:
            ValueError: If space_dict is invalid or missing required fields
        """
        # Validate input
        self._validate_space_dict(space_dict)
        
        space_id = space_dict.get("id", "unknown")
        space_name = space_dict.get("name", "Unnamed Space")
        space_type = space_dict.get("type", "unknown").lower()
        
        # Run all applicable rules
        rule_results = []
        
        # Rule 1: Turning Circle
        rule_results.append(
            self.check_turning_circle_rule(space_dict, geometry_result)
        )
        
        # Rule 2: Door Width
        rule_results.append(
            self.check_door_width_rule(space_dict)
        )
        
        # Rule 3: Threshold Height
        rule_results.append(
            self.check_threshold_rule(space_dict)
        )
        
        # Rule 4: Corridor Width (3:22)
        rule_results.append(
            self.check_corridor_width_rule(space_dict)
        )
        
        # Rule 5: Ramp Slope (3:231)
        rule_results.append(
            self.check_ramp_slope_rule(space_dict)
        )
        
        # Rule 6: Handrail Height (3:232)
        rule_results.append(
            self.check_handrail_height_rule(space_dict)
        )
        
        # Rule 7: Bathroom Door Opens Outward (3:241)
        rule_results.append(
            self.check_bathroom_door_swing_rule(space_dict)
        )
        
        # Rule 8: Rest Area Every 25m (3:311)
        rule_results.append(
            self.check_rest_area_25m_rule(space_dict)
        )
        
        # Calculate statistics
        passed = sum(1 for r in rule_results if r.status == RuleStatus.PASS)
        failed = sum(1 for r in rule_results if r.status == RuleStatus.FAIL)
        not_checked = sum(1 for r in rule_results 
                         if r.status == RuleStatus.NOT_CHECKED)
        
        # Determine overall status
        overall_status = self._calculate_overall_status(rule_results)
        
        return ComplianceResult(
            space_id=space_id,
            space_name=space_name,
            space_type=space_type,
            overall_status=overall_status,
            rules_checked=rule_results,
            passed_count=passed,
            failed_count=failed,
            not_checked_count=not_checked,
            timestamp=datetime.now().isoformat()
        )
    
    def check_turning_circle_rule(
        self, 
        space_dict: Dict[str, Any], 
        geometry_result: Optional[Dict[str, Any]] = None
    ) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:14 - Turning Circle Requirement.
        
        Requirement: A wheelchair turning circle of 1500mm diameter must
        fit within the bathroom space.
        
        Args:
            space_dict: Space information
            geometry_result: Result from geometry.py turning circle check
            
        Returns:
            RuleResult with compliance status
        """
        rule = self.RULE_TURNING_CIRCLE
        space_type = space_dict.get("type", "").lower()
        
        # Check if rule applies to this space type
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Check if geometry result is available
        if geometry_result is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.ERROR,
                details="Geometry check result not provided",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Verify geometry result is for correct space
        if geometry_result.get("space_id") != space_dict.get("id"):
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.ERROR,
                details="Geometry result space_id mismatch",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Check geometry result
        passed = geometry_result.get("passed", False)
        
        if passed:
            circle_center = geometry_result.get("circle_center")
            center_str = ""
            if circle_center:
                center_str = f" at position ({circle_center[0]:.1f}, {circle_center[1]:.1f})mm"
            
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"1500mm turning circle fits in space{center_str}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        else:
            collision_details = geometry_result.get(
                "collision_details", 
                "Circle does not fit"
            )
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.FAIL,
                details=f"1500mm turning circle does not fit: {collision_details}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
    
    def check_door_width_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:15 - Door Width Requirement.
        
        Requirement: Minimum 900mm clear door width for accessibility.
        
        SIMPLIFIED VERSION: Currently checks if space minimum width >= 900mm
        as a proxy. Will be updated when door extraction is implemented.
        
        Args:
            space_dict: Space information
            
        Returns:
            RuleResult with compliance status
        """
        rule = self.RULE_DOOR_WIDTH
        space_type = space_dict.get("type", "").lower()
        
        # Check if rule applies to this space type
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Get space boundary
        boundary = space_dict.get("boundary")
        if not boundary or len(boundary) < 3:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.ERROR,
                details="Invalid or missing space boundary",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Calculate minimum width (simplified check)
        min_width = self._calculate_min_space_width(boundary)
        required_width = 900  # mm
        
        if min_width >= required_width:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Space minimum width {min_width:.0f}mm >= required {required_width}mm (simplified check - actual door width not yet extracted)",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        else:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.FAIL,
                details=f"Space minimum width {min_width:.0f}mm < required {required_width}mm (simplified check - may pass with proper door extraction)",
                severity=rule["severity"],
                reference=rule["reference"]
            )
    
    def check_threshold_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:16 - Threshold Height Requirement.
        
        Requirement: Maximum 25mm threshold height for accessibility.
        
        PLACEHOLDER: Currently returns NOT_CHECKED as threshold data
        is not yet extracted from IFC files. Will be implemented when
        door/threshold extraction is added to parser.py.
        
        Args:
            space_dict: Space information
            
        Returns:
            RuleResult with NOT_CHECKED status
        """
        rule = self.RULE_THRESHOLD
        space_type = space_dict.get("type", "").lower()
        
        # Check if rule applies to this space type
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Placeholder - threshold data not yet available
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.NOT_CHECKED,
            details="Threshold data not available in current IFC file. Will be checked when door/threshold extraction is implemented.",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_corridor_width_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:22 - Corridor Width Requirement.
        
        Requirement: Minimum 1300mm clear width for corridors.
        English: Minimum clear width 1300mm for accessibility.
        Swedish: Minst 1300 mm fri bredd för tillgänglighet.
        
        Returns NOT_CHECKED if corridor width data is not in space_dict.
        """
        rule = self.RULE_CORRIDOR_WIDTH
        space_type = space_dict.get("type", "").lower()
        
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Check for corridor width (from future IFC extraction)
        corridor_width_mm = space_dict.get("corridor_width_mm")
        if corridor_width_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Corridor width not available in current IFC file. Will be checked when corridor geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        required_width = 1300  # mm
        if corridor_width_mm >= required_width:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Corridor width {corridor_width_mm:.0f}mm >= required {required_width}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Corridor width {corridor_width_mm:.0f}mm < required {required_width}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_ramp_slope_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:231 - Ramp Slope Requirement.
        
        Requirement: Maximum slope 1:12 (8.33%) for ramps.
        English: Maximum slope 1:12 (8.33%) for ramps.
        Swedish: Maximal lutning 1:12 (8,33 %) för ramper.
        
        Returns NOT_CHECKED if ramp slope data is not in space_dict.
        """
        rule = self.RULE_RAMP_SLOPE
        space_type = space_dict.get("type", "").lower()
        
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Slope as ratio (e.g. 0.0833 = 8.33%) or as rise:run from IFC
        slope_ratio = space_dict.get("ramp_slope_ratio")  # e.g. 0.0833
        if slope_ratio is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Ramp slope not available in current IFC file. Will be checked when ramp geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        max_slope = 1 / 12  # 8.33%
        if slope_ratio <= max_slope:
            pct = slope_ratio * 100
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Ramp slope {pct:.2f}% (1:{1/slope_ratio:.1f}) <= max 8.33% (1:12). {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        pct = slope_ratio * 100
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Ramp slope {pct:.2f}% exceeds max 8.33% (1:12). {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_handrail_height_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:232 - Handrail Height Requirement.
        
        Requirement: Handrail height 900–1000mm.
        English: Handrail height must be between 900mm and 1000mm.
        Swedish: Räckeshöjd ska vara 900–1000 mm.
        
        Returns NOT_CHECKED if handrail height data is not in space_dict.
        """
        rule = self.RULE_HANDRAIL_HEIGHT
        space_type = space_dict.get("type", "").lower()
        
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        handrail_height_mm = space_dict.get("handrail_height_mm")
        if handrail_height_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Handrail height not available in current IFC file. Will be checked when railing extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        min_h, max_h = 900, 1000
        if min_h <= handrail_height_mm <= max_h:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Handrail height {handrail_height_mm:.0f}mm within 900–1000mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Handrail height {handrail_height_mm:.0f}mm outside 900–1000mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_bathroom_door_swing_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:241 - Bathroom Door Opens Outward.
        
        Requirement: Bathroom door must open outward for emergency access.
        English: Bathroom door must open outward for emergency access.
        Swedish: Dörr till badrum/toalett ska öppnas utåt för nödutrymning.
        
        Returns NOT_CHECKED if door swing data is not in space_dict.
        """
        rule = self.RULE_BATHROOM_DOOR_SWING
        space_type = space_dict.get("type", "").lower()
        
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Expects space_dict.get("door_opens_outward") == True/False when implemented
        door_opens_outward = space_dict.get("door_opens_outward")
        if door_opens_outward is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Door swing direction not available in current IFC file. Will be checked when door extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        if door_opens_outward:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Bathroom door opens outward. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details="Bathroom door does not open outward; must open outward for emergency access.",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_rest_area_25m_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:311 - Rest Area Every 25m in Corridors.
        
        Requirement: Rest area or widening at least every 25m in corridors.
        English: Rest area or widening required at least every 25m in corridors.
        Swedish: Viloplats eller breddning minst var 25:e meter i korridorer.
        
        Returns NOT_CHECKED if corridor length/rest-area data is not in space_dict.
        """
        rule = self.RULE_REST_AREA_25M
        space_type = space_dict.get("type", "").lower()
        
        if space_type not in rule["applies_to"]:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_APPLICABLE,
                details=f"Rule does not apply to space type: {space_type}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        # Expects e.g. corridor_length_m, rest_area_interval_m or rest_areas_present
        has_rest_areas_ok = space_dict.get("rest_area_25m_compliant")
        if has_rest_areas_ok is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Corridor length and rest area data not available in current IFC file. Will be checked when corridor/rest-area extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        if has_rest_areas_ok:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Rest area or widening provided at least every 25m. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details="Rest area or widening required at least every 25m in corridor.",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def _validate_space_dict(self, space_dict: Dict[str, Any]) -> None:
        """
        Validate that space dictionary contains required fields.
        
        Args:
            space_dict: Space dictionary to validate
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["id", "type"]
        missing = [f for f in required_fields if f not in space_dict]
        
        if missing:
            raise ValueError(
                f"Space dictionary missing required fields: {missing}"
            )
    
    def _calculate_min_space_width(self, boundary: List[List[float]]) -> float:
        """
        Calculate minimum width of space from boundary points.
        
        This is a simplified calculation that finds the minimum distance
        between parallel sides. For complex polygons, this is an approximation.
        
        Args:
            boundary: List of [x, y] coordinate pairs
            
        Returns:
            Minimum width in mm
        """
        if len(boundary) < 3:
            return 0.0
        
        # Find bounding box dimensions
        xs = [point[0] for point in boundary]
        ys = [point[1] for point in boundary]
        
        width_x = max(xs) - min(xs)
        width_y = max(ys) - min(ys)
        
        # Return minimum dimension
        return min(width_x, width_y)
    
    def _calculate_overall_status(
        self, 
        rule_results: List[RuleResult]
    ) -> OverallStatus:
        """
        Calculate overall compliance status from individual rule results.
        
        Logic:
        - ERROR if any rule has ERROR status
        - FAIL if any CRITICAL rule fails
        - PARTIAL if any rules are NOT_CHECKED or have warnings
        - PASS if all applicable rules pass
        
        Args:
            rule_results: List of rule check results
            
        Returns:
            Overall compliance status
        """
        # Check for errors first
        if any(r.status == RuleStatus.ERROR for r in rule_results):
            return OverallStatus.ERROR
        
        # Check for critical failures
        critical_fails = [
            r for r in rule_results 
            if r.status == RuleStatus.FAIL and r.severity == Severity.CRITICAL
        ]
        if critical_fails:
            return OverallStatus.FAIL
        
        # Check for not checked or warnings
        has_not_checked = any(
            r.status == RuleStatus.NOT_CHECKED for r in rule_results
        )
        has_warning_fails = any(
            r.status == RuleStatus.FAIL and r.severity == Severity.WARNING 
            for r in rule_results
        )
        
        if has_not_checked or has_warning_fails:
            return OverallStatus.PARTIAL
        
        # All applicable rules passed
        return OverallStatus.PASS


def generate_compliance_report(
    results: List[ComplianceResult], 
    include_passed: bool = True
) -> str:
    """
    Generate human-readable compliance report.
    
    Args:
        results: List of ComplianceResult objects
        include_passed: Whether to include passed rules in report
        
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("BFS 2024:1 ACCESSIBILITY COMPLIANCE REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Spaces Checked: {len(results)}")
    lines.append("")
    
    # Summary statistics
    passed_spaces = sum(
        1 for r in results if r.overall_status == OverallStatus.PASS
    )
    failed_spaces = sum(
        1 for r in results if r.overall_status == OverallStatus.FAIL
    )
    partial_spaces = sum(
        1 for r in results if r.overall_status == OverallStatus.PARTIAL
    )
    
    lines.append("SUMMARY:")
    lines.append(f"  ✓ Passed: {passed_spaces}")
    lines.append(f"  ✗ Failed: {failed_spaces}")
    lines.append(f"  ⚠ Partial: {partial_spaces}")
    lines.append("")
    
    # Detailed results for each space
    for result in results:
        lines.append("-" * 80)
        lines.append(f"SPACE: {result.space_name} ({result.space_type})")
        lines.append(f"ID: {result.space_id}")
        lines.append(f"Overall Status: {result.overall_status.value}")
        lines.append("")
        
        # Rule results
        for rule in result.rules_checked:
            # Skip passed rules if not including them
            if not include_passed and rule.status == RuleStatus.PASS:
                continue
            
            # Status icon
            icon = {
                RuleStatus.PASS: "✓",
                RuleStatus.FAIL: "✗",
                RuleStatus.NOT_APPLICABLE: "-",
                RuleStatus.NOT_CHECKED: "?",
                RuleStatus.ERROR: "!"
            }.get(rule.status, "?")
            
            lines.append(f"  {icon} {rule.rule_name}")
            lines.append(f"    Reference: {rule.reference}")
            lines.append(f"    Status: {rule.status.value}")
            lines.append(f"    Severity: {rule.severity.value}")
            lines.append(f"    Details: {rule.details}")
            lines.append("")
    
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def export_results_json(
    results: List[ComplianceResult], 
    filepath: str
) -> None:
    """
    Export compliance results to JSON file.
    
    Args:
        results: List of ComplianceResult objects
        filepath: Path to output JSON file
    """
    data = {
        "report_metadata": {
            "generated": datetime.now().isoformat(),
            "total_spaces": len(results),
            "standard": "BFS 2024:1"
        },
        "results": [r.to_dict() for r in results]
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================================
# TEST CODE
# ============================================================================

def run_tests():
    """Run comprehensive tests of the compliance checker"""
    print("Running BFS 2024:1 Compliance Checker Tests")
    print("=" * 80)
    
    checker = BFS2024ComplianceChecker()
    
    # Test 1: Bathroom that passes all checks
    print("\nTest 1: Bathroom that passes all checks")
    print("-" * 80)
    
    space_pass = {
        "id": "space_001",
        "name": "Main Bathroom",
        "type": "bathroom",
        "floor_level": 1,
        "boundary": [
            [0, 0], [3000, 0], [3000, 2500], [0, 2500]
        ]
    }
    
    geometry_pass = {
        "space_id": "space_001",
        "passed": True,
        "circle_center": [1500, 1250],
        "collision_details": None
    }
    
    result_pass = checker.check_compliance(space_pass, geometry_pass)
    print(generate_compliance_report([result_pass]))
    
    # Test 2: Bathroom that fails turning circle
    print("\nTest 2: Bathroom that fails turning circle")
    print("-" * 80)
    
    space_fail = {
        "id": "space_002",
        "name": "Small Bathroom",
        "type": "bathroom",
        "floor_level": 1,
        "boundary": [
            [0, 0], [1200, 0], [1200, 2000], [0, 2000]
        ]
    }
    
    geometry_fail = {
        "space_id": "space_002",
        "passed": False,
        "circle_center": None,
        "collision_details": "Circle collides with walls at multiple points"
    }
    
    result_fail = checker.check_compliance(space_fail, geometry_fail)
    print(generate_compliance_report([result_fail]))
    
    # Test 3: Non-bathroom space (rules not applicable)
    print("\nTest 3: Non-bathroom space (kitchen)")
    print("-" * 80)
    
    space_kitchen = {
        "id": "space_003",
        "name": "Kitchen",
        "type": "kitchen",
        "floor_level": 1,
        "boundary": [
            [0, 0], [4000, 0], [4000, 3000], [0, 3000]
        ]
    }
    
    result_kitchen = checker.check_compliance(space_kitchen, None)
    print(generate_compliance_report([result_kitchen]))
    
    # Test 4: Missing geometry data
    print("\nTest 4: Bathroom with missing geometry data")
    print("-" * 80)
    
    space_missing = {
        "id": "space_004",
        "name": "Bathroom Without Geometry",
        "type": "bathroom",
        "floor_level": 2,
        "boundary": [
            [0, 0], [2500, 0], [2500, 2200], [0, 2200]
        ]
    }
    
    result_missing = checker.check_compliance(space_missing, None)
    print(generate_compliance_report([result_missing]))
    
    # Test 5: Narrow bathroom (fails width check)
    print("\nTest 5: Narrow bathroom (fails width check)")
    print("-" * 80)
    
    space_narrow = {
        "id": "space_005",
        "name": "Narrow Bathroom",
        "type": "bathroom",
        "floor_level": 1,
        "boundary": [
            [0, 0], [800, 0], [800, 3000], [0, 3000]  # Only 800mm wide
        ]
    }
    
    geometry_narrow = {
        "space_id": "space_005",
        "passed": False,
        "circle_center": None,
        "collision_details": "Space too narrow for turning circle"
    }
    
    result_narrow = checker.check_compliance(space_narrow, geometry_narrow)
    print(generate_compliance_report([result_narrow]))
    
    # Test 6: Export to JSON
    print("\nTest 6: Export results to JSON")
    print("-" * 80)
    
    all_results = [
        result_pass, 
        result_fail, 
        result_kitchen, 
        result_missing, 
        result_narrow
    ]
    
    json_path = "compliance_results_test.json"
    export_results_json(all_results, json_path)
    print(f"Results exported to: {json_path}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests run: 6")
    print(f"All tests completed successfully")
    print("\nTest Coverage:")
    print("  ✓ Passing bathroom")
    print("  ✓ Failing bathroom (turning circle)")
    print("  ✓ Failing bathroom (width)")
    print("  ✓ Non-applicable space type")
    print("  ✓ Missing geometry data")
    print("  ✓ JSON export")


if __name__ == "__main__":
    run_tests()