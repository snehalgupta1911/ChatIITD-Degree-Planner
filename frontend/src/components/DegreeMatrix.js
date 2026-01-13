import React from 'react';

const DegreeMatrix = ({ planData }) => {
    // Safety check for data
    if (!planData || !planData.semesters) {
        return <div className="placeholder-container">No data available</div>;
    }

    // Determine max courses efficiently
    const maxCourses = Math.max(
        ...planData.semesters.map(sem => (sem.courses ? sem.courses.length : 0)),
        0
    );

    // Create array for column headers: Semester + Course Cols + Credits
    const courseColumns = Array.from({ length: maxCourses }, (_, i) => `Course ${i + 1}`);
    const totalColumns = 1 + maxCourses + 1; // Sem + Courses + Total

    // Inline style for grid template
    const gridStyle = {
        gridTemplateColumns: `80px repeat(${maxCourses}, minmax(160px, 1fr)) 100px`
    };

    return (
        <div className="degree-matrix-container">
            <div className="degree-matrix-grid" style={gridStyle}>

                {/* Header Row */}
                <div className="grid-header-cell">Sem</div>
                {courseColumns.map((col, idx) => (
                    <div key={`head-${idx}`} className="grid-header-cell">{col}</div>
                ))}
                <div className="grid-header-cell">Credits</div>

                {/* Data Rows */}
                {planData.semesters.map((semester) => {
                    const courses = semester.courses || [];
                    const totalCredits = courses.reduce((sum, c) => sum + (c.credits || 0), 0);
                    const filledCount = courses.length;

                    return (
                        <React.Fragment key={semester.number}>
                            {/* Semester Indicator */}
                            <div className="semester-row-header">
                                {semester.number}
                            </div>

                            {/* Course Cards */}
                            {courses.map((course, idx) => {
                                const title = course.title || "Unknown Course";
                                const code = course.code || "N/A";
                                const credits = course.credits || 0;
                                const l = course.l || 0;
                                const t = course.t || 0;
                                const p = course.p || 0;

                                return (
                                    <div key={`crs-${semester.number}-${idx}`} className="course-card">
                                        <div className="course-code">{code}</div>
                                        <div className="course-title" title={title}>{title}</div>
                                        <div className="course-credits">
                                            {credits} ({l}-{t}-{p})
                                        </div>
                                    </div>
                                );
                            })}

                            {/* Empty Placeholders */}
                            {Array.from({ length: maxCourses - filledCount }).map((_, idx) => (
                                <div key={`empty-${semester.number}-${idx}`} className="course-card empty-card"></div>
                            ))}

                            {/* Total Credits */}
                            <div className="total-credits-cell">
                                <span className="total-value">{totalCredits}</span>
                            </div>
                        </React.Fragment>
                    );
                })}
            </div>
        </div>
    );
};

export default DegreeMatrix;
