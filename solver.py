"""
Solver and output utilities for degree planning.
"""

from ortools.sat.python import cp_model
from constraints import DegreePlannerModel


def solve_plan(planner_model: DegreePlannerModel) -> tuple[cp_model.CpSolver, int]:
    """
    Solve the degree planning model.
    
    Args:
        planner_model: The DegreePlannerModel with all constraints added
    
    Returns:
        Tuple of (solver, status)
    """
    solver = cp_model.CpSolver()
    status = solver.Solve(planner_model.get_model())
    return solver, status


def print_solver_status(status: int, credits_done: float, remaining_credits: float, 
                        min_credits: float, max_credits: float, scale: float):
    """Print the solver status with debugging info."""
    if status == cp_model.OPTIMAL:
        print("✅ Optimal solution found!")
    elif status == cp_model.FEASIBLE:
        print("⚠️ Feasible solution found (not optimal)")
    elif status == cp_model.INFEASIBLE:
        print("❌ NO SOLUTION EXISTS - Constraints are impossible to satisfy!")
        print("\n🔍 Debugging info:")
        print(f"  - Completed credits: {credits_done}")
        print(f"  - Remaining target: {remaining_credits / scale}")
        print(f"  - User min/max per sem: {min_credits} - {max_credits}")
    else:
        print(f"❓ Unknown status: {status}")
    
    return status in [cp_model.OPTIMAL, cp_model.FEASIBLE]


def extract_semester_plan(solver: cp_model.CpSolver, 
                          planner_model: DegreePlannerModel,
                          courses_left: dict) -> dict:
    """
    Extract the selected courses from the solved model.
    
    Args:
        solver: The solved CP solver
        planner_model: The planner model
        courses_left: Remaining courses by semester
    
    Returns:
        Dict mapping semester -> list of selected course dicts
    """
    semester_plan = {}
    course_vars = planner_model.get_course_vars()
    
    for (sem, code), var in course_vars.items():
        if solver.Value(var):
            if sem not in semester_plan:
                semester_plan[sem] = []
            
            for course in courses_left[sem]:
                if course["code"] == code:
                    semester_plan[sem].append(course)
                    break
    
    return semester_plan


def print_semester_plan(semester_plan: dict):
    """Print the semester plan in a formatted way."""
    for sem in sorted(semester_plan.keys()):
        print(f"\n📘 Semester {sem}")
        total_credits = 0
        
        for course in semester_plan[sem]:
            code = course.get("code", "")
            name = course.get("name", "Unknown Course")
            credits = course.get("credits", 0)
            prereqs = course.get("prereqs", [])
            ctype = course.get("type", "Unknown")
            
            total_credits += credits
            print(f"  - {code}: {name} ({credits} credits, Type: {ctype}), Prerequisites: {prereqs}")
        
        print(f"👉 Total Credits: {total_credits}")


def print_feasibility_check(courses_left: dict, credits_done: float, 
                            remaining_target: float, min_credits: float, 
                            max_credits: float, scale: float):
    """Print pre-solve feasibility analysis."""
    print("\n🔍 PRE-SOLVE DEBUG:")
    print(f"Semesters to plan: {sorted(courses_left.keys())}")
    print(f"Total credits already done: {credits_done}")
    print(f"Remaining credits needed: {remaining_target / scale}")
    print(f"Min/Max credits per semester: {min_credits} - {max_credits}")
    
    num_future_sems = len(courses_left.keys())
    min_possible = num_future_sems * min_credits
    max_possible = num_future_sems * max_credits
    target_needed = remaining_target / scale
    
    print(f"\n📊 Feasibility check:")
    print(f"  Future semesters: {num_future_sems}")
    print(f"  Possible credit range: {min_possible} - {max_possible}")
    print(f"  Target needed: {target_needed}")
    
    if target_needed < min_possible:
        print("  ❌ PROBLEM: Need too few credits (will exceed minimum)")
    elif target_needed > max_possible:
        print("  ❌ PROBLEM: Need too many credits (can't fit in max limits)")
    else:
        print("  ✅ Feasible range")
    
    # Count available courses per semester
    for sem in sorted(courses_left.keys()):
        total_available = sum(c["credits"] for c in courses_left[sem])
        core_credits = sum(c["credits"] for c in courses_left[sem] if c.get("type") == "Core")
        print(f"\n  Sem {sem}: {len(courses_left[sem])} courses, {total_available} total credits")
        print(f"    Core (mandatory): {core_credits} credits")
