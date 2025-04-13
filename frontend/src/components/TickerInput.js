import React, { useState, useEffect } from 'react';
import './TickerInput.css';

function TickerInput({ onSubmit, loading }) {
  const [ticker, setTicker] = useState('');
  const [timeframe, setTimeframe] = useState('short-term');
  const [submitted, setSubmitted] = useState(false);

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!ticker || loading || submitted) return;
    setSubmitted(true);
    onSubmit({ ticker: ticker.trim().toUpperCase(), timeframe });
  };

  // Reset input after loading is complete
  useEffect(() => {
    if (!loading) {
      setTicker('');
      setSubmitted(false);
    }
  }, [loading, submitted]);

  return (
    <form className="ticker-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Input Ticker"
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        disabled={loading || submitted}
      />
      <select
        value={timeframe}
        onChange={(e) => setTimeframe(e.target.value)}
        disabled={loading || submitted}
      >
        <option value="short-term">Short Term</option>
        <option value="long-term">Long Term</option>
      </select>
      <button type="submit" disabled={loading || submitted || !ticker.trim()}>
        {loading || submitted ? 'Loading...' : 'Submit'}
      </button>
    </form>
  );
}

export default TickerInput;
