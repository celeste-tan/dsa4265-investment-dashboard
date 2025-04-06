from crawlbase import CrawlingAPI
from bs4 import BeautifulSoup
import openai
# import json

def fetch_esg_data(ticker, api_token):
    """Fetch ESG scores from Yahoo Finance for a given stock ticker."""
    page_url = f'https://finance.yahoo.com/quote/{ticker}/sustainability/'
    
    try:
        api = CrawlingAPI({'token': api_token})
        response = api.get(page_url)
        print("page received")

        if response['status_code'] != 200:
            return {"error": f"Failed to fetch ESG data for {ticker}"}

        page_content = response["body"].decode("utf-8")
        soup = BeautifulSoup(page_content, "html.parser")

        esg_data = {"Stock": ticker}
        scores = {
            "Total ESG Risk Score": "TOTAL_ESG_SCORE",
            "Environmental Risk Score": "ENVIRONMENTAL_SCORE",
            "Social Risk Score": "SOCIAL_SCORE",
            "Governance Risk Score": "GOVERNANCE_SCORE"
        }

        for key, test_id in scores.items():
            section = soup.find("section", {"data-testid": test_id})
            if section:
                score_tag = section.find("h4")
                if score_tag:
                    esg_data[key] = float(score_tag.text.strip())

        # Extract Controversy Level
        controversy_section = soup.find("section", {"data-testid": "esg-controversy"})
        if controversy_section:
            val_div = controversy_section.find("div", class_="val yf-ye6fz0")
            if val_div:
                spans = val_div.find_all("span", class_="yf-ye6fz0")
                if len(spans) >= 2:
                    esg_data["Controversy Level"] = {
                        "Value": int(spans[0].text.strip()),
                        "Description": spans[2].text.strip()
                    }
        print("scraped")
        return esg_data

    except Exception as e:
        return {"error": f"Error fetching ESG data for {ticker}: {e}"}

def generate_esg_assessment(esg_data, openai_api_key):
    """Generate an ESG assessment based on extracted ESG scores using OpenAI."""
    if "error" in esg_data:
        return esg_data["error"]

    prompt = (
        f"ESG Analysis for {esg_data['Stock']}:\n"
        f"Total ESG Risk Score: {esg_data.get('Total ESG Risk Score', 'N/A')}\n"
        f"Environmental Risk Score: {esg_data.get('Environmental Risk Score', 'N/A')}\n"
        f"Social Risk Score: {esg_data.get('Social Risk Score', 'N/A')}\n"
        f"Governance Risk Score: {esg_data.get('Governance Risk Score', 'N/A')}\n"
        f"Controversy Level: {esg_data.get('Controversy Level', {}).get('Value', 'N/A')} "
        f"({esg_data.get('Controversy Level', {}).get('Description', 'N/A')})\n\n"
        "Based on the ESG risk scores and controversy level, provide an assessment of the company's sustainability and potential risks. Limit the output to 250 words."
    )

    try:
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an ESG investment analyst."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating ESG assessment: {e}"

def get_esg_report(ticker, api_token, openai_api_key):
    """Retrieve ESG scores and generate an AI-based ESG assessment for a given ticker."""
    esg_data = fetch_esg_data(ticker, api_token)
    esg_assessment = generate_esg_assessment(esg_data, openai_api_key)
    return esg_assessment
