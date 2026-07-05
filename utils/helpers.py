"""Helper functions for Forex Trading Application"""

from datetime import datetime
import re


def calculate_pip_value(pair, lot_size=1, account_currency='USD'):
    """Calculate pip value for a currency pair
    
    Args:
        pair: Currency pair (e.g., 'EUR/USD')
        lot_size: Trade size in lots
        account_currency: Account currency
        
    Returns:
        Pip value in account currency
    """
    # Standard lot = 100,000 units
    standard_lot = 100000
    
    # Simplified calculation (in real app, would use current exchange rates)
    base_currency, quote_currency = pair.split('/')
    
    if quote_currency == account_currency:
        pip_value = (0.0001 * standard_lot * lot_size)
    elif base_currency == account_currency:
        pip_value = (0.0001 * standard_lot * lot_size)
    else:
        # Approximate conversion
        pip_value = (0.0001 * standard_lot * lot_size)
    
    return round(pip_value, 2)


def format_currency(amount, currency='USD'):
    """Format currency amount
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted string
    """
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥'
    }
    
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def parse_datetime(date_string):
    """Parse datetime string
    
    Args:
        date_string: Date string in various formats
        
    Returns:
        datetime object or None
    """
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
        '%d/%m/%Y %H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None


def validate_currency_pair(pair):
    """Validate currency pair format
    
    Args:
        pair: Currency pair string
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[A-Z]{3}/[A-Z]{3}$'
    return bool(re.match(pattern, pair))


def calculate_percentage_change(old_value, new_value):
    """Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0
    
    return ((new_value - old_value) / abs(old_value)) * 100