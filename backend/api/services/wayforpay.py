import hashlib
import hmac
import requests
from datetime import datetime


class WayForPay:
    API_URL = "https://api.wayforpay.com/api"

    def __init__(self, account, key, domain):
        self.account = account
        self.key = key
        self.domain = domain

    def get_signature(self, data):
        order_reference = data['orderReference']
        order_date = data['orderDate']
        amount = data['amount']
        currency = data['currency']
        product_names = data['productName']
        product_counts = data['productCount']
        product_prices = data['productPrice']

        signature_text = (
            f"{self.account};"
            f"{self.domain};"
            f"{order_reference};"
            f"{order_date};"
            f"{amount};"
            f"{currency};"
            f"{';'.join(product_names)};"
            f"{';'.join(str(count) for count in product_counts)};"
            f"{';'.join(str(price) for price in product_prices)}"
        )
        return hmac.new(self.key.encode("utf-8"), signature_text.encode("utf-8"), hashlib.md5).hexdigest()

    def create_invoice(self, data):
        try:
            body = {
                "merchantAccount": self.account,
                "merchantDomainName": self.domain,
                "merchantSignature": self.get_signature(data),
                "transactionType": "CREATE_INVOICE",
                "apiVersion": "1",
                "language": "ua",
                "notifyMethod": "email"
            }
            body.update(data)
            headers = {"Content-Type": "application/json"}

            response = requests.post(self.API_URL, json=body, headers=headers)

            if response.text == "Api cannot read incoming request data. Unknown format":
                raise ValueError("Unknown format")

            return response.json()

        except KeyError as e:
            raise KeyError(f"No required argument – {e}")
        except Exception as e:
            raise e

    @staticmethod
    def get_answer_signature(merchant_key, data):
        order_reference = data["orderReference"]
        status = data["status"]
        time = data["time"]

        signature_text = (
            f"{order_reference};"
            f"{status};"
            f"{time}"
        )
        return hmac.new(merchant_key.encode("utf-8"), signature_text.encode("utf-8"), hashlib.md5).hexdigest()