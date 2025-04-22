# 💹 WealthWave Investment Dashboard

**WealthWave** is a full-stack, AI-powered dashboard designed to assist retail investors in making holistic, data-driven investment decisions. The platform seamlessly integrates stock history, financial health, ESG ratings, and media sentiment into an intuitive interface—powered by OpenAI and real-time market data.
[Explore the technical document here](https://docs.google.com/document/d/1aLdd7UDTqBozy8Sius7_xDuM9LQTB_dgH7p6RgG1eOI/edit?usp=sharing)

---

## 🧠 Features

### 📈 Stock History Performance
- Volatility analysis over selectable periods (1 day to 15 years)
- AI-generated technical indicators (SMA, EMA, RSI) with plain-language interpretation

### 💰 Financial Metrics
- Visualisation of key financials: revenue, net income, and free cash flow
- AI-generated commentary on financial health
- Historical trend tracking for better decision-making

### 🌿 ESG Insights
- ESG risk scores with breakdowns across Environmental, Social, and Governance dimensions
- Controversy tracking with real-time alerts
- AI-generated summaries to contextualise ESG data

### 📰 Media Analysis
- Real-time news scraping from Telegram sources
- Summarisation of headlines from *The Business Times* over the past 6 months

### ✅ Holistic Recommendation
- GPT-4o-powered buy/hold/sell decisions
- Integrated insights from all other modules: stock history, financials, ESG, and news sentiment

---

## ⚙️ Setup Instructions

### Prerequisites

Before installation, ensure the following are available:

- Python 3.8+
- Node.js 16+
- npm
- Telegram account (required for media scraping)
- OpenAI API key

---

### 🔧 Installation & Environment Setup

Follow the steps below to set up the project locally:

1. **Clone the repository and activate a virtual environment:**

    ```bash
    git clone https://github.com/celeste-tan/dsa4265-investment-dashboard.git  # Clone the project
    cd dsa4265-investment-dashboard

    python -m venv venv        # Create a virtual environment
    source venv/bin/activate   # Activate it (use venv\Scripts\activate on Windows)
    ```

2. **Configure Telegram API credentials (for news scraping):**

    - [Follow the guide](https://core.telegram.org/api/obtaining_api_id) to obtain your **API ID** and **API HASH**.
    - Generate your `STRING_SESSION` by running:

      ```bash
      cd backend/utils
      python generate_string_session.py  # Generates a session string after login via terminal
      ```

      Once done, copy the session string output.

    - Return to the root folder:

      ```bash
      cd ../../
      ```
3. **Creating an OpenAI API key (for generation of commentaries):**

   - Login to [OpenAI](https://platform.openai.com)
   - Navigate to 'API Keys' from the dropdown under your profile or go directly to the [API Keys Page](https://platform.openai.com/api-keys)
   - Create a new key and give it a name (optional, for your own tracking)
   - Copy the key and store it securely (eg. in a password manage or `.env` file if using in code)
   > 🔐 **Note: You won't be able to view the full API key again, so make sure you copy it immediately.**
     
4. **Create a `.env` file in the root directory with the following content:**

    ```bash
    echo 'OPENAI_API_KEY="your_openai_key"
    API_ID="your_telegram_api_id"
    API_HASH="your_telegram_api_hash"
    PHONE="your_phone_number"
    USERNAME="your_telegram_username"
    STRING_SESSION="your_telegram_string_session"' > .env
    ```

    > 🔐 **Note:** Do **not** commit this file. It is excluded via `.gitignore`.
    > If you don't have credentials, contact us or register to obtain them.

5. **Install backend dependencies and run the backend server:**

    ```bash
    cd backend
    pip install -r requirements.txt  # Install Python dependencies
    python app.py                    # Launch the FastAPI server (http://127.0.0.1:5000)
    ```

6. **Open a new terminal/tab, activate the environment again, and run the frontend:**

    ```bash
    # In case you're not in project root
    cd dsa4265-investment-dashboard
    source venv/bin/activate           # Reactivate environment if needed
    cd frontend
    npm install                        # Install React dependencies
    npm start                          # Launch the React app (http://localhost:3000)
    ```

    > 📨 **Note:** On your first run, Telegram will send a login code to your Telegram app. Enter this code in the terminal when prompted.  
    > This process links your Telegram session and will only be required once. After that, news scraping will start automatically.

---

## 📁 Folder Structure

```bash
dsa4265-investment-dashboard/
├── backend/                   # FastAPI backend logic
│   ├── app.py                 # Main entry point for the backend server
│   ├── requirements.txt       # Python dependencies
│   └── utils/                 # Core logic for each analysis component
│       ├── stock_history.py           # Historical stock data + technical indicators
│       ├── esg_score.py               # ESG data analysis and scoring
│       ├── financial_metrics.py       # Financial health analysis
│       ├── media_analysis.py          # Telegram scraping + news summarisation
│       ├── holistic_summary.py        # Aggregated GPT recommendation
│       └── generate_string_session.py # Telegram login + session generation
├── frontend/                  # React frontend interface
│   ├── public/                # Static assets and index.html
│   ├── src/
│   │   └── components/        # React components for UI rendering
│   │       ├── Dashboard.js           # Dashboard layout and tabs
│   │       ├── StockHistory.js        # Stock history visualisation
│   │       ├── ESGScore.js            # ESG insights panel
│   │       ├── FinancialMetrics.js    # Financial metrics display
│   │       ├── MediaAnalysis.js       # News sentiment analysis
│   │       └── HolisticSummary.js     # Final AI-generated investment recommendation
│   ├── App.js                 # Root React app component
│   ├── index.js               # React app entry point
│   └── package.json           # React app dependencies
├── .env                       # API credentials (excluded from version control)
└── README.md                  # Project documentation
 ```
---

## 💻 Developers

This project is made possible with the efforts of everyone in the team:
| Name            | GitHub           |
|-----------------|------------------|
| Celeste Tan     | [celeste-tan](https://github.com/celeste-tan)    |
| Chua Yeong Hui    | [c0desnippet](https://github.com/c0desnippet)  |
| Joan, Wong Ya Sian  | [joanwys](https://github.com/joanwys)     |
| Lee Wen Yang   | [leewenyang](https://github.com/leewenyang) |
| Nicole Chong    | [nicolechongg](https://github.com/nicolechongg)  |
| Wan Yanbing   | [oneybb](https://github.com/oneybb)     |


## ⚠️ Disclaimer

This tool is intended for educational and informational purposes only. It does not constitute financial advice. Always consult a licensed financial advisor before making any investment decisions.

