import React, { useState } from 'react';
import './TickerInput.css';

function TickerInput() {
  const [ticker, setTicker] = useState('');
  const [investmentType, setInvestmentType] = useState('short'); // 'short' or 'long'

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Ticker:', ticker);
    console.log('Investment Type:', investmentType);
    setTicker(''); // Reset ticker input after submission
  };

  return (
    <form onSubmit={handleSubmit} className="ticker-form">
      <input
        type="text"
        placeholder="Input Ticker"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
      />
      <select
        value={investmentType}
        onChange={(e) => setInvestmentType(e.target.value)}
      >
        <option value="short">Short Term</option>
        <option value="long">Long Term</option>
      </select>
      <button type="submit">Submit</button>
    </form>
  );
}

export default TickerInput;
