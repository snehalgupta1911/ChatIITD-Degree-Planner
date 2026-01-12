"""
Data loading utilities for degree planner.
All data is loaded from JSON files in the data/ folder.
Includes parsing functions for prerequisite and overlap strings.
"""

import json
import re
from itertools import product
from pathlib import Path

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_prereqs(prereq_string: str) -> list[list[str]]:
    """
    Parse prerequisite string into list of alternative paths.
    
    Input: "[ELL101 and ELL202 and (ELL211 or ELL231)]"
    Output: [['ELL101', 'ELL202', 'ELL211'], ['ELL101', 'ELL202', 'ELL231']]
    
    Logic:
    - 'and' means the course is required in all combinations
    - 'or' within parentheses creates alternative paths
    """
    if not prereq_string or prereq_string.strip() in ["", "[]", "None"]:
        return []
    
    # Remove outer brackets if present
    prereq_string = prereq_string.strip()
    if prereq_string.startswith('[') and prereq_string.endswith(']'):
        prereq_string = prereq_string[1:-1]
    
    # Find all course codes (alphanumeric pattern)
    course_pattern = r'[A-Z]{3}\d{3}'
    
    # Split by 'and' to get main required courses and OR groups
    and_parts = re.split(r'\s+and\s+', prereq_string)
    
    required_courses = []  # Courses that must be in all combinations
    or_groups = []  # Groups of alternatives
    
    for part in and_parts:
        part = part.strip()
        
        # Check if this part contains an OR group (has parentheses)
        if '(' in part and ')' in part:
            # Extract content within parentheses
            match = re.search(r'\((.*?)\)', part)
            if match:
                or_content = match.group(1)
                # Split by 'or' to get alternatives
                alternatives = re.split(r'\s+or\s+', or_content)
                # Extract course codes from each alternative
                or_group = [
                    re.findall(course_pattern, alt)[0] 
                    for alt in alternatives 
                    if re.findall(course_pattern, alt)
                ]
                if or_group:
                    or_groups.append(or_group)
            else:
                # Malformed parentheses, treat as regular courses
                courses = re.findall(course_pattern, part)
                required_courses.extend(courses)
        else:
            # This is a required course (no parentheses)
            courses = re.findall(course_pattern, part)
            required_courses.extend(courses)
    
    # Generate all combinations
    if not or_groups:
        # No OR groups, just return required courses
        return [required_courses] if required_courses else []
    
    # Create cartesian product of OR groups
    combinations = list(product(*or_groups))
    
    # Add required courses to each combination
    result = []
    for combo in combinations:
        combination = required_courses + list(combo)
        result.append(combination)
    
    return result


def parse_overlaps(overlap_string: str) -> list[str]:
    """
    Parse overlap string into a list of course codes.

    Input:  "ELL784, ELL789, COL341/COL774"
    Output: ['ELL784', 'ELL789', 'COL341', 'COL774']
    """
    if not overlap_string or overlap_string.strip() in ["", "None"]:
        return []
    
    # Replace '/' with ',' then split
    cleaned = overlap_string.replace('/', ',')
    overlap_list = [code.strip() for code in cleaned.split(',') if code.strip()]
    
    return overlap_list


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

# Base directory for data files
DATA_DIR = Path(__file__).parent / "data"
PROGRAMME_STRUCTURES_DIR = DATA_DIR / "programme_structures"


def load_courses() -> dict:
    """
    Load all course data from data/courses.json.
    
    Returns:
        Dict with course_code as key and course details as value.
        E.g.: {"ELL101": {"credits": 4, "prereqs": "[MAL111]", ...}}
    """
    courses_file = DATA_DIR / "courses.json"
    
    if not courses_file.exists():
        raise FileNotFoundError(f"Courses file not found: {courses_file}")
    
    with open(courses_file, "r") as f:
        return json.load(f)


def load_department(dept_code: str) -> dict:
    """
    Load department programme structure from data/programme_structures/{code}.json.
    
    Args:
        dept_code: Department code like "EE1", "CS1", etc.
    
    Returns:
        Dict with department structure including:
        - code: Department code
        - name: Full department name
        - credits: Credit requirements by category
        - courses: Lists of course codes by type (PL, DC, DE)
        - recommended: Semester-wise recommended courses
    """
    dept_file = PROGRAMME_STRUCTURES_DIR / f"{dept_code}.json"
    
    if not dept_file.exists():
        available = get_available_departments()
        raise FileNotFoundError(
            f"Department '{dept_code}' not found. Available: {available}"
        )
    
    with open(dept_file, "r") as f:
        return json.load(f)


def get_available_departments() -> list[str]:
    """
    List available department codes from programme_structures folder.
    
    Returns:
        List of available department codes (e.g., ['EE1', 'CS1', 'ME1'])
    """
    if not PROGRAMME_STRUCTURES_DIR.exists():
        return []
    
    return [
        f.stem for f in PROGRAMME_STRUCTURES_DIR.glob("*.json")
        if f.stem != "prompt"  # Exclude the prompt.md file
    ]


def save_json(data: dict, filename: str) -> str:
    """
    Save data to a JSON file in the project root.
    
    Args:
        data: Dictionary to save
        filename: Output filename
    
    Returns:
        Path to the saved file
    """
    output_path = Path(__file__).parent / filename
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)
    
    return str(output_path)
