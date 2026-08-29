"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/core/ssl_patch.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : SSL configuration patch for Windows environments. Resolves local
              issuer certificate verification failures when downloading
              SentenceTransformer models and Hugging Face assets.
================================================================================
"""
import os
import ssl
import urllib3
import requests

def apply_ssl_fix() -> None:
    """
    Applies SSL certificate fixes and unverified context fallbacks to prevent
    SSLCertVerificationError on Windows / corporate firewall environments.
    """
    try:
        # Disable SSL verification environment flags for Hugging Face Hub
        os.environ["CURL_CA_BUNDLE"] = ""
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

        # Create unverified HTTPS context for urllib / standard library
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Patch requests.Session to default to verify=False when needed
        orig_init = requests.Session.__init__
        def patched_session_init(self, *args, **kwargs):
            orig_init(self, *args, **kwargs)
            self.verify = False
        requests.Session.__init__ = patched_session_init
    except Exception:
        pass

# Automatically execute on import
apply_ssl_fix()
