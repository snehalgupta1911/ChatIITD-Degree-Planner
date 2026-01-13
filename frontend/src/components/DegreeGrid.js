import React from 'react';
import SemesterColumn from './SemesterColumn';

const DegreeGrid = ({ planData }) => {
    return (
        <div className="degree-grid-container">
            <h2>My Degree Plan</h2>
            <div className="degree-grid">
                {planData.semesters.map((semester) => (
                    <SemesterColumn
                        key={semester.number}
                        semesterNumber={semester.number}
                        courses={semester.courses}
                    />
                ))}
            </div>
        </div>
    );
};

export default DegreeGrid;
