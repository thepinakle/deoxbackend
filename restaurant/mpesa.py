import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
import base64
from datetime import datetime

def lipa_na_mpesa_online(phone_number, amount, account_reference, transaction_desc):
    business_short_code = settings.MPESA_SHORTCODE
    lipa_na_mpesa_online_passkey = settings.MPESA_PASSKEY
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET
    api_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    oauth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    callback_url = settings.MPESA_CALLBACK_URL

    # Generate the password
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{business_short_code}{lipa_na_mpesa_online_passkey}{timestamp}".encode()).decode('utf-8')

    # Get the access token
    response = requests.get(
        oauth_url,
        auth=HTTPBasicAuth(consumer_key, consumer_secret)
    )
    access_token = response.json()['access_token']

    # Prepare the request payload
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

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Make the request to the M-Pesa API
    response = requests.post(api_url, json=payload, headers=headers)
    return response.json()