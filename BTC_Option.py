# Copyright (c) 2025 Seyed Mohammad Hossein Fasihi (Mhmd Fasihi)
# This file is part of a project licensed under AGPLv3 or a commercial license.
# AGPLv3: https://www.gnu.org/licenses/agpl-3.0.html
# Contact for commercial licensing: mhmd.fasihi@gmail.com

"""
BTC_Option.py - FIXED VERSION
Bitcoin Options Data Collection with Corrected Time Calculations

CRITICAL FIXES:
- ✅ Fixed time-to-maturity calculation bug
- ✅ Added comprehensive error handling  
- ✅ Improved data validation
- ✅ Added proper logging
"""

import pandas as pd
import requests
import time
from datetime import datetime, date
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Union
import logging

# Import our fixed time utilities
from src.core.utils.time_utils import (
    calculate_time_to_maturity_vectorized,
    fix_legacy_time_calculation,
    validate_time_calculation
)

logger = logging.getLogger(__name__)

def datetime_to_timestamp(dt: Union[datetime, date]) -> int:
    """Convert datetime to millisecond timestamp."""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    return int(dt.timestamp() * 1000)

def timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert millisecond timestamp to datetime."""
    return datetime.fromtimestamp(timestamp / 1000)

def get_with_retries(session: requests.Session, url: str, params: dict, 
                    max_retries: int = 3, backoff_factor: float = 1.0) -> Optional[dict]:
    """Make HTTP request with retry logic."""
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Request attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                logger.error(f"All {max_retries} attempts failed")
                return None

class BTCOption:
    """Bitcoin Options Data Collection with Fixed Time Calculations."""
    
    def __init__(self, currency: str, start_date: date, end_date: date):
        """
        Initialize BTC Options data collector.
        
        Args:
            currency: Currency symbol (e.g., 'BTC')
            start_date: Start date for data collection
            end_date: End date for data collection
        """
        self.currency = currency
        self.start_date = start_date
        self.end_date = end_date

        # Validate input arguments
        assert isinstance(currency, str), "currency must be a string"
        assert isinstance(start_date, date), "start_date must be a date object"
        assert isinstance(end_date, date), "end_date must be a date object"
        assert start_date <= end_date, "start_date must be before or equal to end_date"
        
        logger.info(f"Initialized BTCOption collector for {currency} from {start_date} to {end_date}")

    def option_data(self) -> pd.DataFrame:
        """
        Retrieve and process option data from Deribit API with FIXED time calculations.
        
        Returns:
            DataFrame with properly calculated time-to-maturity values
        """
        logger.info(f"Starting options data collection for {self.currency}")
        
        option_list = []
        params = {
            "currency": self.currency,
            "kind": "option",
            "count": 1000,
            "include_old": True,
            "start_timestamp": datetime_to_timestamp(self.start_date),
            "end_timestamp": datetime_to_timestamp(self.end_date)
        }

        url = 'https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time'

        try:
            with requests.Session() as session:
                while True:
                    response_data = get_with_retries(session, url, params)
                    if not response_data or "result" not in response_data or "trades" not in response_data["result"]:
                        break

                    trades = response_data["result"]["trades"]
                    if len(trades) == 0:
                        break

                    option_list.extend(trades)
                    params["start_timestamp"] = trades[-1]["timestamp"] + 1

                    if params["start_timestamp"] >= datetime_to_timestamp(self.end_date):
                        break

                    time.sleep(0.2)  # Rate limiting

        except Exception as e:
            logger.error(f"Failed to collect options data: {e}")
            return pd.DataFrame()

        if not option_list:
            logger.warning("No options data collected")
            return pd.DataFrame()

        # Process the data
        logger.info(f"Processing {len(option_list)} option trades")
        option_data = pd.DataFrame(option_list)

        # Select and process required columns
        required_columns = ["timestamp", "price", "instrument_name", "index_price", "direction", "amount", "iv"]
        missing_columns = [col for col in required_columns if col not in option_data.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return pd.DataFrame()
            
        option_data = option_data[required_columns]

        try:
            # Extract information from instrument name with error handling
            option_data["kind"] = option_data["instrument_name"].apply(
                lambda x: self._safe_extract_kind(str(x))
            )
            option_data["maturity_date"] = option_data["instrument_name"].apply(
                lambda x: self._safe_extract_maturity(str(x))
            )
            option_data["strike_price"] = option_data["instrument_name"].apply(
                lambda x: self._safe_extract_strike(str(x))
            )
            option_data["option_type"] = option_data["instrument_name"].apply(
                lambda x: self._safe_extract_option_type(str(x))
            )

            # Drop rows where extraction failed
            option_data = option_data.dropna(subset=["maturity_date", "strike_price"])
            
            if option_data.empty:
                logger.warning("No valid options after parsing instrument names")
                return pd.DataFrame()

            # Calculate derived metrics
            option_data["moneyness"] = option_data["index_price"] / option_data["strike_price"]
            option_data["price"] = (option_data["price"] * option_data["index_price"]).round(2)
            option_data["date_time"] = option_data["timestamp"].apply(timestamp_to_datetime)
            
            # 🚨 CRITICAL FIX: Use proper time calculation instead of legacy bug
            # OLD BUG: option_data["time_to_maturity"] = option_data["time_to_maturity"].apply(
            #     lambda x: max(round(x.total_seconds() / 31536000, 3), 1e-4) * 365)
            
            # CORRECT: Use our fixed time calculation utilities
            option_data = fix_legacy_time_calculation(
                option_data,
                current_time_col='date_time',
                expiry_time_col='maturity_date',
                output_col='time_to_maturity'
            )
            
            # Convert IV to decimal
            option_data["iv"] = round(option_data["iv"] / 100, 3)

            # Filter for call options only
            call_options = option_data[option_data["option_type"] == "c"]
            
            if call_options.empty:
                logger.warning("No call options found after filtering")
                return pd.DataFrame()

            logger.info(f"✅ Successfully processed {len(call_options)} call options")
            
            # Validate a sample of time calculations
            self._validate_time_calculations(call_options.head())
            
            return call_options[['instrument_name', 'date_time', 'price',
                               'index_price', 'strike_price', 'moneyness',
                               'option_type', 'iv', 'time_to_maturity',
                               'maturity_date']]

        except Exception as e:
            logger.error(f"Failed to process options data: {e}")
            return pd.DataFrame()

    def _safe_extract_kind(self, instrument_name: str) -> Optional[str]:
        """Safely extract kind from instrument name."""
        try:
            return instrument_name.split("-")[0]
        except (IndexError, AttributeError):
            return None

    def _safe_extract_maturity(self, instrument_name: str) -> Optional[datetime]:
        """Safely extract maturity date from instrument name."""
        try:
            from datetime import datetime as dt
            return dt.strptime(instrument_name.split("-")[1], "%d%b%y")
        except (IndexError, ValueError, AttributeError):
            return None

    def _safe_extract_strike(self, instrument_name: str) -> Optional[float]:
        """Safely extract strike price from instrument name."""
        try:
            return float(instrument_name.split("-")[2])
        except (IndexError, ValueError, AttributeError):
            return None

    def _safe_extract_option_type(self, instrument_name: str) -> Optional[str]:
        """Safely extract option type from instrument name."""
        try:
            return instrument_name.split("-")[3].lower()
        except (IndexError, AttributeError):
            return None
            
    def _validate_time_calculations(self, sample_data: pd.DataFrame) -> None:
        """Validate time calculations on a sample of data."""
        try:
            for _, row in sample_data.iterrows():
                is_valid = validate_time_calculation(
                    row['time_to_maturity'],
                    row['date_time'],
                    row['maturity_date']
                )
                if not is_valid:
                    logger.warning(f"Time calculation validation failed for {row['instrument_name']}")
                    break
            else:
                logger.info("✅ Time calculation validation passed for sample data")
        except Exception as e:
            logger.error(f"Time calculation validation error: {e}")


def create_visualizations(call_option_data: pd.DataFrame) -> None:
    """Create visualizations for the option data analysis."""
    
    if call_option_data.empty:
        logger.warning("No data available for visualization")
        return
        
    logger.info(f"Creating visualizations for {len(call_option_data)} options")

    try:
        # 1. Price vs Strike Price Scatter Plot
        plt.figure(figsize=(14, 9))
        plt.scatter(call_option_data["strike_price"], call_option_data["price"],
                   alpha=0.6, c="blue")
        plt.title("Option Price vs. Strike Price", fontsize=14)
        plt.xlabel("Strike Price", fontsize=12)
        plt.ylabel("Option Price", fontsize=12)
        plt.grid(alpha=0.3)
        plt.show()

        # 2. Implied Volatility Distribution
        plt.figure(figsize=(14, 9))
        plt.hist(call_option_data["iv"], bins=30, color="green",
                 alpha=0.7, edgecolor="black")
        plt.title("Distribution of Implied Volatility (IV)", fontsize=14)
        plt.xlabel("Implied Volatility", fontsize=12)
        plt.ylabel("Frequency", fontsize=12)
        plt.grid(alpha=0.3)
        plt.show()

        # 3. Time to Maturity vs Implied Volatility
        plt.figure(figsize=(14, 9))
        plt.scatter(call_option_data["time_to_maturity"], call_option_data["iv"],
                   alpha=0.6, c="red")
        plt.title("Time to Maturity vs Implied Volatility", fontsize=14)
        plt.xlabel("Time to Maturity (Years)", fontsize=12)
        plt.ylabel("Implied Volatility", fontsize=12)
        plt.grid(alpha=0.3)
        plt.show()

        # 4. Option Price Over Time
        plt.figure(figsize=(14, 9))
        call_option_data_sorted = call_option_data.sort_values("date_time")
        plt.plot(call_option_data_sorted["date_time"],
                call_option_data_sorted["price"],
                label="Option Price", color="blue", alpha=0.7)
        plt.title("Option Price Over Time", fontsize=14)
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Option Price", fontsize=12)
        plt.grid(alpha=0.3)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

        # 5. Moneyness Distribution
        plt.figure(figsize=(14, 9))
        plt.hist(call_option_data["moneyness"], bins=30, color="purple",
                 alpha=0.7, edgecolor="black")
        plt.title("Distribution of Moneyness", fontsize=14)
        plt.xlabel("Moneyness (S/K)", fontsize=12)
        plt.ylabel("Frequency", fontsize=12)
        plt.axvline(x=1.0, color='red', linestyle='--', label='ATM')
        plt.grid(alpha=0.3)
        plt.legend()
        plt.show()

        logger.info("✅ All visualizations created successfully")

    except Exception as e:
        logger.error(f"Visualization creation failed: {e}")


# Example usage and testing
def main():
    """Main function to demonstrate fixed BTC options analysis."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the options collector
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 7)  # One week of data
    
    btc_option = BTCOption("BTC", start_date, end_date)
    
    # Collect and process options data with fixed time calculations
    print("🚀 Collecting BTC options data with FIXED time calculations...")
    options_df = btc_option.option_data()
    
    if not options_df.empty:
        print(f"✅ Successfully collected {len(options_df)} BTC call options")
        print("\n📊 Sample data:")
        print(options_df[['instrument_name', 'strike_price', 'price', 'iv', 'time_to_maturity']].head())
        
        # Verify time calculations are reasonable
        print(f"\n⏰ Time to maturity range: {options_df['time_to_maturity'].min():.4f} to {options_df['time_to_maturity'].max():.4f} years")
        
        # Create visualizations
        create_visualizations(options_df)
        
    else:
        print("❌ No options data collected")


if __name__ == "__main__":
    main()
