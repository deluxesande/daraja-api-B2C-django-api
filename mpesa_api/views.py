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
import os
from datetime import datetime

# Load the .env file
load_dotenv()

cl = MpesaClient()

def generate_auth_token():
    """
    Description:generate the access token required by mpesa for authentication.\n
    """
    consumer_key = "1gWEBFicQT4daQ11WlyPAD494j3MLe8L"
    consumer_secret = "LA7ADyBEbfqDvqEu"
    api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))

    # format the response so as to get the token only
    formated_response = json.loads(response.text)
    token = formated_response['access_token']
    
    return token

class IndexView(APIView):
    def get(self, request):
        phone_number = "0742210044"
        amount = 1
        account_reference = "Deluxe Mpesa"
        transaction_desc = "Description"
        callback_url = "https://292b-102-215-12-244.ngrok-free.app/stk-push-callback/"

        response = cl.stk_push(
            phone_number, amount, account_reference, transaction_desc, callback_url
        )
        data = json.loads(response.text)

        # # Save the transaction details to the database
        # MpesaTransaction.objects.create(
        #     transaction_id=data["MerchantRequestID"],
        #     amount=amount,
        #     phone_number=phone_number,
        #     account_reference=account_reference,
        #     transaction_desc=transaction_desc,
        # )

        return Response(data)


@method_decorator(csrf_exempt, name="dispatch")
class STKPushCallBack(APIView):
    """
    Description:This is the endpoint where safaricom are going to send the callback after a transaction\n
    Expected Responses are either success or error 
    """
    def post(self,request,*args,**kwargs):
        
        # first check that the request is not empty
        if request.data:
            print(request.data)

            # get the result code
            the_result_code = request.data['Body']['stkCallback']['ResultCode']

            if the_result_code == 0:
                # this means its successful save the response here
                print("Success request")
                print(request.data['Body']['stkCallback']['CallbackMetadata']['Item'][1]['Value']) 
            
            else:
                #this means the payment was not success so save the error still 
                print("This is not a successful request")


                merchant_request_id = request.data['Body']['stkCallback']['MerchantRequestID']
                checkout_request_id = request.data['Body']['stkCallback']['CheckoutRequestID']
                result_code = request.data['Body']['stkCallback']['ResultCode']
                result_description = request.data['Body']['stkCallback']['ResultDesc']
                
                # first do a query and get to see if the merchant_request_id and  checkout_request_id do exist
                the_transaction = MpesaTransaction.objects.filter(transaction_id=merchant_request_id,checkout_request_id=checkout_request_id).first()
                try:
                    print(the_transaction)

                    # update the transaction with the result code and result_description
                    the_transaction.result_code = result_code
                    the_transaction.result_description = result_description
                    the_transaction.status = "FAILED"
                    the_transaction.save()



                
                except MpesaTransaction.DoesNotExist:
                    print("multiple objects or doesnt exist")
                    pass         
        else:
            pass
            # print("the request is not valid")
        
        message = {
            "ResultCode": 0,
            "ResultDesc": "The service was accepted successfully",
            "ThirdPartyTransID": "1234567890"
            }
        
        return Response(message,status=status.HTTP_200_OK)

class MpesaExpressStatusView(APIView):
    def get(self, request):
        transaction_id = "2ba8-4165-beca-292db11f9ef8381589"
        # Define the URL for the Transaction Status API
        url = "https://sandbox.safaricom.co.ke/mpesa/transactionstatus/v1/query"

        # Define the headers for the request
        headers = {
            "Authorization": f"Bearer {generate_auth_token()}",
            "Content-Type": "application/json"
        }

        # Define the payload for the request
        payload = {
            "Initiator": settings.MPESA_INITIATOR_USERNAME,
            "SecurityCredential": settings.MPESA_SECURITY_CREDENTIAL,
            "CommandID": "TransactionStatusQuery",
            "TransactionID": transaction_id,
            "PartyA": settings.MPESA_SHORTCODE,
            "IdentifierType": "2",
            "ResultURL": "https://292b-102-215-12-244.ngrok-free.app/stk-push-callback/",
            "QueueTimeOutURL": "https://292b-102-215-12-244.ngrok-free.app/stk-push-callback/",
            "Remarks": "Checking transaction status",
            "Occasion": "CheckTransactionStatus"
        }

        # Send the request
        response = requests.post(url, headers=headers, json=payload)

        # Return the response from the transaction status request
        return Response(response.json())