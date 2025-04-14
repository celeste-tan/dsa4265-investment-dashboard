import React from 'react';
import ReactMarkdown from 'react-markdown';
import Modal from 'react-modal';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * ESGScore Component
 *
 * Displays ESG scores in a pie chart and the ESG report in a modal.
 *
 * Props:
 * - ticker: Stock ticker symbol.
 * - esgScores: Object containing ESG scores.
 * - esgScoresLoaded: Boolean flag indicating if the ESG scores have loaded.
 * - esgReport: ESG report content in markdown format.
 * - loadingScores: Boolean flag for the loading state of ESG scores.
 * - loadingReport: Boolean flag for the loading state of the ESG report.
 * - showESGModal: Boolean flag for controlling the modal visibility.
 * - setShowESGModal: Function to toggle the modal visibility.
 */
const ESGScore = ({
  ticker,
  esgScores,
  esgScoresLoaded,
  esgReport,
  loadingScores,
  loadingReport,
  showESGModal,
  setShowESGModal,
}) => {
  // Define colors for the pie chart sections
  const COLORS = ['#4460ef', '#f44879', '#32c1a4'];

  // Prepare pie chart data using the ESG scores object
  const pieData = esgScores ? [
    { name: 'Environmental', value: esgScores['Environmental Risk Score'] },
    { name: 'Social', value: esgScores['Social Risk Score'] },
    { name: 'Governance', value: esgScores['Governance Risk Score'] },
  ] : [];

  return (
    <div className="card">
      <h2>
        ESG Score
        {/* Info button to open the ESG report modal */}
        <button
          className="info-icon"
          onClick={() => setShowESGModal(true)}
          disabled={loadingReport || !esgReport}
        >
          ℹ️
        </button>
      </h2>

      {/* Display loading or error states, or render the ESG scores and chart */}
      {!ticker ? null : loadingScores ? (
        <p>Loading ESG data...</p>
      ) : !esgScoresLoaded ? (
        <p>No ESG data available.</p>
      ) : (
        <>
          <ul>
            <strong>Total ESG Risk Score:</strong> {esgScores['Total ESG Risk Score']}
          </ul>
          <ResponsiveContainer width="100%">
            <PieChart margin={{ top: 10, right: 10, left: -40, bottom: 30 }}>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {pieData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend verticalAlign="middle" align="right" layout="vertical" />
            </PieChart>
          </ResponsiveContainer>
        </>
      )}

      {/* ESG Report Modal */}
      <Modal
        isOpen={showESGModal}
        onRequestClose={() => setShowESGModal(false)}
        className="modal-content"
        overlayClassName="modal-overlay"
      >
        <h2>💡 ESG Commentary</h2>
        <div className="esg-report">
          {loadingReport ? <p>Loading...</p> : <ReactMarkdown>{esgReport}</ReactMarkdown>}
        </div>
        <button onClick={() => setShowESGModal(false)} className="close-btn">
          Close
        </button>
      </Modal>
    </div>
  );
};

export default ESGScore;
