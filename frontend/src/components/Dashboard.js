import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import Modal from 'react-modal';
import ReactMarkdown from 'react-markdown';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';

Modal.setAppElement('#root');

const SHORT_TERM_PERIODS = ['1d', '5d', '1mo', '3mo', '1y'];
const LONG_TERM_PERIODS = ['5y', '10y', '15y'];

// to prevent auto refresh for esg chart
function ESGPieChart({ data }) {
  const COLORS = ['#4460ef', '#f44879', '#32c1a4'];

  const pieData = [
    { name: 'Environmental', value: data["Environmental Risk Score"] },
    { name: 'Social', value: data["Social Risk Score"] },
    { name: 'Governance', value: data["Governance Risk Score"] },
  ];

  return (
    <ResponsiveContainer width="100%">
      <PieChart margin={{ top: 10, right: 10, left: -40, bottom: 30 }}>
        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
          {pieData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend verticalAlign="middle" align="right" layout="vertical" />
      </PieChart>
    </ResponsiveContainer>
  );
}

function Dashboard({ ticker, timeframe, onAllDataLoaded }) {
  const [holisticSummary, setHolisticSummary] = useState('');
  const [loadingHolistic, setLoadingHolistic] = useState(false);

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

  const [financialData, setFinancialData] = useState([]);
  const [financialSummary, setFinancialSummary] = useState(null);
  const [financialInsight, setFinancialInsight] = useState(null);
  const [loadingFinancials, setLoadingFinancials] = useState(false);

  const [showFinancialModal, setShowFinancialModal] = useState(false);
  const [showESGModal, setShowESGModal] = useState(false);
  const [showStockModal, setShowStockModal] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    const defaultPeriod = timeframe === 'long-term' ? '5y' : '1y';
    setChartPeriod(defaultPeriod);
  }, [ticker, timeframe]);

  useEffect(() => {
    if (!ticker) return;

    const fetchData = async () => {
      setLoadingScores(true);
      setLoadingReport(true);
      setLoadingStockHistory(true);
      setLoadingMediaSentiment(true);
      setLoadingHolistic(true);

      try {
        try { // STOCK HISTORY PART: i think can combine with the ones below to make it neater
          const historyRes = await fetch('http://127.0.0.1:5000/api/stock-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, timeframe }),
          })
          const historyData = await historyRes.json();
          setStockHistory(historyData.recommendation || 'No stock history available.');
        } catch {
          setStockHistory('Error loading stock history.');
        } finally {
          setLoadingStockHistory(false);
        }

        const [scoresRes, reportRes, holisticRes, mediaRes] = await Promise.all([
          fetch('http://127.0.0.1:5000/api/esg-scores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker }),
          }),
          fetch('http://127.0.0.1:5000/api/esg-gen-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker }),
          }),
          fetch('http://127.0.0.1:5000/api/holistic-summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, timeframe }),
          }),
          fetch('http://127.0.0.1:5000/api/media-sentiment-summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
          })
        ]);

        // ESG Scores
        try {
          const scoresData = await scoresRes.json();
          setEsgScores(scoresData.esg_scores || {});
        } catch {
          setEsgScores(null);
        } finally {
          setLoadingScores(false);
        }
        
        // ESG Report
        try {
          const reportData = await reportRes.json();
          setEsgReport(reportData.report || 'No ESG report available.');
        } catch {
          setEsgReport('Error loading ESG report.');
        } finally {
          setLoadingReport(false);
        }
        
        // HOLISTIC SUMMARY
        try {
          const holisticData = await holisticRes.json();
          setHolisticSummary(holisticData.summary || 'No summary available.');
        } catch {
          setHolisticSummary('Error loading holistic summary.');
        } finally {
          setLoadingHolistic(false);
        }

        // MEDIA SENTIMENT
        try {
          const headlinesData = await mediaRes.json();
          setMediaSentiment(headlinesData.summary || 'No media headlines available.')
        } catch {
          setMediaSentiment('Error loading media headlines.');
        } finally {
          setLoadingMediaSentiment(false);
        }


      } catch {
        
      }
      if (onAllDataLoaded) onAllDataLoaded();
    };

    fetchData();
  }, [ticker, timeframe]);

  useEffect(() => {
    if (!ticker || !chartPeriod) return;

    const fetchChartData = async () => {
      setLoadingChart(true);
      try {
        const res = await fetch('http://127.0.0.1:5000/api/stock-chart', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker, period: chartPeriod }),
        });
        const data = await res.json();
        setChartData(data.prices || []);
      } catch {
        setChartData([]);
      } finally {
        setLoadingChart(false);
      }
    };

    fetchChartData();
  }, [ticker, chartPeriod]);

  useEffect(() => {
    if (!ticker || !timeframe) return;

    const fetchFinancialData = async () => {
      setLoadingFinancials(true);
      setFinancialData([]);
      setFinancialInsight(null);
      setFinancialSummary(null);

      try {
        const period = timeframe === 'long-term' ? '5y' : '1y';

        const [chartRes, recRes] = await Promise.all([
          fetch('http://127.0.0.1:5000/api/financial-chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, period }),
          }),
          fetch('http://127.0.0.1:5000/api/financial-recommendation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, period }),
          }),
        ]);

        const chartData = await chartRes.json();
        const recData = await recRes.json();

        setFinancialData(chartData.data || []);
        setFinancialSummary(recData.summary || 'No summary available.');
        setFinancialInsight(recData.commentary || 'No commentary available.');
      } catch {
        setFinancialSummary('Error loading financial summary.');
        setFinancialInsight('Error loading financial insight.');
        setFinancialData([]);
      } finally {
        setLoadingFinancials(false);
      }
    };

    fetchFinancialData();
  }, [ticker, timeframe]);

  const renderTabs = () => {
    const periods = timeframe === 'long-term' ? LONG_TERM_PERIODS : SHORT_TERM_PERIODS;
    return (
      <div className="range-tabs">
        {periods.map((p) => (
          <button key={p} className={chartPeriod === p ? 'active' : ''} onClick={() => setChartPeriod(p)}>
            {p.toUpperCase()}
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="dashboard-layout">
      <div className="left-card">
        <div className="card">
          <h2>At a Glance - {ticker}</h2>
          {loadingHolistic ? (
          <p>Loading holistic summary...</p>
          ) : (
            <div className='holistic-summary'>
              <ReactMarkdown>{holisticSummary}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>

      <div className="right-grid">
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
      

        <div className="card">
          <h2>
            Stock History Performance (USD)
            <button className="info-icon" onClick={() => setShowStockModal(true)} disabled={loadingStockHistory || !stockHistory}>
              ℹ️
            </button>
          </h2>
          {renderTabs()}
          {loadingChart ? (
            <p>Loading chart...</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -40, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis 
                  tick={{ fontSize: 12 }} 
                  tickFormatter={(value) =>
                    `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                  }
                />
                <Tooltip 
                  formatter={(value) =>
                    `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                  }
                />
                <Line type="monotone" dataKey="close" stroke="#4460ef" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h2>
            Financial Metrics Trends
            <button className="info-icon" onClick={() => setShowFinancialModal(true)} disabled={loadingFinancials || !financialInsight}>
              ℹ️
            </button>
          </h2>
          {loadingFinancials ? (
            <p>Loading financial chart...</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={financialData} margin={{ top: 10, right: 10, left: -20, bottom: -10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="quarter" tick={{ fontSize: 12 }} />
                <YAxis 
                  tick={{ fontSize: 12 }} 
                  tickFormatter={(value) => `${(value / 1_000_000).toLocaleString()}M`}
                />
                <Tooltip
                  formatter={(value) => `${(value / 1_000_000).toLocaleString()}M`} 
                />
                <Line type="monotone" dataKey="revenue" stroke="#4460ef" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="net_income" stroke="#f44879" strokeWidth = {3} dot={false} />
                <Line type="monotone" dataKey="free_cash_flow" stroke="#32c1a4" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h2>
            ESG Score
            <button className="info-icon" onClick={() => setShowESGModal(true)} disabled={loadingReport || !esgReport}>
              ℹ️
            </button>
          </h2>
          {loadingScores || loadingReport ? (
            <p>Loading ESG data...</p>
          ) : (
            esgScores && (
              <>
                <ul><strong>Total ESG Risk Score:</strong> {esgScores["Total ESG Risk Score"]}</ul>
                <ESGPieChart data={esgScores} />
              </>
            )
          )}
        </div>
      </div>

      <Modal
        isOpen={showStockModal}
        onRequestClose={() => setShowStockModal(false)}
        className="modal-content"
        overlayClassName="modal-overlay"
      >
        <h2>💡 Stock History Commentary</h2>
        <div className="stock-commentary">
          {stockHistory
            ? stockHistory.split('\n\n').map((pt, i) => (
                <ReactMarkdown key={i}>{pt}</ReactMarkdown>
              ))
            : <p>Loading...</p>}
        </div>
        <button onClick={() => setShowStockModal(false)} className="close-btn">Close</button>
      </Modal>

      <Modal isOpen={showFinancialModal} onRequestClose={() => setShowFinancialModal(false)} className="modal-content" overlayClassName="modal-overlay">
        <h2>Financial Summary & AI Commentary</h2>
        <div>
          <h3>📊 Summary</h3>
          <ReactMarkdown>{financialSummary || 'No summary available.'}</ReactMarkdown>

          <h3 style={{ marginTop: '1.5rem' }}>💡 Commentary</h3>
          <ReactMarkdown>{financialInsight || 'No commentary available.'}</ReactMarkdown>
        </div>
        <button onClick={() => setShowFinancialModal(false)} className="close-btn">Close</button>
      </Modal>

      <Modal isOpen={showESGModal} onRequestClose={() => setShowESGModal(false)} className="modal-content" overlayClassName="modal-overlay">
        <h2>💡 ESG Commentary</h2>
        <div className="esg-report">
          {loadingReport ? <p>Loading...</p> : <pre>{esgReport}</pre>}
        </div>
        <button onClick={() => setShowESGModal(false)} className="close-btn">Close</button>
      </Modal>
    </div>
  );
}

export default Dashboard;
