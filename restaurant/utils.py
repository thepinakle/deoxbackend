# utils.py

def calculate_delivery_fee(total_amount):
    """Calculate delivery fee based on the total order amount."""
    if total_amount < 5:
        return 0
    elif 75 <= total_amount <= 150:
        return 21
    elif 151 <= total_amount <= 200:
        return 31
    elif 201 <= total_amount <= 300:
        return 36
    elif 301 <= total_amount <= 400:
        return 51
    elif 401 <= total_amount <= 500:
        return 55
    elif 501 <= total_amount <= 600:
        return 60
    else:  # for amounts above 600
        return 70
