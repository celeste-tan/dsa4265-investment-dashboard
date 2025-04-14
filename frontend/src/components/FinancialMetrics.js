import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import Modal from 'react-modal';

/**
 * Displays financial metrics trends and analysis
 * @param {Object} props - Component props
 * @param {string} props.ticker - Stock ticker symbol
 * @param {Array} props.financialData - Financial data array
 * @param {string} props.financialView - Current view ('1y' or '5y')
 * @param {function} props.setFinancialView - Function to update view
 * @param {string} props.financialSummary - Financial summary text
 * @param {string} props.financialInsight - Financial commentary
 * @param {boolean} props.loadingFinancials - Loading state for summary/insight
 * @param {boolean} props.loadingFinancialData - Loading state for chart data
 * @param {boolean} props.showFinancialModal - Modal visibility state
 * @param {function} props.setShowFinancialModal - Function to toggle modal
 */

const FinancialMetrics = ({
  ticker,
  financialData,
  financialView,
  setFinancialView,
  financialSummary,
  financialInsight,
  loadingFinancials,
  loadingFinancialData,
  showFinancialModal,
  setShowFinancialModal,
}) => {
  return (
    <div className="card">
      <h2>
        Financial Metrics Trends
        <button
          className="info-icon"
          onClick={() => setShowFinancialModal(true)}
          disabled={loadingFinancials || !financialInsight}
        >
          ℹ️
        </button>
      </h2>

      {/* Toggle Buttons */}
      <div className="range-tabs" style={{ marginBottom: '0.5rem' }}>
        <button
          className={financialView === '1y' ? 'active' : ''}
          onClick={() => setFinancialView('1y')}
        >
          Quarterly
        </button>
        <button
          className={financialView === '5y' ? 'active' : ''}
          onClick={() => setFinancialView('5y')}
        >
          Annual
        </button>
      </div>

      {/* Financial Chart Visualization */}
      {!ticker || financialData.length === 0 ? null : (
        <div style={{ transform: 'scale(0.95)', transformOrigin: 'top left' }}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={financialData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} angle={0} textAnchor="middle"/>
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `${(value / 1_000_000).toLocaleString()}M`}
              />
              <Tooltip
                formatter={(value) => `${(value / 1_000_000).toLocaleString()}M`}
              />
              <Legend verticalAlign="bottom" height={40} />
              <Line type="monotone" dataKey="revenue" stroke="#4460ef" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="net_income" stroke="#f44879" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="free_cash_flow" stroke="#32c1a4" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Financial Metrics Modal */}
      <Modal
        isOpen={showFinancialModal}
        onRequestClose={() => setShowFinancialModal(false)}
        className="modal-content"
        overlayClassName="modal-overlay"
      >
        <h2>Financial Summary & AI Commentary</h2>
        <div>
          <h3>📊 Summary</h3>
          <ReactMarkdown>{financialSummary || 'No summary available.'}</ReactMarkdown>
          <h3 style={{ marginTop: '1.5rem' }}>💡 Commentary</h3>
          <ReactMarkdown>{financialInsight || 'No commentary available.'}</ReactMarkdown>
        </div>
        <button onClick={() => setShowFinancialModal(false)} className="close-btn">
          Close
        </button>
      </Modal>
    </div>
  );
};

export default FinancialMetrics;
