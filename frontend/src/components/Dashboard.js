import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import Modal from 'react-modal';
import ReactMarkdown from 'react-markdown';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';


Modal.setAppElement('#root'); // for accessibility (screen readers)

// Define chart time ranges
const SHORT_TERM_PERIODS = ['1d', '5d', '1mo', '3mo', '1y'];
const LONG_TERM_PERIODS = ['5y', '10y', '15y'];

function Dashboard({ ticker, timeframe, onAllDataLoaded }) {
  // State hooks for chart and data
  const [chartData, setChartData] = useState([]);
  const [chartPeriod, setChartPeriod] = useState('1y');
  const [loadingChart, setLoadingChart] = useState(false);

  const [esgScores, setEsgScores] = useState(null);
  const [esgReport, setEsgReport] = useState(null);
  const [stockHistory, setStockHistory] = useState(null);
  const [mediaSentiment, setMediaSentiment] = useState(null);
  const [loadingScores, setLoadingScores] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingStockHistory, setLoadingStockHistory] = useState(false);
  const [loadingMediaSentiment, setLoadingMediaSentiment] = useState(false);

  const [showESGModal, setShowESGModal] = useState(false);
  const [showStockModal, setShowStockModal] = useState(false);

  // Set default chart period based on selected timeframe
  useEffect(() => {
    if (!ticker) return;
    const defaultPeriod = timeframe === 'long-term' ? '5y' : '1y';
    setChartPeriod(defaultPeriod);
  }, [ticker, timeframe]);


  // Fetch ESG scores, reports, and stock insights when ticker/timeframe changes
  useEffect(() => {
    if (!ticker) return;

    const fetchDashboardData = async () => {
      // Set loading states
      setLoadingScores(true);
      setLoadingReport(true);
      setLoadingStockHistory(true);
      setLoadingMediaSentiment(true);

      // Clear current data
      setEsgScores(null);
      setEsgReport(null);
      setStockHistory(null);
      setMediaSentiment(null);

      // Fetch ESG scores
      try {
        const scoresResponse = await fetch('http://127.0.0.1:5000/api/esg-scores', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker }),
        });
        const scoresData = await scoresResponse.json();
        setEsgScores(scoresData.esg_scores || 'No ESG scores available.');
      } catch (error) {
        setEsgScores('Error fetching ESG scores.');
      } finally {
        setLoadingScores(false);
      }

      // Fetch ESG report
      try {
        const reportResponse = await fetch('http://127.0.0.1:5000/api/esg-gen-report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker }),
        });
        const reportData = await reportResponse.json();
        setEsgReport(reportData.report || 'No ESG report available.');
      } catch (error) {
        setEsgReport('Error fetching ESG report.');
      } finally {
        setLoadingReport(false);
      }

      // Fetch stock recommendation
      try {
        const historyResponse = await fetch('http://127.0.0.1:5000/api/stock-history', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker, timeframe }),
        });
        const historyData = await historyResponse.json();
        setStockHistory(historyData.recommendation || 'No stock history available.');
      } catch (error) {
        setStockHistory('Error fetching stock history.');
      } finally {
        setLoadingStockHistory(false);
      }

      // Fetch media headlines & generate summary
      try {
        const headlinesResponse = await fetch('http://127.0.0.1:5000/api/media-sentiment-summary',{
          method: 'POST',
          headers: { 'Content-Type': 'application/json'},
          body: JSON.stringify({ ticker }),
        });
        const headlinesData = await headlinesResponse.json();
        // console.log(headlinesData)
        setMediaSentiment(headlinesData.summary || 'No media headlines available')
      } catch (error) {
        setMediaSentiment('Error fetching media data.');
      } finally {
        setLoadingMediaSentiment(false);
      }

      // Notify parent (App) that all data is fetched
      if (onAllDataLoaded) onAllDataLoaded();
    };

    fetchDashboardData();
  }, [ticker, timeframe]);

  // Fetch historical stock price chart data
  useEffect(() => {
    if (!ticker || !chartPeriod) return;

    const fetchChartData = async () => {
      setLoadingChart(true);
      try {
        const response = await fetch('http://127.0.0.1:5000/api/stock-chart', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker, period: chartPeriod }),
        });
        const data = await response.json();
        setChartData(data.prices || []);
      } catch {
        setChartData([]);
      } finally {
        setLoadingChart(false);
      }
    };

    fetchChartData();
  }, [ticker, chartPeriod]);

  // Render short or long term buttons
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

  const ESGPieChart = ({ data }) => {
    const COLORS = ['#82ca9d', '#8884d8', '#ffc658']; // Env, Social, Gov
  
    const pieData = [
      { name: 'Environmental', value: data["Environmental Risk Score"] },
      { name: 'Social', value: data["Social Risk Score"] },
      { name: 'Governance', value: data["Governance Risk Score"] },
    ];
  
    return (
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
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
          <Legend
            verticalAlign="bottom"
            height={36}
            layout="horizontal"
            iconType="circle"
            wrapperStyle={{ lineHeight: '40px' }}
          />
        </PieChart>
      </ResponsiveContainer>
    );
  };
  
  
  
  return (
    <div className="dashboard-layout">
      {/* Left summary */}
      <div className="left-card">
        <div className="card">
          <h2>At a Glance - {ticker}</h2>
        </div>
      </div>

      {/* Right metrics grid */}
      <div className="right-grid">
        {/* Placeholder for media sentiment */}
        <div className="card">
          <h2>Media Sentiment Analysis</h2>
          {loadingMediaSentiment ? (
            <p>Loading media analysis...</p>
          ) : (
            <div className="media-summary">
              <p>{mediaSentiment}</p>
            </div>
          )}
        </div>

        {/* Stock performance + chart */}
        <div className="card">
          <h2>
            Stock History Performance
            <button
              className="info-icon"
              onClick={() => setShowStockModal(true)}
              disabled={loadingStockHistory || !stockHistory}
              style={{ marginLeft: '10px', opacity: loadingStockHistory || !stockHistory ? 0.5 : 1 }}
            >
              ℹ️
            </button>
          </h2>
          {renderTabs()}
          {loadingChart ? (
            <p>Loading chart...</p>
          ) : (
            <div style={{ height: 'calc(100% - 100px)', margin: '0 -10px 10px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    interval="preserveStartEnd"
                    minTickGap={20}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 12 }}
                    label={{
                      value: 'Price (USD)',
                      angle: -90,
                      position: 'insideLeft',
                      offset: 10,
                      style: { textAnchor: 'middle', fill: '#000' },
                    }}
                  />
                  <Tooltip />
                  <Line type="monotone" dataKey="close" stroke="#4e73df" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Placeholder card for future use */}
        <div className="card">
          <h2>Financial Statements</h2>
        </div>
      
        {/* ESG Scores */}
        <div className="card">
          <h2>
            ESG Score
            <button
              className="info-icon"
              onClick={() => setShowESGModal(true)}
              disabled={loadingReport || !esgReport}
              style={{ marginLeft: '10px', opacity: loadingReport || !esgReport ? 0.5 : 1 }}
            >
              ℹ️
            </button>
          </h2>

          {loadingScores || loadingReport ? (
            <p>Loading ESG data...</p>
          ) : (
            esgScores && esgReport && (
              <>
                <ul>
                  <strong>Total ESG Risk Score:</strong> {esgScores["Total ESG Risk Score"]}
                  {/* <li><strong>Environmental Risk Score:</strong> {esgScores["Environmental Risk Score"]}</li>
                  <li><strong>Social Risk Score:</strong> {esgScores["Social Risk Score"]}</li>
                  <li><strong>Governance Risk Score:</strong> {esgScores["Governance Risk Score"]}</li> */}
                </ul>

                {/* Charts */}
                <div className="mt-6">
                  <ESGPieChart data={esgScores} />
                </div>

                {/* <ul>
                  <strong>Controversy Level:</strong> {esgScores["Controversy Level"]}
                  <li><strong>Peer Controversy (Min):</strong> {esgScores["Peer Controversy Min"]}</li>
                  <li><strong>Peer Controversy (Avg):</strong> {esgScores["Peer Controversy Avg"]}</li>
                  <li><strong>Peer Controversy (Max):</strong> {esgScores["Peer Controversy Max"]}</li>
                </ul> */}
              </>
            )
          )}
        </div>
      </div>
      

      {/* ESG Modal */}
      <Modal
        isOpen={showESGModal}
        onRequestClose={() => setShowESGModal(false)}
        className="modal-content"
        overlayClassName="modal-overlay"
      >
        <h2>ESG Report for {ticker}</h2>
        <div className="esg-report">
          {loadingReport ? <p>Loading detailed ESG report...</p> : <pre>{esgReport}</pre>}
        </div>
        <button onClick={() => setShowESGModal(false)} className="close-btn">Close</button>
      </Modal>

      {/* Stock Insight Modal */}
      <Modal
        isOpen={showStockModal}
        onRequestClose={() => setShowStockModal(false)}
        className="modal-content"
        overlayClassName="modal-overlay"
      >
        <h2>Stock History Insights for {ticker}</h2>
        <div className="stock-history-report">
          {loadingStockHistory ? (
            <p>Loading detailed stock history...</p>
          ) : stockHistory ? (
            stockHistory.split('\n\n').map((para, idx) => (
              <p key={idx} style={{ marginBottom: '1rem' }}>
                <ReactMarkdown>{para}</ReactMarkdown>
              </p>
            ))
          ) : (
            <p>No stock history available.</p>
          )}
        </div>
        <button onClick={() => setShowStockModal(false)} className="close-btn">
          Close
        </button>
      </Modal>
    </div>
  );
}

export default Dashboard;
