import React, { useState } from 'react';
import './App.css';
import TickerInput from './components/TickerInput';
import Dashboard from './components/Dashboard';

function App() {
  // State to hold the selected ticker and investment type
  const [selectedTicker, setSelectedTicker] = useState('');
  const [investmentType, setInvestmentType] = useState('short-term');

  // Tracks whether data is being fetched to prevent duplicate submissions
  const [isLoading, setIsLoading] = useState(false);

  // Handles form submission from the TickerInput component
  const handleFormSubmit = ({ ticker, timeframe }) => {
    if (isLoading) return; // Ignore if a request is already in progress
    setIsLoading(true);
    setSelectedTicker(ticker);
    setInvestmentType(timeframe);
  };

  // Callback from Dashboard once all backend data has loaded
  const handleDashboardDone = () => {
    setIsLoading(false);
  };

  return (
    <div className="app-container">
      {/* Header section with branding and input form */}
      <header className="top-bar">
        <h1 className="app-title">
          Wealth<span className="wave-highlight">Wave</span>: Ride the Market Trends
        </h1>
        <TickerInput onSubmit={handleFormSubmit} loading={isLoading} />
      </header>

      {/* Main content showing the dashboard with insights */}
      <main className="main-content">
        <Dashboard
          ticker={selectedTicker}
          timeframe={investmentType}
          onAllDataLoaded={handleDashboardDone}
        />
      </main>

      {/* Decorative wave footer */}
      <div className="wave-container">
        <svg
          className="waves"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 1440 320"
          preserveAspectRatio="none"
        >
          <path
            fill="#4e73df"
            d="M0,96 C240,192 480,64 720,64 C960,64 1200,160 1440,128 L1440,320 L0,320 Z"
          />
          <path
            fill="none"
            stroke="#fff"
            strokeWidth="3"
            d="M0,96 C240,192 480,64 720,64 C960,64 1200,160 1440,128"
          />
          <path
            fill="#4e73df"
            d="M0,192 C240,96 480,256 720,256 C960,256 1200,192 1440,224 L1440,320 L0,320 Z"
          />
          <path
            fill="none"
            stroke="#fff"
            strokeWidth="3"
            d="M0,192 C240,96 480,256 720,256 C960,256 1200,192 1440,224"
          />
          <path
            fill="#4e73df"
            d="M0,256 C240,320 480,224 720,224 C960,224 1200,288 1440,288 L1440,320 L0,320 Z"
          />
          <path
            fill="none"
            stroke="#fff"
            strokeWidth="3"
            d="M0,256 C240,320 480,224 720,224 C960,224 1200,288 1440,288"
          />
        </svg>
      </div>
    </div>
  );
}

export default App;
