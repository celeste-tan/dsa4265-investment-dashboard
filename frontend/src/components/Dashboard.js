import React from 'react';
import './Dashboard.css';

function Dashboard() {
  return (
    <div className="dashboard-layout">
      {/* Left column: Big holistic summary */}
      <div className="left-card">
        <div className="card">
          <h2>At a Glance</h2>
        </div>
      </div>

      {/* Right grid: Four breakdown sections */}
      <div className="right-grid">
        <div className="card">
          <h2>Media Sentiment Analysis</h2>
        </div>
        <div className="card">
          <h2>Stock History Performance</h2>
        </div>
        <div className="card">
          <h2>Financial Statements</h2>
        </div>
        <div className="card">
          <h2>ESG Score</h2>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
