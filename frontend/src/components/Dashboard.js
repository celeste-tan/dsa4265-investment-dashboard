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

  const [financialView, setFinancialView] = useState('1y'); // NEW STATE

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
        const [historyRes, scoresRes, reportRes, mediaRes] = await Promise.all([
          fetch('http://127.0.0.1:5000/api/stock-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, timeframe }),
          }),
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
          fetch('http://127.0.0.1:5000/api/media-sentiment-summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
          })
        ]);

        const historyData = await historyRes.json();
        setStockHistory(historyData.recommendation || 'No stock history available.');
        setLoadingStockHistory(false);

        const scoresData = await scoresRes.json();
        setEsgScores(scoresData.esg_scores || {});
        setLoadingScores(false);

        const headlinesData = await mediaRes.json();
        setMediaSentiment(headlinesData.summary || 'No media headlines available.');
        setLoadingMediaSentiment(false);

        const reportData = await reportRes.json();
        setEsgReport(reportData.report || 'No ESG report available.');
        setLoadingReport(false);

        const holisticRes = await fetch('http://127.0.0.1:5000/api/holistic-summary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker, timeframe }),
        });
        const holisticData = await holisticRes.json();
        setHolisticSummary(holisticData.summary || 'No summary available.');
        setLoadingHolistic(false);
      } catch {
        setStockHistory('Error loading stock history.');
        setEsgScores(null);
        setMediaSentiment('Error loading media headlines.');
        setEsgReport('Error loading ESG report.');
        setHolisticSummary('Error loading holistic summary.');
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
    if (!ticker || !financialView) return;

    const fetchFinancialData = async () => {
      setLoadingFinancials(true);
      setFinancialData([]);
      setFinancialInsight(null);
      setFinancialSummary(null);

      try {
        const period = financialView;

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
  }, [ticker, financialView]); // includes financialView now

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
      {/* Holistic Summary */}
      <div className="left-card">
        <div className="card">
          <h2>At a Glance - {ticker}</h2>
          {loadingHolistic ? (
            <p>Loading holistic summary...</p>
          ) : (
            <div className="holistic-summary">
              <ReactMarkdown>{holisticSummary}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel */}
      <div className="right-grid">

        {/* Media */}
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

        {/* Stock History Chart */}
        <div className="card">
          <h2>
            Stock History Performance (USD)
            <button className="info-icon" onClick={() => setShowStockModal(true)} disabled={loadingStockHistory || !stockHistory}>ℹ️</button>
          </h2>
          {renderTabs()}
          {loadingChart ? (
            <p>Loading chart...</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -40, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v.toLocaleString()}`} />
                <Tooltip formatter={(v) => `$${v.toLocaleString()}`} />
                <Line type="monotone" dataKey="close" stroke="#4460ef" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
{/* Financial Chart + Toggle */}
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

  {/* Toggle Buttons only */}
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
{loadingFinancials ? (
  <p>Loading financial chart...</p>
) : (
  <div style={{ transform: 'scale(0.95)', transformOrigin: 'top left' }}>
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={financialData} margin={{ top: 10, right: 60, left: 0, bottom: 30 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 12 }}
          interval={0}
          angle={0}
          textAnchor="middle"
        />
        <YAxis
          tick={{ fontSize: 12 }}
          tickFormatter={(v) => `${(v / 1_000_000).toLocaleString()}M`}
        />
        <Tooltip formatter={(v) => `${(v / 1_000_000).toLocaleString()}M`} />

        {/* One Label Per Line at Final Data Point */}
        <Line
          type="monotone"
          dataKey="revenue"
          stroke="#4460ef"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="Revenue"
          label={({ index, x, y }) =>
            index === financialData.length - 1 ? (
              <text x={x + 8} y={y} fill="#4460ef" fontSize={11}>
                Revenue
              </text>
            ) : null
          }
        />
        <Line
          type="monotone"
          dataKey="net_income"
          stroke="#f44879"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="Net Income"
          label={({ index, x, y }) =>
            index === financialData.length - 1 ? (
              <text x={x + 8} y={y} fill="#f44879" fontSize={11}>
                Net Income
              </text>
            ) : null
          }
        />
        <Line
          type="monotone"
          dataKey="free_cash_flow"
          stroke="#32c1a4"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="Free Cash Flow"
          label={({ index, x, y }) =>
            index === financialData.length - 1 ? (
              <text x={x + 8} y={y} fill="#32c1a4" fontSize={11}>
                Free Cash Flow
              </text>
            ) : null
          }
        />
      </LineChart>
    </ResponsiveContainer>
  </div>
)}
</div>






        {/* ESG Score */}
        <div className="card">
          <h2>
            ESG Score
            <button className="info-icon" onClick={() => setShowESGModal(true)} disabled={loadingReport || !esgReport}>ℹ️</button>
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

      {/* Modals (stock, financial, ESG) */}
      {/* ...existing modal code stays unchanged... */}
    </div>
  );
}

export default Dashboard;
