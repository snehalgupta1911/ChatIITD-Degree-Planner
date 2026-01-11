"""
Degree Planner - Main orchestrator for course planning using constraint programming.

This module coordinates the loading of course data, building constraint models,
and solving for optimal semester plans.
"""

from data_loader import (
    load_courses, load_department, save_json,
    parse_prereqs, parse_overlaps
)
from constraints import DegreePlannerModel
from solver import (
    solve_plan, print_solver_status, extract_semester_plan,
    print_semester_plan, print_feasibility_check
)
from user import UserData


# Configuration
CONFIG = {
    "TOTAL_TARGET_CREDITS": 150,   # EE degree requirement
    "CREDIT_SCALE": 10,            # Scale to avoid floats in OR-Tools
    "MAX_HUL_PER_SEM": 2
}


def build_selected_courses(department: dict, all_courses: dict) -> dict:
    """
    Build semester-wise course selection based on department recommendations.
    
    Args:
        department: Department structure with recommended courses
        all_courses: All available courses
    
    Returns:
        Dict mapping semester -> list of course dicts
    """
    recommended_courses = department["recommended"]
    selected_courses = {}
    
    for sem_idx, course_list in enumerate(recommended_courses, start=1):
        selected_courses[sem_idx] = []
        
        for course_code in course_list:
            # Handle DE (Department Elective) placeholders
            if course_code.startswith("DE"):
                for de_code in department["courses"].get("DE", []):
                    if de_code in all_courses:
                        course = all_courses[de_code].copy()
                        prereq_string = course.get("prereqs", "")
                        course["prereqs_parsed"] = parse_prereqs(prereq_string)
                        course["type"] = "DE"
                        selected_courses[sem_idx].append(course)
            
            # Handle HUL2XX placeholder
            elif course_code == "HUL2XX":
                for code, course_data in all_courses.items():
                    if code.startswith("HUL2"):
                        course = course_data.copy()
                        prereq_string = course.get("prereqs", "")
                        course["prereqs_parsed"] = parse_prereqs(prereq_string)
                        course["type"] = "HUL2XX"
                        selected_courses[sem_idx].append(course)
            
            # Handle HUL3XX placeholder
            elif course_code == "HUL3XX":
                for code, course_data in all_courses.items():
                    if code.startswith("HUL3"):
                        course = course_data.copy()
                        prereq_string = course.get("prereqs", "")
                        course["prereqs_parsed"] = parse_prereqs(prereq_string)
                        course["type"] = "HUL3XX"
                        selected_courses[sem_idx].append(course)
            
            # Handle OC (Open Course) placeholders - skip for now
            elif course_code.startswith("OC"):
                continue
            
            # Regular course
            elif course_code in all_courses:
                course = all_courses[course_code].copy()
                prereq_string = course.get("prereqs", "")
                course["prereqs_parsed"] = parse_prereqs(prereq_string)
                course["type"] = "Core"
                selected_courses[sem_idx].append(course)
            
            else:
                print(f"⚠ Warning: {course_code} not found in courses.json")
    
    return selected_courses


def build_courses_left(selected_courses: dict, user: UserData) -> dict:
    """
    Build dict of remaining courses based on user's completed courses.
    
    Args:
        selected_courses: All selected courses by semester
        user: User data with completion info
    
    Returns:
        Dict mapping semester -> list of remaining course dicts
    """
    courses_left = {}
    
    # Build set of all completed courses
    all_completed = set(user.completed_corecourses)
    all_completed.update(user.completed_hul)
    all_completed.update(user.completed_DE)
    
    # Build courses_left for all semesters
    for sem, courses in selected_courses.items():
        target_sem = sem if sem >= user.current_semester else user.current_semester
        
        for course in courses:
            code = course["code"]
            
            if code in all_completed:
                continue
            
            courses_left.setdefault(target_sem, []).append(course)
    
    # Find incomplete core courses from past semesters
    incomplete_cores = []
    for sem, courses in selected_courses.items():
        if sem < user.current_semester:
            for course in courses:
                code = course["code"]
                ctype = course.get("type", "")
                
                if ctype == "Core" and code not in all_completed:
                    incomplete_cores.append(course)
                    print(f"Found incomplete/failed course: {code} from semester {sem}")
    
    # Add failed courses to all future semesters
    for sem in range(user.current_semester, 9):
        if sem not in courses_left:
            courses_left[sem] = []
        
        for failed_course in incomplete_cores:
            code = failed_course["code"]
            if not any(c["code"] == code for c in courses_left[sem]):
                courses_left[sem].append(failed_course)
    
    return courses_left


def calculate_credits_done(user: UserData) -> float:
    """Calculate total credits already completed."""
    credits_done = 0
    seen_courses = set()
    
    for sem, courses in user.EE_courses.items():
        for course in courses:
            code = course["code"]
            if code in seen_courses:
                continue
            
            if (code in user.completed_corecourses or 
                code in user.completed_hul or 
                code in user.completed_DE):
                credits_done += course["credits"]
                seen_courses.add(code)
    
    return credits_done


def main():
    """Main entry point for the degree planner."""
    # Load data from JSON files
    print("📚 Loading course data...")
    all_courses = load_courses()
    department = load_department("EE1")
    dept_code = department["code"]
    
    print(f"✅ Loaded {len(all_courses)} courses")
    print(f"✅ Loaded department: {department['name']}")
    
    # Build selected courses
    selected_courses = build_selected_courses(department, all_courses)
    
    # Save department courses
    output_file = f"{dept_code}_courses_data.json"
    save_json(selected_courses, output_file)
    print(f"✅ Department courses saved to '{output_file}'")
    
    # Create user (this would come from user input in a real app)
    user = UserData(
        name="Snehal",
        current_semester=4,
        EE_courses=selected_courses,
        completed_corecourses=[
            'ELL101', 'PYL101', 'MCP100', 'MTL100', 'COL100', 'PYP100', 'MCP101',
            'APL100', 'CML101', 'MTL101', 'CMP100', 'ELL205', 'ELL203', 'ELL201',
            'COL106', 'ELL202', 'ELP101'
        ]
    )
    user.print_summary(debug=True)
    
    # Build remaining courses
    courses_left = build_courses_left(selected_courses, user)
    
    # Save courses_left
    save_json(courses_left, "courses_left.json")
    print(f"\n✅ Courses left saved to 'courses_left.json'")
    
    # Print summary
    print(f"\n📊 Summary:")
    for sem in sorted(courses_left.keys()):
        hul_count = sum(1 for c in courses_left[sem] if c.get("type", "").startswith("HUL"))
        de_count = sum(1 for c in courses_left[sem] if c.get("type") == "DE")
        core_count = sum(1 for c in courses_left[sem] if c.get("type") == "Core")
        print(f"  Semester {sem}: {len(courses_left[sem])} courses ({core_count} Core, {hul_count} HUL, {de_count} DE)")
    
    # Build and solve constraint model
    print("\n🔧 Building constraint model...")
    planner = DegreePlannerModel(CONFIG)
    planner.create_course_variables(courses_left)
    
    # Add constraints
    planner.add_semester_credit_constraints(courses_left, user.min_credits, user.max_credits)
    
    credits_done = calculate_credits_done(user)
    print(f"Credits done: {credits_done}")
    
    planner.add_total_credit_constraint(courses_left, credits_done)
    planner.add_hul_limit_constraint(courses_left)
    
    # Build completed courses set
    all_completed = set(user.completed_corecourses)
    all_completed.update(user.completed_hul)
    all_completed.update(user.completed_DE)
    
    planner.add_prerequisite_constraints(courses_left, all_completed)
    planner.add_core_course_constraint(courses_left)
    
    # Add overlap constraints
    overlap_string = department.get("overlaps", "")
    overlap_list = parse_overlaps(overlap_string)
    planner.add_overlap_constraints(courses_left, overlap_list)
    print("Overlap constraints added")
    
    # Print pre-solve debug info
    remaining_target = (CONFIG["TOTAL_TARGET_CREDITS"] - credits_done) * CONFIG["CREDIT_SCALE"]
    print_feasibility_check(
        courses_left, credits_done, remaining_target,
        user.min_credits, user.max_credits, CONFIG["CREDIT_SCALE"]
    )
    
    # Solve
    print("\n🧮 Solving...")
    solver, status = solve_plan(planner)
    
    # Print results
    success = print_solver_status(
        status, credits_done, remaining_target,
        user.min_credits, user.max_credits, CONFIG["CREDIT_SCALE"]
    )
    
    if success:
        semester_plan = extract_semester_plan(solver, planner, courses_left)
        print_semester_plan(semester_plan)


if __name__ == "__main__":
    main()
