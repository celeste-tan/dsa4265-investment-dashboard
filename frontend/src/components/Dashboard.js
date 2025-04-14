import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import Modal from 'react-modal';
import HolisticSummary from './HolisticSummary';
import MediaAnalysis from './MediaAnalysis';
import StockHistory from './StockHistory';
import FinancialMetrics from './FinancialMetrics';
import ESGScore from './ESGScore';

Modal.setAppElement('#root');

// Define available periods for short-term and long-term views
const SHORT_TERM_PERIODS = ['1d', '5d', '1mo', '3mo', '1y'];
const LONG_TERM_PERIODS = ['5y', '10y', '15y'];

function Dashboard({ ticker, timeframe, onAllDataLoaded }) {
    // ============================
    // State Declarations
    // ============================
    // Holistic Summary
    const [holisticSummary, setHolisticSummary] = useState('');
    const [loadingHolistic, setLoadingHolistic] = useState(false);

    // Stock Chart Data
    const [chartData, setChartData] = useState([]);
    const [chartPeriod, setChartPeriod] = useState('1y');
    const [loadingChart, setLoadingChart] = useState(false);

    // ESG Scores / Report
    const [esgScores, setEsgScores] = useState(null);
    const [esgScoresLoaded, setEsgScoresLoaded] = useState(false);
    const [esgReport, setEsgReport] = useState(null);

    // Stock History and Media Sentiment
    const [stockHistory, setStockHistory] = useState(null);
    const [mediaSentiment, setMediaSentiment] = useState(null);
    const [loadingScores, setLoadingScores] = useState(false);
    const [loadingReport, setLoadingReport] = useState(false);
    const [loadingStockHistory, setLoadingStockHistory] = useState(false);
    const [loadingMediaSentiment, setLoadingMediaSentiment] = useState(false);

    // Financial Data and Insights
    const [financialData, setFinancialData] = useState([]);
    const [financialSummary, setFinancialSummary] = useState(null);
    const [financialInsight, setFinancialInsight] = useState(null);
    const [loadingFinancials, setLoadingFinancials] = useState(false);
    const [loadingFinancialData, setLoadingFinancialData] = useState(false);

    // Modal Visibility Controls
    const [showFinancialModal, setShowFinancialModal] = useState(false);
    const [showESGModal, setShowESGModal] = useState(false);
    const [showStockModal, setShowStockModal] = useState(false);

    // Financial View Period
    const [financialView, setFinancialView] = useState('1y');

    // ============================
    // Side Effects & Data Fetching
    // ============================
    // Parent Callback Trigger for Holistic Summary
    useEffect(() => {
        if (holisticSummary !== '') {
            onAllDataLoaded();
        }
    }, [holisticSummary, onAllDataLoaded]);

    // Set Default Chart Period Based on Ticker and Timeframe
    useEffect(() => {
        if (!ticker) return;
        const defaultPeriod = timeframe === 'long-term' ? '5y' : '1y';
        setChartPeriod(defaultPeriod);
    }, [ticker, timeframe]);

    // --- Begin: Data Fetching Section ---

    // Fetch ESG Scores
    useEffect(() => {
        if (!ticker) return;
        const fetchEsgScores = async () => {
            setLoadingScores(true);
            try {
                const res = await fetch('http://127.0.0.1:5000/api/esg-scores', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker }),
                });
                const scoresData = await res.json();
                setEsgScores(scoresData.esg_scores || {});
                setEsgScoresLoaded(true);
            } catch {
                setEsgScores({});
            } finally {
                setLoadingScores(false);
            }
        };
        fetchEsgScores();
    }, [ticker]);

    // Fetch Stock Chart Data
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

    // Fetch Financial Chart Data
    useEffect(() => {
        if (!ticker) return;
        const fetchMetrics = async () => {
            setLoadingFinancialData(true);
            setFinancialData([]);
            try {
                const period = financialView;
                const res = await fetch('http://127.0.0.1:5000/api/financial-chart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker, period }),
                });
                const chartData = await res.json();
                setFinancialData(chartData.data || []);
            } catch {
                setFinancialData([]);
            } finally {
                setLoadingFinancialData(false);
            }
        };
        fetchMetrics();
    }, [ticker, financialView]);

    // Fetch Financial Recommendations (Summary and Insight)
    useEffect(() => {
        if (!ticker || !financialView) return;
        const fetchFinancialData = async () => {
            setLoadingFinancials(true);
            setFinancialInsight(null);
            setFinancialSummary(null);
            try {
                const period = financialView;
                const [recRes] = await Promise.all([
                    fetch('http://127.0.0.1:5000/api/financial-recommendation', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticker, period }),
                    }),
                ]);
                const recData = await recRes.json();
                setFinancialSummary(recData.summary || 'No summary available.');
                setFinancialInsight(recData.commentary || 'No commentary available.');
            } catch {
                setFinancialSummary('Error loading financial summary.');
                setFinancialInsight('Error loading financial insight.');
            } finally {
                setLoadingFinancials(false);
            }
        };
        fetchFinancialData();
    }, [ticker, financialView]);

    // Fetch Stock History (Commentary)
    useEffect(() => {
        if (!ticker || !timeframe) return;
        const fetchStockHistory = async () => {
            setLoadingStockHistory(true);
            try {
                const res = await fetch('http://127.0.0.1:5000/api/stock-history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker, timeframe }),
                });
                const data = await res.json();
                setStockHistory(data.recommendation || 'No stock history available.');
            } catch {
                setStockHistory('Error loading stock history.');
            } finally {
                setLoadingStockHistory(false);
            }
        };
        fetchStockHistory();
    }, [ticker, timeframe]);

    // Fetch ESG Report
    useEffect(() => {
        if (!ticker) return;
        const fetchEsgReport = async () => {
            setLoadingReport(true);
            try {
                const res = await fetch('http://127.0.0.1:5000/api/esg-gen-report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker }),
                });
                const data = await res.json();
                setEsgReport(data.report || 'No ESG report available.');
            } catch {
                setEsgReport('Error loading ESG report.');
            } finally {
                setLoadingReport(false);
            }
        };
        fetchEsgReport();
    }, [ticker]);

    // Fetch Media Sentiment
    useEffect(() => {
        if (!ticker) return;
        const fetchMediaSentiment = async () => {
            setLoadingMediaSentiment(true);
            try {
                const res = await fetch('http://127.0.0.1:5000/api/media-sentiment-summary', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker }),
                });
                const data = await res.json();
                setMediaSentiment(data.summary || 'No media headlines available.');
            } catch {
                setMediaSentiment('Error loading media headlines.');
            } finally {
                setLoadingMediaSentiment(false);
            }
        };
        fetchMediaSentiment();
    }, [ticker]);

    // Fetch Holistic Summary
    useEffect(() => {
        if (!ticker || !timeframe) return;
        const fetchHolisticSummary = async () => {
            setLoadingHolistic(true);
            try {
                const res = await fetch('http://127.0.0.1:5000/api/holistic-summary', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker, timeframe }),
                });
                const data = await res.json();
                setHolisticSummary(data.summary || 'No summary available.');
            } catch {
                setHolisticSummary('Error loading holistic summary.');
            } finally {
                setLoadingHolistic(false);
            }
        };
        fetchHolisticSummary();
    }, [ticker, timeframe]);

    // --- End: Data Fetching Section ---

    // Render Tabs for Stock Chart Period Selection
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

    // ============================
    // Render Dashboard Layout
    // ============================
    return (
        <div className="dashboard-layout">
            <HolisticSummary 
                holisticSummary={holisticSummary}
                loading={loadingHolistic}
                ticker={ticker}
            />
            <div className="right-grid">
                <MediaAnalysis 
                    mediaSentiment={mediaSentiment}
                    loading={loadingMediaSentiment}
                />
                <StockHistory
                    ticker={ticker}
                    timeframe={timeframe}
                    chartData={chartData}
                    chartPeriod={chartPeriod}
                    setChartPeriod={setChartPeriod}
                    loadingChart={loadingChart}
                    stockHistory={stockHistory}
                    loadingStockHistory={loadingStockHistory}
                    showStockModal={showStockModal}
                    setShowStockModal={setShowStockModal}
                />
                <FinancialMetrics
                    ticker={ticker}
                    financialData={financialData}
                    financialView={financialView}
                    setFinancialView={setFinancialView}
                    financialSummary={financialSummary}
                    financialInsight={financialInsight}
                    loadingFinancials={loadingFinancials}
                    loadingFinancialData={loadingFinancialData}
                    showFinancialModal={showFinancialModal}
                    setShowFinancialModal={setShowFinancialModal}
                />
                <ESGScore
                    ticker={ticker}
                    esgScores={esgScores}
                    esgScoresLoaded={esgScoresLoaded}
                    esgReport={esgReport}
                    loadingScores={loadingScores}
                    loadingReport={loadingReport}
                    showESGModal={showESGModal}
                    setShowESGModal={setShowESGModal}
                />
            </div>
        </div>
    );
}

export default Dashboard;
