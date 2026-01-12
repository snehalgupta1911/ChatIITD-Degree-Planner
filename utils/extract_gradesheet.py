# IMPORTANT: Currently this doesn't work for F grade or withdrawn courses.
import PyPDF2
import re

def extract_course_codes(pdf_path):
    course_codes = set()
    # Regex for standard course codes: 3 letters uppercase followed by 3 digits (e.g., COL106)
    # Adjust regex if the format is different (e.g. might have spaces or different length)
    course_code_pattern = re.compile(r'[A-Z]{3}\d{3}')

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    # Find all matches in the page text
                    matches = course_code_pattern.findall(text)
                    for match in matches:
                        course_codes.add(match)
        
        return sorted(list(course_codes))

    except Exception as e:
        print(f"Error extracting course codes: {e}")
        return []

if __name__ == "__main__":
    pdf_file = "gradesheet.pdf"
    codes = extract_course_codes(pdf_file)
    
    if codes:
        print("Extracted Course Codes:")
        for code in codes:
            print(code)
    else:
        print("No course codes found or error occurred.")
