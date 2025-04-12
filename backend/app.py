import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import asyncio
from dotenv import load_dotenv
from config import Config
from extensions import db
from models import FinancialMetric, NewsArticle
from database import InvestmentDB
from utils import (
    esg_analysis,
    stock_history,
    media_sentiment_analysis,
    financial_summary,
    holistic_summary
)
from utils.holistic_summary import get_holistic_recommendation
from utils.esg_analysis import get_esg_report, fetch_esg_data
from utils.stock_history import get_stock_recommendation, fetch_stock_data
from utils.media_sentiment_analysis import get_stock_summary
from utils.financial_summary import (
    get_full_quarterly_data,
    generate_financial_summary,
    generate_ai_investment_commentary,
    filter_financial_data_by_period 
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    investment_db = InvestmentDB(app)
    
    # Register routes
    register_routes(app)
    
    return app

def register_routes(app):
    @app.route("/api/esg-scores", methods=["POST"])
    def get_esg_scores():
        """Endpoint 1: Get raw ESG scores with database caching"""
        data = request.json
        ticker = data.get("ticker", "").upper()

        if not ticker:
            return jsonify({"error": "Missing ticker symbol"}), 400
        
        try:
            # Check cache first (valid for 7 days)
            latest_date = db.session.query(
                db.func.max(FinancialMetric.date)
            ).filter_by(ticker=ticker).scalar()
            
            if latest_date and (datetime.now().date() - latest_date).days < 7:
                metric = FinancialMetric.query.filter_by(
                    ticker=ticker,
                    date=latest_date
                ).first()
                
                if metric:
                    return jsonify({
                        "esg_scores": {
                            "Total": metric.esg_risk_score,
                            "Environmental": metric.environmental_score,
                            "Social": metric.social_score,
                            "Governance": metric.governance_score,
                            "Controversy": {
                                "Value": metric.controversy_value,
                                "Description": metric.controversy_description
                            }
                        }
                    }), 200

            # Fetch fresh ESG data
            esg_data = fetch_esg_data(ticker)
        
            if "error" in esg_data:
                return jsonify({"error": esg_data["error"]}), 400
            
            # Store in database
            db.session.add(FinancialMetric(
                ticker=ticker,
                date=datetime.now().date(),
                esg_risk_score=esg_data.get("Total"),
                environmental_score=esg_data.get("Environmental"),
                social_score=esg_data.get("Social"),
                governance_score=esg_data.get("Governance"),
                controversy_value=esg_data.get("Controversy", {}).get("Value"),
                controversy_description=esg_data.get("Controversy", {}).get("Description")
            ))
            db.session.commit()
            
            return jsonify({"esg_scores": esg_data}), 200
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"ESG scores error: {str(e)}")
            return jsonify({
                "error": "Failed to get ESG scores",
                "details": str(e) if app.config['DEBUG'] else None
            }), 500

    @app.route("/api/esg-gen-report", methods=["POST"])
    def generate_esg_report():
        """Endpoint 2: Generate AI analysis of ESG scores"""
        data = request.json
        ticker = data.get("ticker", "").upper()

        if not ticker:
            return jsonify({"error": "Missing ticker symbol"}), 400

        # First get scores
        esg_response, status_code = get_esg_scores()
        if status_code != 200:
            return esg_response, status_code
        
        esg_data = esg_response.get_json()["esg_scores"]
        
        # Generate AI report
        report = esg_analysis.generate_esg_assessment(
            {
                "Stock": ticker,
                "Total ESG Risk Score": esg_data.get("Total", "N/A"),
                "Environmental Risk Score": esg_data.get("Environmental", "N/A"),
                "Social Risk Score": esg_data.get("Social", "N/A"),
                "Governance Risk Score": esg_data.get("Governance", "N/A"),
                "Controversy Level": esg_data.get("Controversy", "N/A")
            },
            app.config['OPENAI_API_KEY']
        )
        
        return jsonify({"report": report}), 200

    @app.route("/api/stock-chart", methods=["POST"])
    def stock_chart():
        """Endpoint 3: Get historical price data with caching"""
        data = request.json
        ticker = data.get("ticker")
        period = data.get("period", "1y")
        logger.info(f"stock_chart: {ticker} {period}")

        if not ticker:
            return jsonify({"error": "Ticker is required"}), 400

        try:
            # Determine date range
            end_date = datetime.now().strftime('%Y-%m-%d')
            if period == "1d":
                start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            elif period == "5d":
                start_date = (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d')
            elif period == "1mo":
                start_date = (datetime.now() - timedelta(weeks=4)).strftime('%Y-%m-%d')
            elif period == "1y":
                start_date = (datetime.now() - timedelta(weeks=52)).strftime('%Y-%m-%d')
            else:
                start_date = (datetime.now() - timedelta(weeks=52)).strftime('%Y-%m-%d')

            # Fetch fresh data
            logger.info(f"Getting fresh stock prices for {ticker} ({period}) from {start_date} to {end_date}...")
            df = stock_history.fetch_stock_data(ticker, period, start_date, end_date)
            prices = []
            for index, row in df.iterrows():
                date_str = index.strftime('%Y-%m-%d')
                prices.append({
                    "date": date_str,
                    "close": round(row["Close"], 2)
                })
                
            if prices:
                logger.info(f"Data for ticker {ticker}: {prices[0]}, {prices[-1]}")
            return jsonify({"prices": prices})
        except Exception as e:
            logger.error(f"Stock chart error: {str(e)}")
            return jsonify({
                "error": "Failed to get stock data",
                "details": str(e) if app.config['DEBUG'] else None
            }), 500

    @app.route("/api/stock-history", methods=["POST"])
    def get_stock_history():
        """Endpoint 4: Get AI-generated stock recommendation"""
        data = request.json
        ticker = data.get("ticker")
        timeframe = data.get("timeframe", "short-term")

        if not ticker:
            return jsonify({"error": "Missing ticker"}), 400

        recommendation, _ = get_stock_recommendation(ticker, timeframe, os.getenv("OPENAI_API_KEY", ""))
        return jsonify({"recommendation": recommendation})

    @app.route("/api/financial-chart", methods=["POST"])
    def financial_chart():
        data = request.json
        ticker = data.get("ticker", "").upper()
        period = data.get("period", "1y")

        if not ticker:
            return jsonify({"error": "Missing ticker symbol"}), 400

        try:
            df_all = get_full_quarterly_data(ticker)
            df = filter_financial_data_by_period(df_all, period)

            # Drop rows with any NaN values
            logger.info(f"Original rows: {len(df)}")
            df = df.dropna()
            logger.info(f"Cleaned rows: {len(df)}")

            chart_data = []
            for _, row in df.iterrows():
                chart_data.append({
                    "quarter": row["Quarter"],
                    "revenue": row["Revenue"],
                    "net_income": row["Net Income"],
                    "free_cash_flow": row["Free Cash Flow"]
                })

            return jsonify({"data": chart_data})
        except Exception as e:
            logger.error(f"Financial chart error for {ticker}: {str(e)}")
            return jsonify({
                "error": "Failed to get financial data",
                "details": str(e) if app.config['DEBUG'] else None
            }), 500

    @app.route("/api/financial-recommendation", methods=["POST"])
    def financial_recommendation():
        data = request.json
        ticker = data.get("ticker", "").upper()
        if not ticker:
            return jsonify({"error": "Missing ticker symbol"}), 400

        try:
            df = get_full_quarterly_data(ticker)
            summary = generate_financial_summary(df, ticker)
            commentary = generate_ai_investment_commentary(summary, os.getenv("OPENAI_API_KEY"))
            return jsonify({
                "summary": summary,
                "commentary": commentary
            })
        except Exception as e:
            logger.error(f"Financial recommendation failed for {ticker}: {str(e)}")
            return jsonify({
                "error": "Failed to generate financial analysis",
                "details": str(e) if app.config['DEBUG'] else None
            }), 500

    @app.route("/api/media-sentiment-summary", methods=["POST"])
    def get_media_sentiment():
        """Endpoint 5: Get news sentiment analysis with caching"""
        data = request.json
        ticker = data.get("ticker", "").upper()

        if not ticker:
            return jsonify({"error": "Missing ticker"}), 400

        try:
            # Check for cached news (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            news_articles = NewsArticle.query.filter(
                NewsArticle.ticker == ticker,
                NewsArticle.published_date >= cutoff_date
            ).all()
            
            logger.info(f"Found {len(news_articles)} cached news articles")
            
            if not news_articles:
                # Scrape fresh news if none in cache
                try:
                    news_articles = asyncio.run(
                        media_sentiment_analysis.scrape_telegram_headlines()
                    )
                except Exception as scrape_error:
                    logger.error(f"Failed to scrape Telegram headlines: {str(scrape_error)}")
                    return jsonify({
                        "error": "Failed to fetch news articles",
                        "details": str(scrape_error)
                    }), 500

                # Store new articles
                successful_inserts = 0
                for article in news_articles:
                    try:
                        db.session.add(NewsArticle(
                            ticker=ticker,
                            title=article.get('title'),
                            source="Telegram",
                            url=article.get('url'),
                            published_date=datetime.strptime(article.get('date'), '%Y-%m-%d').date(),
                            content=article.get('content'),
                            sentiment_score=None
                        ))
                        successful_inserts += 1
                    except Exception as insert_error:
                        db.session.rollback()
                        logger.error(f"Failed to insert article {article.get('url')}: {str(insert_error)}")
                        continue
                
                if successful_inserts > 0:
                    db.session.commit()
                
                if successful_inserts == 0:
                    return jsonify({
                        "error": "Failed to store any news articles",
                        "details": "Database insertion failed for all articles"
                    }), 500

            # Generate summary
            try:
                summary = asyncio.run(
                    get_stock_summary(
                        ticker,
                        app.config['OPENAI_API_KEY']
                    )
                )
                return jsonify({"summary": summary})
                
            except Exception as analysis_error:
                logger.error(f"Sentiment analysis failed: {str(analysis_error)}")
                return jsonify({
                    "error": "Failed to generate sentiment analysis",
                    "details": str(analysis_error)
                }), 500

        except Exception as e:
            logger.error(f"Unexpected error in media sentiment endpoint: {str(e)}")
            return jsonify({
                "error": "Internal server error",
                "details": str(e) if app.config['DEBUG'] else None
            }), 500
    
    @app.route("/api/holistic-summary", methods=["POST"])
    def holistic_summary():
        data = request.json
        ticker = data.get("ticker", "").upper()
        timeframe = data.get("timeframe", "short-term")

        if not ticker:
            return jsonify({"error": "Missing ticker symbol"}), 400

        try:
            summary = asyncio.run(get_holistic_recommendation(ticker, timeframe))
            return jsonify({"summary": summary})
        except Exception as e:
            logger.error(f"Holistic summary failed for {ticker}: {str(e)}")
            return jsonify({
                "error": "Failed to generate holistic analysis",
                "details": str(e) if app.config['DEBUG'] else None
            }), 500

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)