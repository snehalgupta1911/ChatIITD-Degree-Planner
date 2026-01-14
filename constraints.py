"""
Constraint model builder for degree planning using OR-Tools CP-SAT solver.
"""

from ortools.sat.python import cp_model
from data_loader import parse_prereqs
from slotting.slotparsing import load_slot_dataframe

slot_df=load_slot_dataframe()
print(slot_df.head())



class DegreePlannerModel:
    """Builds and manages the constraint satisfaction model for degree planning."""
    
    def __init__(self, config: dict):
        """
        Initialize the planner model.
        
        Args:
            config: Configuration dict with keys:
                - TOTAL_TARGET_CREDITS: Total credits required for degree
                - CREDIT_SCALE: Scale factor for credits (to avoid floats)
                - MAX_HUL_PER_SEM: Maximum HUL courses per semester
        """
        self.config = config
        self.model = cp_model.CpModel()
        self.course_vars = {}  # (sem, code) -> BoolVar
    
    def create_course_variables(self, courses_left: dict):
        """
        Create boolean variables for all remaining courses.
        
        Args:
            courses_left: Dict mapping semester -> list of course dicts
        """
        for sem, courses in courses_left.items():
            for course in courses:
                code = course["code"]
                self.course_vars[(sem, code)] = self.model.NewBoolVar(f"{code}_sem{sem}")
    
    def add_semester_credit_constraints(self, courses_left: dict, min_credits: float, max_credits: float):
        """
        Add min/max credit constraints for each semester.
        
        Args:
            courses_left: Remaining courses by semester
            min_credits: Minimum credits per semester
            max_credits: Maximum credits per semester
        """
        scale = self.config["CREDIT_SCALE"]
        
        for sem, courses in courses_left.items():
            total_credits = 0
            for course in courses:
                code = course["code"]
                total_credits += self.course_vars[(sem, code)] * int(course["credits"] * scale)
            
            self.model.Add(total_credits >= int(min_credits * scale))
            self.model.Add(total_credits <= int(max_credits * scale))
    
    def add_total_credit_constraint(self, courses_left: dict, credits_done: float):
        """
        Add constraint for total degree credits.
        
        Args:
            courses_left: Remaining courses by semester
            credits_done: Credits already completed
        """
        scale = self.config["CREDIT_SCALE"]
        target = self.config["TOTAL_TARGET_CREDITS"]
        remaining_target = int((target - credits_done) * scale)
        
        total_remaining = 0
        for (sem, code), var in self.course_vars.items():
            for course in courses_left[sem]:
                if course["code"] == code:
                    total_remaining += var * int(course["credits"] * scale)
                    break
        
        self.model.Add(total_remaining == remaining_target)
    
    def add_hul_limit_constraint(self, courses_left: dict):
        """
        Add constraint limiting HUL courses per semester.
        
        Args:
            courses_left: Remaining courses by semester
        """
        max_hul = self.config["MAX_HUL_PER_SEM"]
        
        for sem, courses in courses_left.items():
            hul_vars = []
            for course in courses:
                code = course["code"]
                if course.get("type", "").startswith("HUL"):
                    hul_vars.append(self.course_vars[(sem, code)])
            
            if hul_vars:
                self.model.Add(sum(hul_vars) <= max_hul)
    
    def add_prerequisite_constraints(self, courses_left: dict, completed_courses: set):
        """
        Add prerequisite ordering constraints.
        
        Args:
            courses_left: Remaining courses by semester
            completed_courses: Set of already completed course codes
        """
        for (sem, code), var in self.course_vars.items():
            course_data = None
            for c in courses_left[sem]:
                if c["code"] == code:
                    course_data = c
                    break
            
            if course_data is None:
                continue
            
            prereqs_parsed = course_data.get("prereqs_parsed", [])
            if not prereqs_parsed:
                continue
            
            path_constraints = []
            
            for prereq_path in prereqs_parsed:
                prereq_vars_in_path = []
                all_prereqs_satisfiable = True
                
                for prereq_code in prereq_path:
                    if prereq_code in completed_courses:
                        continue
                    
                    prereq_found = False
                    for sem_p in range(1, sem):
                        if (sem_p, prereq_code) in self.course_vars:
                            prereq_vars_in_path.append(self.course_vars[(sem_p, prereq_code)])
                            prereq_found = True
                            break
                    
                    if not prereq_found:
                        all_prereqs_satisfiable = False
                        break
                
                if all_prereqs_satisfiable:
                    if len(prereq_vars_in_path) == 0:
                        path_var = self.model.NewBoolVar(f'path_{code}_sem{sem}_completed')
                        self.model.Add(path_var == 1)
                        path_constraints.append(path_var)
                    elif len(prereq_vars_in_path) > 0:
                        path_var = self.model.NewBoolVar(f'path_{code}_sem{sem}_{prereq_path}')
                        self.model.AddMinEquality(path_var, prereq_vars_in_path)
                        path_constraints.append(path_var)
            
            if path_constraints:
                self.model.Add(sum(path_constraints) >= var)
    
    def add_core_course_constraint(self, courses_left: dict):
        """
        Add constraint that each core course is taken exactly once.
        
        Args:
            courses_left: Remaining courses by semester
        """
        seen_cores = set()
        
        for sem, courses in courses_left.items():
            for course in courses:
                if course.get("type") == "Core":
                    code = course["code"]
                    if code in seen_cores:
                        continue
                    seen_cores.add(code)
                    
                    core_vars = [
                        var for (s, c), var in self.course_vars.items() if c == code
                    ]
                    
                    if core_vars:
                        self.model.Add(sum(core_vars) == 1)
    
    def add_overlap_constraints(self, courses_left: dict, overlap_list: list[str]):
        """
        Add constraints preventing overlapping courses in same semester.
        
        Args:
            courses_left: Remaining courses by semester
            overlap_list: List of course codes that overlap
        """
        for sem in courses_left.keys():
            for i in range(len(overlap_list)):
                for j in range(i + 1, len(overlap_list)):
                    course1 = overlap_list[i]
                    course2 = overlap_list[j]
                    if (sem, course1) in self.course_vars and (sem, course2) in self.course_vars:
                        self.model.Add(
                            self.course_vars[(sem, course1)] + self.course_vars[(sem, course2)] <= 1
                        )
    
    def get_model(self) -> cp_model.CpModel:
        """Return the underlying OR-Tools model."""
        return self.model
    
    def get_course_vars(self) -> dict:
        """Return the course variable mapping."""
        return self.course_vars
    
    def add_slotting_constraints(self, courses_left: dict):
        """
        Add slotting constraints:
        - No two courses with the same slot can be taken in the same semester.
        - EXCEPTION: Lab courses (XXP) and Lecture courses (XXL etc) are treated separately.
          - Sum(Labs in Slot X) <= 1
          - Sum(Lectures in Slot X) <= 1
        Also prints debug information.
        
        Args:
            courses_left: Remaining courses by semester
        """
        print("\n[DEBUG] Adding slotting constraints")

        for sem, courses in courses_left.items():
            print(f"\n[DEBUG] Semester {sem}")

            # Filter slot_df for this semester
            # Map planner semester to slot semester
            slot_sem = 1 if sem % 2 == 1 else 2

            print(f"[DEBUG] Planner sem {sem} -> Slot sem {slot_sem}")

            sem_slot_df = slot_df[
                slot_df["Semester"].astype(int) == slot_sem
            ] #if odd sem using sem1 data- winter sem and if even sem using sem 2 data - summer sem 

            # Build mapping: slot -> list of course codes
            slot_to_courses = (
                sem_slot_df.groupby("Slot Name")["Course Code"]
                .apply(list)
                .to_dict()
            )

            for slot, codes_in_slot in slot_to_courses.items():
                # Filter for active courses in this semester
                active_codes = [
                    code for code in codes_in_slot
                    if (sem, code) in self.course_vars
                ]
                
                if not active_codes:
                    continue

                # Split into Labs (XXP) and Lectures (Others)
                lab_codes = [c for c in active_codes if len(c) > 2 and c[2] == 'P'] # Assuming format ELP123
                lecture_codes = [c for c in active_codes if len(c) <= 2 or c[2] != 'P']
                
                # Apply constraints for Labs
                if len(lab_codes) > 1:
                    print(f"  Slot {slot} (Labs): {lab_codes}")
                    print(f"    -> Constraint: sum(vars) <= 1")
                    lab_vars = [self.course_vars[(sem, code)] for code in lab_codes]
                    self.model.Add(sum(lab_vars) <= 1)
                
                # Apply constraints for Lectures
                if len(lecture_codes) > 1:
                    print(f"  Slot {slot} (Lectures): {lecture_codes}")
                    print(f"    -> Constraint: sum(vars) <= 1")
                    lecture_vars = [self.course_vars[(sem, code)] for code in lecture_codes]
                    self.model.Add(sum(lecture_vars) <= 1)

