import streamlit as st
import requests
from typing import Dict, Any, Optional, List
import json

# Ensure this matches your FastAPI server address
API_BASE_URL = "http://localhost:8000"


# --- Backend API Helper Functions ---

@st.cache_data(ttl=3600)
def fetch_portfolio_summary() -> Optional[Dict[str, Any]]:
    """
    Fetches the complete portfolio summary. This endpoint now returns
    fully enriched investment data, so no local joining is needed.
    """
    try:
        url = f"{API_BASE_URL}/investments/portfolio_summary/"
        summary_response = requests.get(url)
        summary_response.raise_for_status()
        return summary_response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching portfolio summary from {url}: {e}")
        return None


@st.cache_data(ttl=3600)
def fetch_user_investments() -> List[Dict[str, Any]]:
    """
    Fetches the list of all investments the user holds, with
    their full catalog details. Used for SIP management and forms.
    """
    try:
        url = f"{API_BASE_URL}/investments/"
        inv_list_response = requests.get(url)
        inv_list_response.raise_for_status()
        return inv_list_response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching user investment list from {url}: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_catalog() -> List[Dict[str, Any]]:
    """
    Fetches the complete investment catalog.
    Used for the 'Add New Asset' dropdown.
    """
    try:
        url = f"{API_BASE_URL}/catalog/"
        catalog_response = requests.get(url)
        catalog_response.raise_for_status()
        return catalog_response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching investment catalog from {url}: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_api_exclusions():
    """Fetch the blacklist from CockroachDB via FastAPI."""
    response = requests.get(f"{API_BASE_URL}/catalog/exclusions")
    return response.json() if response.status_code == 200 else []


def get_excluded_list(item_type: str) -> List[str]:
    """Helper to retrieve blacklisted items by type from SQLite."""
    # exclusions = get_all_exclusions()
    exclusions = fetch_api_exclusions()
    # exclusions format: [(id, type, value), ...]
    # return [val for _, t, val in exclusions if t == item_type]
    return [
        item["exclusion_value"]
        for item in exclusions
        if item.get("exclusion_type") == item_type
    ]


@st.cache_data(ttl=3600)  # Cache market data for 1 hour (less frequent changes)
def fetch_index_categories() -> List[str]:
    """Fetch unique index categories from the FastAPI catalog router."""
    try:
        url = f"{API_BASE_URL}/catalog/indices/categories"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        all_categories = response.json()
        # 2. Get Exclusions
        excluded = get_excluded_list("Category")
        # 3. Filter
        filtered = [c for c in all_categories if c not in excluded]
        # 4. Priority Sort
        priority = "INDICES ELIGIBLE IN DERIVATIVES"
        return sorted(filtered, key=lambda x: (x != priority, x))
    except Exception as e:
        st.error(f"Failed to fetch categories: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_indices_by_category(category: str) -> List[Dict[str, Any]]:
    """Fetch indices belonging to a specific category."""
    try:
        # category is passed as a path parameter
        url = f"{API_BASE_URL}/catalog/indices/by-category/{category}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        all_indices = response.json()
        excluded = get_excluded_list("Index")
        return [c for c in all_indices if c['index_name'] not in excluded]
    except Exception as e:
        st.error(f"Failed to fetch indices for {category}: {e}")
        return []


def make_api_post(url: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generic POST request function with error handling."""
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"API Error ({response.status_code}): {e}")
        try:
            st.json(response.json())  # Try to show the error detail from the API
        except json.JSONDecodeError:
            st.error(f"Raw error response: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network Error: Could not post data to {url}. {e}")
        return None


def add_catalog_item(asset_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Creates a new investment in the main catalog."""
    url = f"{API_BASE_URL}/catalog/"
    return make_api_post(url, asset_data)


def add_user_holding(holding_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Adds an investment from the catalog to the user's portfolio."""
    url = f"{API_BASE_URL}/investments/"
    return make_api_post(url, holding_data)


def add_new_transaction(investment_id: int, transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Logs a new transaction for one of the user's investments."""
    url = f"{API_BASE_URL}/investments/{investment_id}/transactions"
    return make_api_post(url, transaction_data)


def add_new_valuation(investment_id: int, valuation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Logs a new valuation (price update) for one of the user's investments."""
    url = f"{API_BASE_URL}/investments/{investment_id}/valuation"
    return make_api_post(url, valuation_data)


@st.cache_data(ttl=3600)
def fetch_stocks_by_index(index_symbol: str) -> List[Dict[str, Any]]:
    """Fetch constituent stocks for a specific index symbol."""
    try:
        # index_symbol is passed as a path parameter
        url = f"{API_BASE_URL}/catalog/stocks/by-index/{index_symbol}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        all_stocks = response.json()
        excluded = get_excluded_list("Stock")
        # print(excluded)
        # print(all_stocks)
        return [c for c in all_stocks if c['symbol'] not in excluded]
    except Exception as e:
        st.error(f"Failed to fetch stocks for {index_symbol}: {e}")
        return []


def search_catalog_items(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches catalog items matching the query using the search endpoint.
    Uses the required URL structure: http://127.0.0.1:8000/catalog/search?q=<INPUT>
    """
    try:
        # Calls the backend API's search endpoint using the defined base URL
        # API_BASE_URL = "http://127.0.0.1:8000"
        response = requests.get(f"{API_BASE_URL}/catalog/search?q={query}")
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API for search or search failed: {e}")
        st.error(f"Catalog search failed: Connection error or API error. Details: {e}")
        # Return empty list on failure so the Streamlit app can handle it gracefully
        return []


def add_api_exclusion(item_type: str, item_value: str):
    """
    Sends a POST request to FastAPI to add a new exclusion
    to the CockroachDB blacklist.
    """
    try:
        payload = {"type": item_type, "value": item_value}
        response = requests.post(f"{API_BASE_URL}/catalog/exclusions", params=payload)
        response.raise_for_status()
        # Clear cache so the UI updates immediately
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to add exclusion: {e}")
        return False


def remove_api_exclusion(item_type: str, item_value: str):
    """
    Sends a DELETE request to FastAPI to remove an item
    from the CockroachDB blacklist.
    """
    try:
        url = f"{API_BASE_URL}/catalog/exclusions/{item_type}/{item_value}"
        response = requests.delete(url)
        response.raise_for_status()
        # Clear cache so the UI updates immediately
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to remove exclusion: {e}")
        return False


@st.cache_data(ttl=3600)
def fetch_api_exclusions() -> List[Dict[str, Any]]:
    """
    Fetches the current blacklist from CockroachDB.
    Returns a list of dicts: [{'exclusion_type': '...', 'exclusion_value': '...'}, ...]
    """
    try:
        response = requests.get(f"{API_BASE_URL}/catalog/exclusions", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch exclusions: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_scoring_config() -> Dict[str, Any]:
    """
    Fetches the hierarchical scoring JSON from CockroachDB.
    Key used in DB: 'scoring_weights'
    """
    try:
        url = f"{API_BASE_URL}/primeScore/config/scoring_weights"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching configuration: {e}")
        return {}


def save_scoring_config(config_dict: Dict[str, Any]) -> bool:
    """
    Sends the entire updated JSON back to FastAPI to be UPSERTED
    into the financial_scorer_config table.
    """
    try:
        url = f"{API_BASE_URL}/primeScore/config/scoring_weights"
        response = requests.post(url, json=config_dict, timeout=5)
        response.raise_for_status()

        # Clear local Streamlit cache so changes reflect immediately
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save configuration: {e}")
        return False


@st.cache_data(ttl=3600)
def fetch_prime_score(symbol: str) -> Dict[str, Any]:
    """
    Fetches the hierarchical scoring JSON from CockroachDB.
    Key used in DB: 'scoring_weights'
    """
    try:

        url = f"{API_BASE_URL}/primeScore/report/{symbol}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching configuration: {e}")
        return {}


@st.cache_data(ttl=3600)
def fetch_ai_score_an_analysis(symbol: str) -> Dict[str, Any]:
    """
    Fetches the hierarchical scoring JSON from CockroachDB.
    Key used in DB: 'scoring_weights'
    """
    try:

        url = f"{API_BASE_URL}/primeScore/update-sentiment/{symbol}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching configuration: {e}")
        return {}


@st.cache_data(ttl=3600)
def fetch_get_stock_full_analysis(index_symbol: str) -> Dict[str, Any]:
    """
    Fetches the hierarchical scoring JSON from CockroachDB.
    Key used in DB: 'scoring_weights'
    """
    try:

        url = f"{API_BASE_URL}/catalog/stocks/full-analysis/{index_symbol}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching configuration: {e}")
        return {}


# @st.cache_data(ttl=300)  # 5-minute cache for live portfolio data
def fetch_open_signals() -> List[Dict[str, Any]]:
    """
    Fetches all enriched open signals (Portfolio View) from the API.
    Includes CMP, Industry, Financial Score, and Unrealized PnL.
    """
    try:
        url = f"{API_BASE_URL}/catalog/stocks/signals/open"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # Returning the 'data' list from your FastAPI response structure
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"📡 Error fetching open signals: {e}")
        return []


def post_new_signal(signal_payload: Dict[str, Any]) -> bool:
    """
    Invoked by the scanner to push a new Minervini Buy Signal to the DB.
    """
    try:
        url = f"{API_BASE_URL}/catalog/stocks/signals"
        response = requests.post(url, json=signal_payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            st.warning(f"⚠️ Failed to push signal: {response.text}")
            return False
    except Exception as e:
        st.error(f"❌ Connection error during signal push: {e}")
        return False
