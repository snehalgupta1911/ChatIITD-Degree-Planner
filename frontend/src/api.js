const API_BASE_URL = 'http://localhost:8000';

export const fetchDegreePlan = async (deptCode) => {
    try {
        const response = await fetch(`${API_BASE_URL}/selected-courses/${deptCode}`);
        if (!response.ok) {
            throw new Error(`Error fetching data: ${response.statusText}`);
        }
        const data = await response.json();

        // Transform object { "1": [...], "2": [...] } to array [{ number: 1, courses: [...] }]
        const semesters = Object.keys(data).map(key => ({
            number: parseInt(key),
            courses: data[key]
        })).sort((a, b) => a.number - b.number);

        return { semesters };
    } catch (error) {
        console.error("Failed to fetch degree plan:", error);
        throw error;
    }
};
