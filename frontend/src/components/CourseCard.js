import React from 'react';
import '../App.css'; // We'll add styles to App.css or a module

const CourseCard = ({ course }) => {
    return (
        <div className={`course-card ${course.type ? course.type.toLowerCase() : 'elective'}`}>
            <div className="course-header">
                <span className="course-code">{course.code}</span>
                <span className="course-credits">{course.credits} Credits</span>
            </div>
            <div className="course-title">{course.title}</div>
        </div>
    );
};

export default CourseCard;
