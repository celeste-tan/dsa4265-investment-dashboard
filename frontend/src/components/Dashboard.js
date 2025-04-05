// import React from 'react';
// import './Dashboard.css';

// function Dashboard() {
//   return (
//     <div className="dashboard-layout">
//       {/* Left column: Big holistic summary */}
//       <div className="left-card">
//         <div className="card">
//           <h2>At a Glance</h2>
//         </div>
//       </div>

//       {/* Right grid: Four breakdown sections */}
//       <div className="right-grid">
//         <div className="card">
//           <h2>Media Sentiment Analysis</h2>
//         </div>
//         <div className="card">
//           <h2>Stock History Performance</h2>
//         </div>
//         <div className="card">
//           <h2>Financial Statements</h2>
//         </div>
//         <div className="card">
//           <h2>ESG Score</h2>
//         </div>
//       </div>
//     </div>
//   );
// }

// export default Dashboard;

// import React, { useState, useEffect } from 'react';
// import './Dashboard.css';

// function Dashboard({ ticker }) {
//   const [esgReport, setEsgReport] = useState('');
//   const [loading, setLoading] = useState(false);

//   useEffect(() => {
//     if (!ticker) return;

//     const fetchESG = async () => {
//       setLoading(true);
//       try {
//         const response = await fetch('http://localhost:5000/api/esg', {
//           method: 'POST',
//           headers: { 'Content-Type': 'application/json' },
//           body: JSON.stringify({ ticker }),
//         });
//         const data = await response.json();
//         setEsgReport(data.report || "No ESG report available.");
//       } catch (error) {
//         setEsgReport("Error fetching ESG report.");
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchESG();
//   }, [ticker]);

//   return (
//     <div className="dashboard-layout">
//       {/* Left column */}
//       <div className="left-card">
//         <div className="card">
//           <h2>At a Glance</h2>
//         </div>
//       </div>

//       {/* Right grid */}
//       <div className="right-grid">
//         <div className="card">
//           <h2>Media Sentiment Analysis</h2>
//         </div>
//         <div className="card">
//           <h2>Stock History Performance</h2>
//         </div>
//         <div className="card">
//           <h2>Financial Statements</h2>
//         </div>
//         <div className="card">
//           <h2>ESG Score</h2>
//           {loading ? (
//             <p>Loading...</p>
//           ) : (
//             <pre style={{ whiteSpace: 'pre-wrap' }}>{esgReport}</pre>
//           )}
//         </div>
//       </div>
//     </div>
//   );
// }

// export default Dashboard;

import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import Modal from 'react-modal';  // Importing Modal

Modal.setAppElement('#root');

function Dashboard({ ticker }) {
  const [esgScores, setEsgScores] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [esgReport, setEsgReport] = useState(null);

  useEffect(() => {
    if (!ticker) return;

    const fetchESG = async () => {
      setLoading(true);
      try {
        const response = await fetch('http://localhost:5000/api/esg-scores', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker }),
        });
        const data = await response.json();
        setEsgScores(data.esg_scores || "No ESG scores available.");
      } catch (error) {
        setEsgScores("Error fetching ESG scores.");
      } finally {
        setLoading(false);
      }
    };

    fetchESG();
  }, [ticker]);

  const fetchEsgReport = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/esg-gen-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      });
      const data = await response.json();
      setEsgReport(data.report);
    } catch (error) {
      console.error('Error fetching ESG report:', error);
    }
  };

  const handleModalOpen = () => {
    fetchEsgReport();
    setShowModal(true);
  };

  const handleModalClose = () => {
    setShowModal(false);
    setEsgReport(null); // Clear the report content when closing
  };

  return (
    <div className="dashboard-layout">
      {/* Left column */}
      <div className="left-card">
        <div className="card">
          <h2>At a Glance - {ticker}</h2> {/* Dynamically displaying ticker here */}
        </div>
      </div>

      {/* Right grid */}
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
          <h2>ESG Score
            <button
              className="info-icon"
              onClick={handleModalOpen}
              aria-label="Get additional ESG report info"
            >
              ℹ️
            </button>
          </h2>
          {loading ? (
            <p>Loading...</p>
          ) : (
            <div>
              {esgScores ? (
                <ul>
                  <li><strong>Total ESG Risk Score:</strong> {esgScores["Total ESG Risk Score"]}</li>
                  <li><strong>Environmental Risk Score:</strong> {esgScores["Environmental Risk Score"]}</li>
                  <li><strong>Social Risk Score:</strong> {esgScores["Social Risk Score"]}</li>
                  <li><strong>Governance Risk Score:</strong> {esgScores["Governance Risk Score"]}</li>
                  <li><strong>Controversy Level:</strong> {esgScores["Controversy Value"]}</li>
                  <li><strong>Controversy Level:</strong> {esgScores["Controversy Description"]}</li>
                </ul>
              ) : (
                <p>No ESG scores available.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modal for detailed ESG Report */}
      <Modal isOpen={showModal} onRequestClose={handleModalClose} className="modal-content" overlayClassName="modal-overlay">
        <h2>ESG Report for {ticker}</h2>
        
        {/* Only show the report or a loading message */}
        <div className="esg-report">
          {esgReport ? (
            <pre>{esgReport}</pre>
          ) : (
            <p>Loading detailed ESG report...</p>
          )}
        </div>

        {/* Close button will always appear at the bottom after content */}
        <button onClick={handleModalClose} className="close-btn">Close</button>
      </Modal>
    </div>
  );
}

export default Dashboard;