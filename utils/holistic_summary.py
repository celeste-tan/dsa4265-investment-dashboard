def get_holistic_recommendation(ticker, stock_rec, esg_rec="", fin_rec="", news_rec=""):
    """
    For now, this function only uses the stock history recommendation.
    In the future, it will combine ESG, financial, and news analyses as well.
    """
    holistic_report = (
        f"Holistic Recommendation for {ticker}:\n\n"
        f"Technical Analysis (Stock History):\n{stock_rec}\n\n"
        f"ESG Analysis: {esg_rec}\n"
        f"Financial Analysis: {fin_rec}\n"
        f"News Analysis: {news_rec}\n"
        "Final Decision: Based on the technical analysis, a recommendation has been provided."
    )
    return holistic_report
