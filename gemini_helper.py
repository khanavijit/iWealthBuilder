from Constants import GEMINI_API_KEY, GEMINI_API_URL
import requests
from typing import Dict, Any
import json
import time


def get_gemini_suggestion(profile_name: str, portfolio_data: Dict[str, Any]) -> str:
    """Fetches an AI-generated investment suggestion from the Gemini API."""

    if not GEMINI_API_KEY:
        return "⚠️ **ERROR:** Gemini API key is not configured. Please set `GEMINI_API_KEY` in the application file to enable AI features."

    # 1. Prepare data for AI
    summary_data = portfolio_data.get('portfolio_summary', {})
    performance_list = portfolio_data.get('performance_list', [])

    # Format portfolio summary as a simple string for the LLM
    portfolio_summary_text = (
        f"Total Invested: {summary_data.get('total_invested_capital', 0.0):.2f} | "
        f"Total Market Value: {summary_data.get('total_market_value', 0.0):.2f} | "
        f"Net P&L: {summary_data.get('net_profit_loss', 0.0):.2f}\n\n"
        "Individual Asset Performance:\n"
    )
    for asset in performance_list:
        portfolio_summary_text += (
            f"- {asset['investment_name']} (Category: {asset['asset_category']}, SIP: {asset['sip_frequency']}): "
            f"CMV={asset['current_market_value']:.2f}, "
            f"Invested={asset['total_invested_capital']:.2f}, "
            f"Unrealized P&L={asset['unrealized_pnl']:.2f}\n"
        )

    # 2. Define AI persona and prompt
    system_prompt = (
        "You are 'iWealthAI', a sophisticated, friendly, and objective financial advisor. "
        "Your task is to analyze the provided user investment portfolio data, compare it "
        f"against the recommended '{profile_name}' risk profile, and provide actionable, "
        "easy-to-understand investment suggestions in three sections:\n"
        "1. **Analysis Summary:** A brief summary of the user's current allocation health, noting any major category imbalances.\n"
        "2. **Actionable Suggestions:** Specific, concrete actions (e.g., 'Increase SIP for Quant Small Cap Fund by 10%', 'Hold on Reliance Stock', 'Consider booking profit in X').\n"
        "3. **Next Steps:** General advice on market trends relevant to their holdings (e.g., small cap outlook, fixed income strategy) using Google Search grounding.\n"
        "Format the response using bold headers for the sections and clear, conversational language. Do not repeat the input data or allocation percentages in the final output."
    )

    user_query = (
        f"The user wants advice based on their selected risk profile: '{profile_name}'.\n"
        f"The user's current portfolio data is:\n---\n{portfolio_summary_text}\n---\n"
        f"The target allocation profile is for {profile_name}.\n"
        f"Please provide an analysis and suggestions based on this data."
    )

    # 3. Build API Payload
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "tools": [{"google_search": {}}],  # Enable grounding for market trend advice
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    headers = {
        'Content-Type': 'application/json',
    }

    # 4. Make the API Call with Retry Logic (Simple backoff)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()

            result = response.json()
            generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

            if generated_text:
                return generated_text
            else:
                return f"⚠️ **API Error:** Gemini returned an empty response or an error. Check the response body: {result}"

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                return f"❌ **Request Failed:** Could not get a response from the Gemini API after {max_retries} attempts. Error: {e}"

    return "❌ **API Error:** Unknown communication error."
