from django_daraja.mpesa.core import MpesaClient

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from mpesa_api.models import MpesaTransaction

from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import json
import requests
from datetime import datetime
import base64
import os

# Load the .env file
load_dotenv()

cl = MpesaClient()


def generate_auth_token():
    """
    Description:generate the access token required by mpesa for authentication.\n
    """
    api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(api_URL, auth=HTTPBasicAuth(os.getenv("CONSUMER_KEY"), os.getenv("CONSUMER_SECRET")))

    # format the response so as to get the token only
    formatted_response = json.loads(response.text)
    token = formatted_response["access_token"]

    print(token)
    return token


def get_encoded_string():
    """
    Description:Generate the password for encrypting the request by base64 encoding BusinessShortcode, Passkey and Timestamp.
    """
    # Define your shortcode, passkey, and timestamp
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Combine the shortcode, passkey, and timestamp
    combined_string = f"{shortcode}{passkey}{timestamp}"

    # Encode the combined string in base64
    return base64.b64encode(combined_string.encode()).decode()

class RootAPI(APIView):
    """
    Description:This is the root endpoint of the API\n
    """

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "message": "Welcome to the Mpesa API",
                "endpoints": {
                    "STK Push": "/payment/",
                    "STK Push Callback": "/stk-push-callback/",
                    "STK Push Status": "/status/",
                },
            },
            status=status.HTTP_200_OK,
        )

@method_decorator(csrf_exempt, name="dispatch")
class STKPushCallBack(APIView):
    """
    Description:This is the endpoint where safaricom are going to send the callback after a transaction\n
    Expected Responses are either success or error
    """

    def post(self, request, *args, **kwargs):

        # first check that the request is not empty
        if request.data:
            print(request.data)

            # get the result code
            the_result_code = request.data["Body"]["stkCallback"]["ResultCode"]

            if the_result_code == 0:
                # this means its successful save the response here
                print("Success request")
                print(
                    request.data["Body"]["stkCallback"]["CallbackMetadata"]["Item"][1][
                        "Value"
                    ]
                )

            else:
                # this means the payment was not success so save the error still
                print("This is not a successful request")

                merchant_request_id = request.data["Body"]["stkCallback"][
                    "MerchantRequestID"
                ]
                checkout_request_id = request.data["Body"]["stkCallback"][
                    "CheckoutRequestID"
                ]
                result_code = request.data["Body"]["stkCallback"]["ResultCode"]
                result_description = request.data["Body"]["stkCallback"]["ResultDesc"]

                # first do a query and get to see if the merchant_request_id and  checkout_request_id do exist
                the_transaction = MpesaTransaction.objects.filter(
                    transaction_id=merchant_request_id,
                    checkout_request_id=checkout_request_id,
                ).first()
                try:
                    print(the_transaction)

                    # update the transaction with the result code and result_description
                    the_transaction.result_code = result_code
                    the_transaction.result_description = result_description
                    the_transaction.status = "FAILED"
                    the_transaction.save()

                except MpesaTransaction.DoesNotExist:
                    print("multiple objects or doesn't exist")
                    pass
        else:
            pass
            # print("the request is not valid")

        message = {
            "ResultCode": 0,
            "ResultDesc": "The service was accepted successfully",
            "ThirdPartyTransID": "1234567890",
        }

        return Response(message, status=status.HTTP_200_OK)


class MpesaTransactionStatus(APIView):
    """
    Description:This is the endpoint to check the status of a transaction\n
    """
    def get(self, request):
        transaction_id = "2ba8-4165-beca-292db11f9ef8381589"
        # Define the URL for the Transaction Status API
        url = "https://sandbox.safaricom.co.ke/mpesa/transactionstatus/v1/query"

        # Define the headers for the request
        headers = {
            "Authorization": f"Bearer {generate_auth_token()}",
            "Content-Type": "application/json",
        }

        # Define the payload for the request
        payload = {
            "Initiator": settings.MPESA_INITIATOR_USERNAME,
            "SecurityCredential": settings.MPESA_SECURITY_CREDENTIAL,
            "CommandID": "TransactionStatusQuery",
            "TransactionID": transaction_id,
            "PartyA": settings.MPESA_SHORTCODE,
            "IdentifierType": "2",
            "ResultURL": settings.MPESA_CALLBACK_URL,
            "QueueTimeOutURL": settings.MPESA_CALLBACK_URL,
            "Remarks": "Checking transaction status",
            "Occasion": "CheckTransactionStatus"
        }

        # Send the request
        response = requests.post(url, headers=headers, json=payload)

        # Return the response from the transaction status request
        return Response(response.json())
    
class MpesaTransactionPayment(APIView):
    """
    Description:This is the endpoint to initialize a payment\n
    """
    def post(self, request):
        """
        Description:Endpoint to initialize payment \n
        """
        url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        # Define the headers for the request
        headers = {
            "Authorization": f"Bearer {generate_auth_token()}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": get_encoded_string(),
            "Timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            "TransactionType": "CustomerPayBillOnline",
            "Amount": "1",
            "PartyA": "254742210044", # The phone number sending money
            "PartyB": settings.MPESA_SHORTCODE,
            # "PhoneNumber": "254714208354", # The Mobile Number to receive the STK Pin Prompt
            "PhoneNumber": "254742210044", # The Mobile Number to receive the STK Pin Prompt
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": "Deluxe Sande",
            "TransactionDesc": "Test",
        }

        # Send the request
        response = requests.post(url, headers=headers, json=payload)

        # Return the response from the transaction status request
        return Response(response.json())
    
class MpesaExpressQuery(APIView):
    """
    Description: Use this API to check the status of a Lipa Na M-Pesa Online Payment.\n
    """
    def post(self, request):
        url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"

        # Define the headers for the request
        headers = {
            "Authorization": f"Bearer {generate_auth_token()}",
            "Content-Type": "application/json",
        }
        
        payload = {    
            "BusinessShortCode": settings.MPESA_SHORTCODE,    
            "Password": get_encoded_string(),    
            "Timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),    
            "CheckoutRequestID": "ws_CO_09022024131620073742210044",    
        } 

        # Send the request
        response = requests.post(url, headers=headers, json=payload)

        # Return the response from the transaction status request
        return Response(response.json())