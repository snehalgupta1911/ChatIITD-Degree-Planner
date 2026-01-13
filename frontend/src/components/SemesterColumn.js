import React from 'react';
import CourseCard from './CourseCard';

const SemesterColumn = ({ semesterNumber, courses }) => {
    const totalCredits = courses.reduce((sum, course) => sum + course.credits, 0);

    return (
        <div className="semester-column">
            <div className="semester-header">
                <h3>Semester {semesterNumber}</h3>
                <span className="semester-credits">Total Credits: {totalCredits}</span>
            </div>
            <div className="semester-courses">
                {courses.map((course) => (
                    <CourseCard key={course.id} course={course} />
                ))}
            </div>
        </div>
    );
};

export default SemesterColumn;
