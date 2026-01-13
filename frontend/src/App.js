import React, { useState } from 'react';
import './App.css';
import DegreeMatrix from './components/DegreeMatrix';
import { fetchDegreePlan } from './api';

function App() {
  const [degreePlan, setDegreePlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deptCode, setDeptCode] = useState('EE1'); // Default to EE1

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDegreePlan(deptCode);
      setDegreePlan(data);
    } catch (err) {
      setError("Failed to fetch data. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-title">
          <span>🎓</span> IITD Degree Planner
        </div>
        <div className="controls">
          <select
            value={deptCode}
            onChange={(e) => setDeptCode(e.target.value)}
            className="programme-select"
            disabled={loading}
          >
            <option value="EE1">Electrical Engineering (EE1)</option>
            <option value="CS1" disabled>Computer Science (CS1) - Coming Soon</option>
            <option value="MT1" disabled>Maths & Computing (MT1) - Coming Soon</option>
          </select>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="generate-btn"
          >
            {loading ? 'Generating...' : 'Generate Plan'}
          </button>
        </div>
      </header>
      <main className="main-content">
        {error && <div className="error-message">{error}</div>}

        {!degreePlan && !loading && !error && (
          <div className="placeholder-container">
            <div className="placeholder-icon">📊</div>
            <div className="placeholder-text">
              Select a programme and click Generate to see the plan.
            </div>
          </div>
        )}

        {degreePlan && <DegreeMatrix planData={degreePlan} />}
      </main>
    </div>
  );
}

export default App;
