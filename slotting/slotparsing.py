import pandas as pd
import re #to extract year and sem from courses offered csvs
from pathlib import Path

def load_slot_dataframe():
    BASE_DIR = Path(__file__).parent
    # Allowed slots
    allowed_slots = set("ABHJCDEFMKL") #just valid slot letters

    csv_files = [
    BASE_DIR / "Courses_Offered_2025_Sem1.csv",
    BASE_DIR / "Courses_Offered_2025_Sem2.csv",
]
    all_dfs = []

    for csv_file in csv_files:
        # -------- Extract year & semester from filename --------
        match = re.search(r"(\d{4})_Sem(\d)", csv_file.name)
        year = match.group(1) if match else ""
        semester = match.group(2) if match else ""


        # Read CSV, skip first line (department header)
        df = pd.read_csv(csv_file, skiprows=1)
        
        # Strip column names and remove empty ones
        df.columns = [col.strip() for col in df.columns]
        df = df.loc[:, df.columns != '']
        
        # # Extract department from first line
        # with open(csv_file, encoding="utf-8") as f:
        #     first_line = f.readline().strip()
        # dept = first_line.split(":")[-1].strip()
        
        # # Add department column
        # df.insert(0, "Department", dept)
        
        # Split course name and code
        def split_course_name(course_str):
            if pd.isna(course_str):
                return pd.Series(["", ""])
            parts = course_str.rsplit("-", 1)
            if len(parts) == 2:
                return pd.Series([parts[0].strip(), parts[1].strip()])
            return pd.Series([course_str.strip(), ""])
        
        df[["Course Name", "Course Code"]] = df["Course Name"].apply(split_course_name)
        
        # Keep only relevant columns
        df = df[[ "Course Code", "Course Name", "Slot Name"]]
        
        # Remove rows with empty or null Course Code
        df = df[df["Course Code"].notna() & (df["Course Code"] != "")]
        df["Course Code"] = df["Course Code"].str.strip()
        
        # ✅ Keep only courses with allowed slots
        df = df[df["Slot Name"].isin(allowed_slots)]
        df["Year"] = year
        df["Semester"] = semester

        
        all_dfs.append(df)

    # Combine all files into a single DataFrame
    combined_df = pd.concat(all_dfs, ignore_index=True)
    slot_df = combined_df
    return slot_df

