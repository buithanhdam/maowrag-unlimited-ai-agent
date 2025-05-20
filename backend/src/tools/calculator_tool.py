import math

def sum(a: float, b: float) -> float:
    """Returns the sum of a and b."""
    return a + b
def sum_numbers(numbers: list[float]) -> float:
    """Returns the sum of a list of numbers."""
    return sum(numbers)
def subtract(a: float, b: float) -> float:
    """Returns the difference of a and b."""
    return a - b
def multiply(a: float, b: float) -> float:
    """Returns the product of a and b."""
    return a * b
def divide(a: float, b: float) -> float:
    """Returns the division of a by b."""
    if b == 0:
        return 0
    return a / b
def power(a: float, b: float) -> float:
    """Returns a raised to the power of b."""
    return a ** b
def square_root(a: float) -> float:
    """Returns the square root of a."""
    if a < 0:
        return 0
    return math.sqrt(a)
def abs(a: float) -> float:
    """Returns the absolute value of a."""
    return abs(a)
def convert_currency_to_USD(amount: float, from_currency: str = "USD") -> float:
    """Convert amount from one currency to another using predefined rates."""
    # Example implementation - in production this would call an API or use a database
    rates = {
        "USD": 1.0,
        "EUR": 0.92,
        "VND": 24850.0,
        "JPY": 154.35,
        "CNY": 7.24
    }
    
    if from_currency not in rates:
        raise ValueError(f"Currency not supported: {from_currency} or {"USD"}")
    if from_currency == "USD":
        return amount
    # Convert to USD first, then to target currency
    usd_amount = amount / rates[from_currency]
    return usd_amount * rates["USD"]