import React from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Displays the holistic summary of the stock analysis
 * @param {Object} props - Component props
 * @param {string} props.holisticSummary - The summary text to display
 * @param {boolean} props.loading - Loading state
 * @param {string} props.ticker - Stock ticker symbol
 */
const HolisticSummary = ({ holisticSummary, loading, ticker }) => {
  return (
    <div className="left-card">
      <div className="card">
        <h2>At a Glance - {ticker}</h2>
        {loading ? (
          <p>Loading holistic summary...</p>
        ) : (
          <div className="holistic-summary">
            <ReactMarkdown>{holisticSummary}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
};

export default HolisticSummary;
