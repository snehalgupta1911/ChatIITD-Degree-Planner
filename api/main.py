from fastapi import FastAPI, HTTPException
import sys
from pathlib import Path

# Add the parent directory to sys.path to allow imports from root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from planner import build_selected_courses
from data_loader import load_courses, load_department

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Degree Planner API"}

@app.get("/selected-courses/{dept_code}")
def get_selected_courses(dept_code: str):
    try:
        all_courses = load_courses()
        department = load_department(dept_code)
        selected_courses = build_selected_courses(department, all_courses)
        return selected_courses
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
