# 💹 WealthWave Investment Dashboard

WealthWave is a full-stack AI-powered dashboard designed to assist retail investors in making holistic, data-driven investment decisions. The platform integrates stock history, financial health, ESG ratings, and media sentiment into an intuitive interface, powered by OpenAI and real-time market data.

## 🧠 Features

### 📈 Stock History Performance
- Volatility analysis over selectable periods (1 day to 15 years)
- AI generated technical indicators (SMA, EMA, RSI) and analysis of what those numbers mean


### 💰 Financial Metrics
- Key metrics visualization (revenue, net income, free cash flow)
- AI-generated commentary on financial health
- Historical performance trends

### 🌿 ESG Insights
- Comprehensive ESG risk scoring
- Sub-category breakdowns (Environmental, Social, Governance)
- Controversy tracking and alerts
- AI generated insights to explain the numbers and their meanings

### 📰 Media Analysis
- Real-time news headline scraping via Telegram
- Summary of news headlines over the past 6 months from The Business Times


### ✅ Holistic Recommendation
- GPT-4o-generated buy/hold/sell judgement
- Multi-dimensional analysis combining all 4 outputs generated from above

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm/yarn
- Telegram account (for news scraping)

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm/yarn
- Telegram account (for news scraping)

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-user>/dsa4265-investment-dashboard.git
cd dsa4265-investment-dashboard

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Configure environment variables
# Create a .env file in root folder with these contents:
OPENAI_API_KEY="your_openai_key"
ESG_API_TOKEN="your_esg_token"
API_ID="your_telegram_api_id"
API_HASH="your_telegram_api_hash"
PHONE="your_phone_number"
USERNAME="your_telegram_username"
STRING_SESSION="your_telegram_string_session"

# Install backend dependencies
pip install -r requirements.txt

# Start backend server
cd backend
python app.py
# Backend runs at: http://127.0.0.1:5000

# In a new terminal, setup frontend
cd frontend
npm install
npm start
# Frontend runs at: http://localhost:3000

Note: Contact us to get access to credentials or generate your own using generate_string_session.py.
```

Note: Contact us to get access to credentials or generate your own using `generate_string_session.py`.

## 📁 Folder Structure

```
dsa4265-investment-dashboard/
├── backend/                   # FastAPI backend logic
│   ├── app.py                 # Main entry point for the backend server
│   └── utils/                 # Core logic for each analysis component
│       ├── stock_history.py
│       ├── esg_score.py
│       ├── financial_metrics.py
│       ├── media_analysis.py
│       └── holistic_summary.py
├── frontend/                  # React frontend interface
│   ├── public/                # Static assets and index.html
│   ├── src/
│   │   └── components/        # React components for UI rendering
│   │       ├── Dashboard.js         # Calls all 5 components and renders them in the dashboard
│   │       ├── StockHistory.js
│   │       ├── ESGScore.js
│   │       ├── FinancialMetrics.js
│   │       ├── MediaAnalysis.js
│   │       └── HolisticSummary.js
│   ├── App.js                 # Main frontend application
│   └── index.js               # Entry point for React
├── requirements.txt           # Python dependencies
├── package.json               # Frontend dependencies
├── .env                       # API credentials (excluded from version control)
└── README.md                  # Project documentation
```

## ⚠️ Disclaimer

This tool is intended for educational and informational purposes only. It does not constitute financial advice. Always consult a licensed financial advisor before making any investment decisions.
