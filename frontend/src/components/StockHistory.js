import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import Modal from 'react-modal';

/**
 * StockHistory Component
 *
 * Displays a line chart of stock price history along with commentary.
 *
 * Props:
 * - ticker: Stock ticker symbol.
 * - timeframe: Timeframe ('short-term' or 'long-term').
 * - chartData: Array of data points for the chart.
 * - chartPeriod: Currently selected period for the chart.
 * - setChartPeriod: Function to update the selected chart period.
 * - loadingChart: Boolean flag indicating if the chart data is loading.
 * - stockHistory: Commentary text for stock history.
 * - loadingStockHistory: Boolean flag indicating if the commentary is loading.
 * - showStockModal: Boolean to control the visibility of the stock history modal.
 * - setShowStockModal: Function to toggle the modal visibility.
 */
const StockHistory = ({
  ticker,
  timeframe,
  chartData,
  chartPeriod,
  setChartPeriod,
  loadingChart,
  stockHistory,
  loadingStockHistory,
  showStockModal,
  setShowStockModal,
}) => {
  // Define period options based on the timeframe
  const SHORT_TERM_PERIODS = ['1d', '5d', '1mo', '3mo', '1y'];
  const LONG_TERM_PERIODS = ['5y', '10y', '15y'];

  // Render tabs to select the chart period
  const renderTabs = () => {
    const periods = timeframe === 'long-term' ? LONG_TERM_PERIODS : SHORT_TERM_PERIODS;
    return (
      <div className="range-tabs">
        {periods.map((p) => (
          <button
            key={p}
            className={chartPeriod === p ? 'active' : ''}
            onClick={() => setChartPeriod(p)}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="card">
      <h2>
        Stock History Performance (USD)
        {/* Info icon to open the stock history commentary modal */}
        <button
          className="info-icon"
          onClick={() => setShowStockModal(true)}
          disabled={loadingStockHistory || !stockHistory}
        >
          ℹ️
        </button>
      </h2>

      {/* Render period selection tabs */}
      {renderTabs()}

      {/* Render the line chart or a loading indicator */}
      {loadingChart ? (
        <p>Loading chart...</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -40, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v.toLocaleString()}`} />
            <Tooltip formatter={(v) => `$${v.toLocaleString()}`} />
            <Line type="monotone" dataKey="close" stroke="#4460ef" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}

      {/* Stock History Commentary Modal */}
      <Modal
        isOpen={showStockModal}
        onRequestClose={() => setShowStockModal(false)}
        className="modal-content"
        overlayClassName="modal-overlay"
      >
        <h2>💡 Stock History Commentary</h2>
        <p
          style={{
            fontSize: '14px',
            fontStyle: 'italic',
            marginTop: '10px',
            marginBottom: '10px',
            color: '#ccc',
          }}
        >
          📌 Note: Short-term (ST) insights are based on 1-year data. Long-term (LT) insights are based on 15-year data.
        </p>
        <div>
          {stockHistory
            ? stockHistory.split('\n\n').map((pt, i) => (
                <ReactMarkdown key={i}>{pt}</ReactMarkdown>
              ))
            : <p>Loading...</p>}
        </div>
        <button onClick={() => setShowStockModal(false)} className="close-btn">
          Close
        </button>
      </Modal>
    </div>
  );
};

export default StockHistory;
