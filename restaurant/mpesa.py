from django.conf import settings
from requests.auth import HTTPBasicAuth
import requests
import base64
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_mpesa_access_token():
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET
    oauth_url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    try:
        response = requests.get(oauth_url, auth=HTTPBasicAuth(consumer_key, consumer_secret), timeout=30)
        response.raise_for_status()
        access_token = response.json().get('access_token')
        return access_token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error generating access token: {e}")
        raise Exception("Failed to generate access token")

def lipa_na_mpesa_online(phone_number, amount, account_reference, transaction_desc):
    business_short_code = settings.MPESA_SHORTCODE
    lipa_na_mpesa_online_passkey = settings.MPESA_PASSKEY
    callback_url = settings.MPESA_CALLBACK_URL
    api_url = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'

    # Generate the password
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{business_short_code}{lipa_na_mpesa_online_passkey}{timestamp}".encode()).decode('utf-8')

    # Generate the access token
    access_token = generate_mpesa_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": business_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": business_short_code,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making M-Pesa request: {e}")
        raise Exception("Failed to make M-Pesa request")

# Example usage
try:
    response = lipa_na_mpesa_online("254712345678", 100, "AccountRef", "TransactionDesc")
    print(response)
except Exception as e:
    print(f"Error: {e}")