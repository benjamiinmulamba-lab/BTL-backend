"""
Central config — loads everything from environment variables.
Nothing here (or anywhere in this backend) should ever be sent to the frontend.
Create a `.env` file locally (see `.env.example`) and never commit it.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Supabase ---
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # service_role key, backend only

    # --- PayFast ---
    PAYFAST_MERCHANT_ID = os.environ.get("PAYFAST_MERCHANT_ID")
    PAYFAST_MERCHANT_KEY = os.environ.get("PAYFAST_MERCHANT_KEY")
    PAYFAST_PASSPHRASE = os.environ.get("PAYFAST_PASSPHRASE")  # optional but recommended

    # Toggle sandbox vs live — set PAYFAST_SANDBOX=false in production
    PAYFAST_SANDBOX = os.environ.get("PAYFAST_SANDBOX", "true").lower() == "true"
    PAYFAST_PROCESS_URL = (
        "https://sandbox.payfast.co.za/eng/process"
        if PAYFAST_SANDBOX
        else "https://www.payfast.co.za/eng/process"
    )
    PAYFAST_VALIDATE_URL = (
        "https://sandbox.payfast.co.za/eng/query/validate"
        if PAYFAST_SANDBOX
        else "https://www.payfast.co.za/eng/query/validate"
    )

    # --- URLs the frontend/PayFast need ---
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5500")
    RETURN_URL = f"{SITE_URL}/donate-success.html"
    CANCEL_URL = f"{SITE_URL}/donate.html"
    NOTIFY_URL = os.environ.get("PAYFAST_NOTIFY_URL", "https://your-backend.onrender.com/api/payfast-webhook")

    # PayFast's known IP hostnames — used to validate the source of an ITN (see services/payfast_service.py)
    PAYFAST_VALID_HOSTS = [
        "www.payfast.co.za",
        "sandbox.payfast.co.za",
        "w1w.payfast.co.za",
        "w2w.payfast.co.za",
    ]
