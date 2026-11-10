"""
Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments
Module: Currency Conversion & Live Exchange Rate Service

Features:
- Live exchange rate integration with external API (ExchangeRate-API)
- Support for API key configuration via EXCHANGE_RATE_API_KEY environment variable
- Fallback-free authentic API access via open endpoints (open.er-api.com)
- TTL-based memory caching with thread safety
- Precise financial calculations using Python's Decimal (avoiding floating point errors)
- Support for common global trading currencies: INR, USD, EUR, GBP, SGD, AED, AUD, CAD, JPY
- Custom decimal precision per currency (e.g., JPY has 0 decimals, others have 2)
- Normalization to reference USD currency for Machine Learning risk assessment
- Strict error handling: invalid amounts, unsupported currencies, API timeouts/failures
"""

import os
import time
import threading
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Any, Optional, Tuple
import requests

# -------------------------------------------------------------------------
# Supported Currencies Metadata
# -------------------------------------------------------------------------
SUPPORTED_CURRENCIES: Dict[str, Dict[str, Any]] = {
    "USD": {
        "code": "USD",
        "name": "US Dollar",
        "symbol": "$",
        "decimals": 2,
        "flag": "🇺🇸",
        "default_country": "United States"
    },
    "EUR": {
        "code": "EUR",
        "name": "Euro",
        "symbol": "€",
        "decimals": 2,
        "flag": "🇪🇺",
        "default_country": "Germany"
    },
    "GBP": {
        "code": "GBP",
        "name": "British Pound",
        "symbol": "£",
        "decimals": 2,
        "flag": "🇬🇧",
        "default_country": "United Kingdom"
    },
    "INR": {
        "code": "INR",
        "name": "Indian Rupee",
        "symbol": "₹",
        "decimals": 2,
        "flag": "🇮🇳",
        "default_country": "India"
    },
    "SGD": {
        "code": "SGD",
        "name": "Singapore Dollar",
        "symbol": "S$",
        "decimals": 2,
        "flag": "🇸🇬",
        "default_country": "Singapore"
    },
    "AED": {
        "code": "AED",
        "name": "UAE Dirham",
        "symbol": "AED",
        "decimals": 2,
        "flag": "🇦🇪",
        "default_country": "United Arab Emirates"
    },
    "AUD": {
        "code": "AUD",
        "name": "Australian Dollar",
        "symbol": "A$",
        "decimals": 2,
        "flag": "🇦🇺",
        "default_country": "Australia"
    },
    "CAD": {
        "code": "CAD",
        "name": "Canadian Dollar",
        "symbol": "C$",
        "decimals": 2,
        "flag": "🇨🇦",
        "default_country": "Canada"
    },
    "JPY": {
        "code": "JPY",
        "name": "Japanese Yen",
        "symbol": "¥",
        "decimals": 0,
        "flag": "🇯🇵",
        "default_country": "Japan"
    }
}

COUNTRY_TO_DEFAULT_CURRENCY = {
    "United States": "USD",
    "United Kingdom": "GBP",
    "Germany": "EUR",
    "France": "EUR",
    "Singapore": "SGD",
    "Japan": "JPY",
    "India": "INR",
    "United Arab Emirates": "AED",
    "Australia": "AUD",
    "Canada": "CAD",
    "Brazil": "USD",
    "Nigeria": "USD",
    "South Africa": "USD",
    "Mexico": "USD",
    "Russia": "USD",
    "Pakistan": "USD"
}

# -------------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------------
class CurrencyConversionError(Exception):
    """Base exception for currency conversion errors."""
    pass

class UnsupportedCurrencyError(CurrencyConversionError):
    """Raised when an unsupported currency is requested."""
    pass

class InvalidAmountError(CurrencyConversionError):
    """Raised when the transaction amount is invalid or <= 0."""
    pass

class ExchangeRateAPIError(CurrencyConversionError):
    """Raised when the exchange rate API request fails or is unavailable."""
    pass


# -------------------------------------------------------------------------
# Exchange Rate Service Implementation
# -------------------------------------------------------------------------
class CurrencyService:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
        
    @property
    def api_key(self) -> Optional[str]:
        return os.environ.get("EXCHANGE_RATE_API_KEY", "").strip() or None

    @property
    def custom_api_url(self) -> Optional[str]:
        return os.environ.get("EXCHANGE_RATE_API_URL", "").strip() or None

    @property
    def cache_ttl_seconds(self) -> int:
        try:
            return int(os.environ.get("EXCHANGE_RATE_CACHE_TTL", "3600"))
        except ValueError:
            return 3600

    @property
    def request_timeout(self) -> float:
        try:
            return float(os.environ.get("EXCHANGE_RATE_TIMEOUT", "8.0"))
        except ValueError:
            return 8.0

    @property
    def provider_name(self) -> str:
        return os.environ.get("EXCHANGE_RATE_PROVIDER", "ExchangeRate-API").strip()

    def get_supported_currencies(self) -> Dict[str, Dict[str, Any]]:
        """Return the dictionary of supported currencies."""
        return SUPPORTED_CURRENCIES

    def validate_currency(self, currency_code: str) -> str:
        """Validate and return normalized uppercase currency code."""
        if not currency_code or not isinstance(currency_code, str):
            raise UnsupportedCurrencyError(f"Currency code must be a non-empty string, got: {currency_code!r}")
        code = currency_code.strip().upper()
        if code not in SUPPORTED_CURRENCIES:
            supported = ", ".join(SUPPORTED_CURRENCIES.keys())
            raise UnsupportedCurrencyError(
                f"Currency '{code}' is not supported. Supported currencies are: {supported}"
            )
        return code

    def parse_amount(self, amount: Any) -> Decimal:
        """Safely parse input amount into positive Decimal."""
        if amount is None:
            raise InvalidAmountError("Transaction amount cannot be empty.")
        try:
            # Handle string or numeric input
            str_amt = str(amount).strip().replace(",", "")
            dec_amt = Decimal(str_amt)
        except (InvalidOperation, ValueError, TypeError):
            raise InvalidAmountError(f"Invalid transaction amount: '{amount}'. Must be a valid numerical value.")

        if dec_amt <= Decimal("0"):
            raise InvalidAmountError("Transaction amount must be strictly greater than 0.")
        return dec_amt

    def quantize_amount(self, amount: Decimal, currency_code: str) -> Decimal:
        """Quantize amount using currency-specific decimal precision and ROUND_HALF_UP."""
        code = self.validate_currency(currency_code)
        decimals = SUPPORTED_CURRENCIES[code]["decimals"]
        if decimals == 0:
            return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        unit = Decimal("10") ** -decimals
        return amount.quantize(unit, rounding=ROUND_HALF_UP)

    def format_amount(self, amount: Decimal, currency_code: str) -> str:
        """Format Decimal amount with currency symbol and appropriate decimal places."""
        code = self.validate_currency(currency_code)
        meta = SUPPORTED_CURRENCIES[code]
        symbol = meta["symbol"]
        decimals = meta["decimals"]
        quantized = self.quantize_amount(amount, code)
        if decimals == 0:
            return f"{symbol}{int(quantized):,}"
        return f"{symbol}{quantized:,.{decimals}f}"

    def _build_api_url(self, base_currency: str) -> str:
        """Build the appropriate API endpoint URL based on environment configuration."""
        if self.custom_api_url:
            return self.custom_api_url.format(
                base=base_currency,
                api_key=self.api_key or ""
            )
        if self.api_key:
            return f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest/{base_currency}"
        # Standard open public endpoint for ExchangeRate-API (no key required)
        return f"https://open.er-api.com/v6/latest/{base_currency}"

    def fetch_rates_from_api(self, base_currency: str) -> Dict[str, Any]:
        """
        Fetch real-time rates from external API.
        Never returns hardcoded or invented rates.
        Raises ExchangeRateAPIError on timeout, network failure, or bad response.
        """
        base = self.validate_currency(base_currency)
        url = self._build_api_url(base)

        headers = {
            "User-Agent": "CrossPay-SME-RiskAdaptiveSettlement/1.0",
            "Accept": "application/json"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=self.request_timeout)
        except requests.exceptions.Timeout:
            raise ExchangeRateAPIError(
                f"Exchange rate API connection timed out ({self.request_timeout}s) while fetching rates for {base}."
            )
        except requests.exceptions.RequestException as e:
            raise ExchangeRateAPIError(
                f"Network error while connecting to Exchange Rate API: {str(e)}"
            )

        if resp.status_code != 200:
            raise ExchangeRateAPIError(
                f"Exchange rate API returned HTTP {resp.status_code}: {resp.text[:120]}"
            )

        try:
            data = resp.json()
        except Exception:
            raise ExchangeRateAPIError("Exchange rate API returned an invalid non-JSON response.")

        # Check API status
        result_status = data.get("result")
        if result_status != "success":
            error_type = data.get("error-type", "Unknown API error")
            raise ExchangeRateAPIError(f"Exchange Rate API error: {error_type}")

        rates_dict = data.get("rates") or data.get("conversion_rates")
        if not rates_dict or not isinstance(rates_dict, dict):
            raise ExchangeRateAPIError("Exchange Rate API response missing valid 'rates' dictionary.")

        # Extract timestamp
        time_last_update = data.get("time_last_update_utc")
        if not time_last_update:
            time_last_update = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC")

        provider = data.get("provider") or self.provider_name

        # Parse rates into Decimal
        decimal_rates = {}
        for curr, rate_val in rates_dict.items():
            try:
                decimal_rates[curr.upper()] = Decimal(str(rate_val))
            except (InvalidOperation, ValueError):
                continue

        return {
            "base": base,
            "rates": decimal_rates,
            "last_updated": time_last_update,
            "provider": provider,
            "fetched_at": time.time()
        }

    def get_rates(self, base_currency: str) -> Dict[str, Any]:
        """
        Retrieve exchange rates for a base currency, utilizing thread-safe in-memory caching.
        If cache is expired, fetches fresh rates.
        """
        base = self.validate_currency(base_currency)

        with self._cache_lock:
            cached_entry = self._cache.get(base)
            if cached_entry:
                age = time.time() - cached_entry["fetched_at"]
                if age < self.cache_ttl_seconds:
                    return cached_entry

        # Fetch fresh rates
        fresh_data = self.fetch_rates_from_api(base)

        with self._cache_lock:
            self._cache[base] = fresh_data

        return fresh_data

    def get_exchange_rate(self, source_currency: str, target_currency: str) -> Dict[str, Any]:
        """
        Get the precise exchange rate from source_currency to target_currency.
        Handles same-currency conversion (rate = 1.0) without redundant network requests.
        """
        src = self.validate_currency(source_currency)
        tgt = self.validate_currency(target_currency)

        # Same currency parity
        if src == tgt:
            return {
                "source": src,
                "target": tgt,
                "rate": Decimal("1.0"),
                "rate_formatted": f"1 {src} = 1.000000 {tgt}",
                "provider": "Direct Parity (1:1)",
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "is_cached": True
            }

        rates_data = self.get_rates(src)
        rates = rates_data["rates"]

        if tgt not in rates:
            raise UnsupportedCurrencyError(
                f"Target currency '{tgt}' not available from rate provider for base '{src}'."
            )

        rate = rates[tgt]
        return {
            "source": src,
            "target": tgt,
            "rate": rate,
            "rate_formatted": f"1 {src} = {rate:.6f} {tgt}",
            "provider": rates_data.get("provider", self.provider_name),
            "last_updated": rates_data.get("last_updated"),
            "is_cached": (time.time() - rates_data["fetched_at"]) > 0.1
        }

    def convert(
        self,
        amount: Any,
        source_currency: str,
        target_currency: str
    ) -> Dict[str, Any]:
        """
        Perform complete currency conversion:
        - Validates amount and currencies
        - Fetches exchange rate
        - Formula: Converted Amount = Transaction Amount * Exchange Rate
        - Calculates normalized reference USD amount for ML model
        - Formats all amounts with currency symbols and decimals
        """
        amount_dec = self.parse_amount(amount)
        src = self.validate_currency(source_currency)
        tgt = self.validate_currency(target_currency)

        # H5: the target rate and the USD reference rate come from the SAME base response. If the USD rate is
        # missing the payment fails; a foreign amount is never treated as USD.
        rates_data = None
        if not (src == tgt == "USD"):
            rates_data = self.get_rates(src)
        if src == tgt:
            rate_dec = Decimal("1")
        else:
            rate_dec = rates_data["rates"].get(tgt)
            if rate_dec is None:
                raise UnsupportedCurrencyError(
                    f"Target currency '{tgt}' not available from rate provider for base '{src}'."
                )
        if src == "USD":
            usd_rate = Decimal("1")
        else:
            usd_rate = rates_data["rates"].get("USD")
            if usd_rate is None:
                raise ExchangeRateAPIError(
                    f"USD reference rate for {src} is unavailable, so the payment cannot be risk-scored. Try again later."
                )
        if rates_data is None:
            rate_info = {"provider": "Direct Parity (1:1)",
                         "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                         "is_cached": False}
        else:
            rate_info = {"provider": rates_data.get("provider", self.provider_name),
                         "last_updated": rates_data.get("last_updated"),
                         "is_cached": rates_data.get("from_cache", False)}

        converted_dec = self.quantize_amount(amount_dec * rate_dec, tgt)
        normalized_usd = self.quantize_amount(amount_dec * usd_rate, "USD")

        return {
            "source_currency": src,
            "source_symbol": SUPPORTED_CURRENCIES[src]["symbol"],
            "source_name": SUPPORTED_CURRENCIES[src]["name"],
            "target_currency": tgt,
            "target_symbol": SUPPORTED_CURRENCIES[tgt]["symbol"],
            "target_name": SUPPORTED_CURRENCIES[tgt]["name"],
            "original_amount": float(amount_dec),
            "original_amount_decimal": str(amount_dec),
            "formatted_original_amount": self.format_amount(amount_dec, src),
            "exchange_rate": float(rate_dec),
            "exchange_rate_decimal": str(rate_dec),
            "exchange_rate_formatted": f"1 {src} = {rate_dec:.6f} {tgt}",
            "converted_amount": float(converted_dec),
            "converted_amount_decimal": str(converted_dec),
            "formatted_converted_amount": self.format_amount(converted_dec, tgt),
            "normalized_usd_amount": float(normalized_usd),
            "provider": rate_info["provider"],
            "last_updated": rate_info["last_updated"],
            "is_cached": rate_info["is_cached"]
        }

    def clear_cache(self):
        """Clear the in-memory exchange rate cache (useful for testing)."""
        with self._cache_lock:
            self._cache.clear()


# Global Singleton instance
currency_service = CurrencyService()
