from . import adyen_utils

# Stubs/placeholders for Adyen calls you will wire up with real SDK/API later.
# Keep your Adyen API key/merchant account in environment variables.

def verify_hmac(hmac_key: str, notification: dict) -> bool:
    # TODO: implement proper HMAC validation for Adyen notifications.
    # For now return True to accept in test/dev.
    return True

def create_platform_account(merchant_payload: dict) -> dict:
    # TODO: Call Adyen Balance Platform API to create account/related legal entity
    return {"status": "stubbed", "accountCode": "ACCT_TEST_EXAMPLE"}
