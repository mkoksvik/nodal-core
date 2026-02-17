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
    
    RULE_ELEVATOR_SIZE = {
        "id": "BFS-2024:1-3:143",
        "name": "Elevator Minimum Size (1100mm x 1400mm)",
        "reference": "BFS 2024:1 Section 3:143",
        "severity": Severity.CRITICAL,
        "applies_to": ["elevator", "lift", "hiss"],
        "description_en": "Elevator cabin minimum clear dimensions 1100mm x 1400mm.",
        "description_sv": "Hisskupans minsta fria mått 1100 mm x 1400 mm."
    }
    
    RULE_ELEVATOR_DOOR_WIDTH = {
        "id": "BFS-2024:1-3:144",
        "name": "Elevator Door Width (800mm minimum)",
        "reference": "BFS 2024:1 Section 3:144",
        "severity": Severity.CRITICAL,
        "applies_to": ["elevator", "lift", "hiss"],
        "description_en": "Elevator door clear width minimum 800mm.",
        "description_sv": "Hissdörrens fria bredd minst 800 mm."
    }
    
    RULE_EMERGENCY_EXIT_WIDTH = {
        "id": "BFS-2024:1-3:51",
        "name": "Emergency Exit Width (900mm minimum)",
        "reference": "BFS 2024:1 Section 3:51",
        "severity": Severity.CRITICAL,
        "applies_to": ["emergency_exit", "exit", "nödutgång", "utgång", "emergency", "evacuation"],
        "description_en": "Emergency exit clear width minimum 900mm.",
        "description_sv": "Nödutgångens fria bredd minst 900 mm."
    }
    
    RULE_EMERGENCY_EXIT_DOOR_SWING = {
        "id": "BFS-2024:1-3:52",
        "name": "Emergency Exit Door Opens Outward",
        "reference": "BFS 2024:1 Section 3:52",
        "severity": Severity.CRITICAL,
        "applies_to": ["emergency_exit", "exit", "nödutgång", "utgång", "emergency", "evacuation"],
        "description_en": "Emergency exit door must open outward for evacuation.",
        "description_sv": "Nödutgångens dörr ska öppnas utåt för evakuering."
    }
    
    RULE_STAIR_DIMENSIONS = {
        "id": "BFS-2024:1-3:421",
        "name": "Stair Step Height (max 150mm) and Depth (min 300mm)",
        "reference": "BFS 2024:1 Section 3:421",
        "severity": Severity.CRITICAL,
        "applies_to": ["stair", "stairs", "trappa"],
        "description_en": "Step rise maximum 150mm, step run minimum 300mm.",
        "description_sv": "Steghöjden max 150 mm, stegbredden minst 300 mm."
    }
    
    RULE_PARKING_WIDTH = {
        "id": "BFS-2024:1-3:131",
        "name": "Accessible Parking Space Width (3600mm minimum)",
        "reference": "BFS 2024:1 Section 3:131",
        "severity": Severity.CRITICAL,
        "applies_to": ["parking", "parkeringsplats", "accessible_parking", "parking_space"],
        "description_en": "Accessible parking space minimum clear width 3600mm.",
        "description_sv": "Tillgänglig parkeringsplats minst 3600 mm bred."
    }
    
    RULE_PARKING_LENGTH = {
        "id": "BFS-2024:1-3:132",
        "name": "Parking Space Length (5000mm minimum)",
        "reference": "BFS 2024:1 Section 3:132",
        "severity": Severity.CRITICAL,
        "applies_to": ["parking", "parkeringsplats", "accessible_parking", "parking_space"],
        "description_en": "Parking space length minimum 5000mm.",
        "description_sv": "Parkeringsplatsens längd minst 5000 mm."
    }
    
    RULE_STAIR_HANDRAIL_BOTH = {
        "id": "BFS-2024:1-3:411",
        "name": "Stair Handrail Both Sides Required",
        "reference": "BFS 2024:1 Section 3:411",
        "severity": Severity.CRITICAL,
        "applies_to": ["stair", "stairs", "trappa"],
        "description_en": "Stairs must have handrails on both sides.",
        "description_sv": "Trappor ska ha räcken på båda sidor."
    }
    
    RULE_STAIR_WIDTH = {
        "id": "BFS-2024:1-3:412",
        "name": "Stair Width (1200mm minimum)",
        "reference": "BFS 2024:1 Section 3:412",
        "severity": Severity.CRITICAL,
        "applies_to": ["stair", "stairs", "trappa"],
        "description_en": "Stair clear width minimum 1200mm.",
        "description_sv": "Trappans fria bredd minst 1200 mm."
    }
    
    RULE_WINDOW_SILL_HEIGHT = {
        "id": "BFS-2024:1-3:531",
        "name": "Window Sill Height (max 600mm from floor)",
        "reference": "BFS 2024:1 Section 3:531",
        "severity": Severity.WARNING,
        "applies_to": ["window", "fönster", "room", "rum", "space"],
        "description_en": "Window sill height maximum 600mm from floor level.",
        "description_sv": "Fönsterbrädans höjd max 600 mm från golvnivå."
    }
    
    RULE_WINDOW_OPENING_SIZE = {
        "id": "BFS-2024:1-3:532",
        "name": "Window Opening (min 900mm x 1200mm)",
        "reference": "BFS 2024:1 Section 3:532",
        "severity": Severity.WARNING,
        "applies_to": ["window", "fönster", "room", "rum", "space"],
        "description_en": "Window opening minimum 900mm x 1200mm for emergency access.",
        "description_sv": "Fönsteröppning minst 900 mm x 1200 mm för nödutrymning."
    }
    
    RULE_TACTILE_GUIDANCE = {
        "id": "BFS-2024:1-3:611",
        "name": "Tactile Floor Guidance (visually impaired)",
        "reference": "BFS 2024:1 Section 3:611",
        "severity": Severity.WARNING,
        "applies_to": ["corridor", "circulation", "passage", "hallway", "korridor", "public", "offentlig", "lobby", "entrance"],
        "description_en": "Tactile floor guidance required for visually impaired in public areas.",
        "description_sv": "Taktil golvledning krävs för synskadade i offentliga områden."
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
            self.RULE_ELEVATOR_SIZE,
            self.RULE_ELEVATOR_DOOR_WIDTH,
            self.RULE_EMERGENCY_EXIT_WIDTH,
            self.RULE_EMERGENCY_EXIT_DOOR_SWING,
            self.RULE_STAIR_DIMENSIONS,
            self.RULE_PARKING_WIDTH,
            self.RULE_PARKING_LENGTH,
            self.RULE_STAIR_HANDRAIL_BOTH,
            self.RULE_STAIR_WIDTH,
            self.RULE_WINDOW_SILL_HEIGHT,
            self.RULE_WINDOW_OPENING_SIZE,
            self.RULE_TACTILE_GUIDANCE,
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
        
        # Rule 9: Elevator Minimum Size (3:143)
        rule_results.append(
            self.check_elevator_size_rule(space_dict)
        )
        
        # Rule 10: Elevator Door Width (3:144)
        rule_results.append(
            self.check_elevator_door_width_rule(space_dict)
        )
        
        # Rule 11: Emergency Exit Width (3:51)
        rule_results.append(
            self.check_emergency_exit_width_rule(space_dict)
        )
        
        # Rule 12: Emergency Exit Door Opens Outward (3:52)
        rule_results.append(
            self.check_emergency_exit_door_swing_rule(space_dict)
        )
        
        # Rule 13: Stair Step Dimensions (3:421)
        rule_results.append(
            self.check_stair_dimensions_rule(space_dict)
        )
        
        # Rule 14: Accessible Parking Width (3:131)
        rule_results.append(
            self.check_parking_width_rule(space_dict)
        )
        
        # Rule 15: Parking Space Length (3:132)
        rule_results.append(
            self.check_parking_length_rule(space_dict)
        )
        
        # Rule 16: Stair Handrail Both Sides (3:411)
        rule_results.append(
            self.check_stair_handrail_both_rule(space_dict)
        )
        
        # Rule 17: Stair Width (3:412)
        rule_results.append(
            self.check_stair_width_rule(space_dict)
        )
        
        # Rule 18: Window Sill Height (3:531)
        rule_results.append(
            self.check_window_sill_height_rule(space_dict)
        )
        
        # Rule 19: Window Opening Size (3:532)
        rule_results.append(
            self.check_window_opening_size_rule(space_dict)
        )
        
        # Rule 20: Tactile Floor Guidance (3:611)
        rule_results.append(
            self.check_tactile_guidance_rule(space_dict)
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
    
    def check_elevator_size_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:143 - Elevator Minimum Size.
        
        Requirement: Elevator cabin minimum 1100mm x 1400mm clear dimensions.
        English: Elevator cabin minimum clear dimensions 1100mm x 1400mm.
        Swedish: Hisskupans minsta fria mått 1100 mm x 1400 mm.
        
        Returns NOT_CHECKED if elevator dimensions are not in space_dict.
        """
        rule = self.RULE_ELEVATOR_SIZE
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
        
        width_mm = space_dict.get("elevator_width_mm")
        depth_mm = space_dict.get("elevator_depth_mm")
        if width_mm is None or depth_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Elevator cabin dimensions not available in current IFC file. Will be checked when elevator geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        min_width, min_depth = 1100, 1400
        if width_mm >= min_width and depth_mm >= min_depth:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Elevator size {width_mm:.0f}mm x {depth_mm:.0f}mm >= required {min_width}mm x {min_depth}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        issues = []
        if width_mm < min_width:
            issues.append(f"width {width_mm:.0f}mm < {min_width}mm")
        if depth_mm < min_depth:
            issues.append(f"depth {depth_mm:.0f}mm < {min_depth}mm")
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Elevator size insufficient: {'; '.join(issues)}. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_elevator_door_width_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:144 - Elevator Door Width.
        
        Requirement: Elevator door clear width minimum 800mm.
        English: Elevator door clear width minimum 800mm.
        Swedish: Hissdörrens fria bredd minst 800 mm.
        
        Returns NOT_CHECKED if elevator door width is not in space_dict.
        """
        rule = self.RULE_ELEVATOR_DOOR_WIDTH
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
        
        door_width_mm = space_dict.get("elevator_door_width_mm")
        if door_width_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Elevator door width not available in current IFC file. Will be checked when elevator door extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        required = 800
        if door_width_mm >= required:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Elevator door width {door_width_mm:.0f}mm >= required {required}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Elevator door width {door_width_mm:.0f}mm < required {required}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_emergency_exit_width_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:51 - Emergency Exit Width.
        
        Requirement: Emergency exit clear width minimum 900mm.
        English: Emergency exit clear width minimum 900mm.
        Swedish: Nödutgångens fria bredd minst 900 mm.
        
        Returns NOT_CHECKED if emergency exit width is not in space_dict.
        """
        rule = self.RULE_EMERGENCY_EXIT_WIDTH
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
        
        width_mm = space_dict.get("emergency_exit_width_mm")
        if width_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Emergency exit width not available in current IFC file. Will be checked when exit geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        required = 900
        if width_mm >= required:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Emergency exit width {width_mm:.0f}mm >= required {required}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Emergency exit width {width_mm:.0f}mm < required {required}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_emergency_exit_door_swing_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:52 - Emergency Exit Door Opens Outward.
        
        Requirement: Emergency exit door must open outward for evacuation.
        English: Emergency exit door must open outward for evacuation.
        Swedish: Nödutgångens dörr ska öppnas utåt för evakuering.
        
        Returns NOT_CHECKED if door swing data is not in space_dict.
        """
        rule = self.RULE_EMERGENCY_EXIT_DOOR_SWING
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
        
        opens_outward = space_dict.get("emergency_exit_door_opens_outward")
        if opens_outward is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Emergency exit door swing direction not available in current IFC file. Will be checked when exit door extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        if opens_outward:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Emergency exit door opens outward. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details="Emergency exit door does not open outward; must open outward for evacuation.",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_stair_dimensions_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:421 - Stair Step Height and Depth.
        
        Requirement: Step rise (height) maximum 150mm, step run (depth) minimum 300mm.
        English: Step rise maximum 150mm, step run minimum 300mm.
        Swedish: Steghöjden max 150 mm, stegbredden minst 300 mm.
        
        Returns NOT_CHECKED if stair dimension data is not in space_dict.
        """
        rule = self.RULE_STAIR_DIMENSIONS
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
        
        rise_mm = space_dict.get("stair_rise_mm")
        run_mm = space_dict.get("stair_run_mm")
        if rise_mm is None or run_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Stair step dimensions (rise/run) not available in current IFC file. Will be checked when stair geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        max_rise, min_run = 150, 300
        if rise_mm <= max_rise and run_mm >= min_run:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Step rise {rise_mm:.0f}mm <= {max_rise}mm, run {run_mm:.0f}mm >= {min_run}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        issues = []
        if rise_mm > max_rise:
            issues.append(f"rise {rise_mm:.0f}mm > max {max_rise}mm")
        if run_mm < min_run:
            issues.append(f"run {run_mm:.0f}mm < min {min_run}mm")
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Stair dimensions non-compliant: {'; '.join(issues)}. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_parking_width_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:131 - Accessible Parking Space Width.
        
        Requirement: Accessible parking space minimum 3600mm wide.
        English: Accessible parking space minimum clear width 3600mm.
        Swedish: Tillgänglig parkeringsplats minst 3600 mm bred.
        
        Returns NOT_CHECKED if parking width is not in space_dict.
        """
        rule = self.RULE_PARKING_WIDTH
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
        
        width_mm = space_dict.get("parking_width_mm")
        if width_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Parking space width not available in current IFC file. Will be checked when parking geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        required = 3600
        if width_mm >= required:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Parking width {width_mm:.0f}mm >= required {required}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Parking width {width_mm:.0f}mm < required {required}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_parking_length_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:132 - Parking Space Length.
        
        Requirement: Parking space length minimum 5000mm.
        English: Parking space length minimum 5000mm.
        Swedish: Parkeringsplatsens längd minst 5000 mm.
        
        Returns NOT_CHECKED if parking length is not in space_dict.
        """
        rule = self.RULE_PARKING_LENGTH
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
        
        length_mm = space_dict.get("parking_length_mm")
        if length_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Parking space length not available in current IFC file. Will be checked when parking geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        required = 5000
        if length_mm >= required:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Parking length {length_mm:.0f}mm >= required {required}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Parking length {length_mm:.0f}mm < required {required}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_stair_handrail_both_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:411 - Stair Handrail Both Sides.
        
        Requirement: Stairs must have handrails on both sides.
        English: Stairs must have handrails on both sides.
        Swedish: Trappor ska ha räcken på båda sidor.
        
        Returns NOT_CHECKED if handrail data is not in space_dict.
        """
        rule = self.RULE_STAIR_HANDRAIL_BOTH
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
        
        both_sides = space_dict.get("stair_handrail_both_sides")
        if both_sides is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Stair handrail configuration not available in current IFC file. Will be checked when railing extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        if both_sides:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Stair has handrails on both sides. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details="Stair must have handrails on both sides.",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_stair_width_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:412 - Stair Width.
        
        Requirement: Stair clear width minimum 1200mm.
        English: Stair clear width minimum 1200mm.
        Swedish: Trappans fria bredd minst 1200 mm.
        
        Returns NOT_CHECKED if stair width is not in space_dict.
        """
        rule = self.RULE_STAIR_WIDTH
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
        
        width_mm = space_dict.get("stair_width_mm")
        if width_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Stair width not available in current IFC file. Will be checked when stair geometry extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        required = 1200
        if width_mm >= required:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Stair width {width_mm:.0f}mm >= required {required}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Stair width {width_mm:.0f}mm < required {required}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_window_sill_height_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:531 - Window Sill Height.
        
        Requirement: Window sill height maximum 600mm from floor.
        English: Window sill height maximum 600mm from floor level.
        Swedish: Fönsterbrädans höjd max 600 mm från golvnivå.
        
        Returns NOT_CHECKED if window sill height is not in space_dict.
        """
        rule = self.RULE_WINDOW_SILL_HEIGHT
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
        
        sill_height_mm = space_dict.get("window_sill_height_mm")
        if sill_height_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Window sill height not available in current IFC file. Will be checked when window extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        max_height = 600
        if sill_height_mm <= max_height:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Window sill height {sill_height_mm:.0f}mm <= max {max_height}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Window sill height {sill_height_mm:.0f}mm > max {max_height}mm. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_window_opening_size_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:532 - Window Opening Size.
        
        Requirement: Window opening minimum 900mm x 1200mm for emergency access.
        English: Window opening minimum 900mm x 1200mm for emergency access.
        Swedish: Fönsteröppning minst 900 mm x 1200 mm för nödutrymning.
        
        Returns NOT_CHECKED if window opening dimensions are not in space_dict.
        """
        rule = self.RULE_WINDOW_OPENING_SIZE
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
        
        width_mm = space_dict.get("window_opening_width_mm")
        height_mm = space_dict.get("window_opening_height_mm")
        if width_mm is None or height_mm is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Window opening dimensions not available in current IFC file. Will be checked when window extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        min_width, min_height = 900, 1200
        if width_mm >= min_width and height_mm >= min_height:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Window opening {width_mm:.0f}mm x {height_mm:.0f}mm >= required {min_width}mm x {min_height}mm. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        issues = []
        if width_mm < min_width:
            issues.append(f"width {width_mm:.0f}mm < {min_width}mm")
        if height_mm < min_height:
            issues.append(f"height {height_mm:.0f}mm < {min_height}mm")
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details=f"Window opening insufficient: {'; '.join(issues)}. {rule.get('description_en', '')}",
            severity=rule["severity"],
            reference=rule["reference"]
        )
    
    def check_tactile_guidance_rule(self, space_dict: Dict[str, Any]) -> RuleResult:
        """
        Check BFS 2024:1 Section 3:611 - Tactile Floor Guidance.
        
        Requirement: Tactile floor guidance for visually impaired in public areas.
        English: Tactile floor guidance required for visually impaired in public areas.
        Swedish: Taktil golvledning krävs för synskadade i offentliga områden.
        
        Returns NOT_CHECKED if tactile guidance data is not in space_dict.
        """
        rule = self.RULE_TACTILE_GUIDANCE
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
        
        has_guidance = space_dict.get("tactile_guidance_present")
        if has_guidance is None:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.NOT_CHECKED,
                details="Tactile floor guidance data not available in current IFC file. Will be checked when floor finish/guidance extraction is implemented.",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        
        if has_guidance:
            return RuleResult(
                rule_id=rule["id"],
                rule_name=rule["name"],
                status=RuleStatus.PASS,
                details=f"Tactile floor guidance present. {rule.get('description_en', '')}",
                severity=rule["severity"],
                reference=rule["reference"]
            )
        return RuleResult(
            rule_id=rule["id"],
            rule_name=rule["name"],
            status=RuleStatus.FAIL,
            details="Tactile floor guidance required for visually impaired in this public area.",
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