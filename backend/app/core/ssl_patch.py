"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/core/ssl_patch.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Universal SSL configuration patch for Windows & Corporate networks.
              Resolves local issuer certificate verification failures across:
                - urllib / standard library
                - requests.Session
                - httpx.Client and httpx.AsyncClient (used by Groq and LlamaIndex)
                - Hugging Face Hub model downloads
================================================================================
"""
import os
import ssl
import urllib3

def apply_ssl_fix() -> None:
    """
    Applies SSL certificate fixes and unverified context fallbacks to prevent
    SSLCertVerificationError on Windows / corporate firewall environments.
    """
    try:
        # Disable SSL verification environment flags for Hugging Face & cURL
        os.environ["CURL_CA_BUNDLE"] = ""
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

        # Create unverified HTTPS context for urllib / standard library
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Patch requests.Session to default to verify=False
        try:
            import requests
            orig_req_init = requests.Session.__init__
            def patched_req_init(self, *args, **kwargs):
                orig_req_init(self, *args, **kwargs)
                self.verify = False
            requests.Session.__init__ = patched_req_init
        except Exception:
            pass

        # Patch httpx.Client and httpx.AsyncClient (used by Groq & LlamaIndex)
        try:
            import httpx
            orig_httpx_init = httpx.Client.__init__
            def patched_httpx_init(self, *args, **kwargs):
                kwargs["verify"] = False
                orig_httpx_init(self, *args, **kwargs)
            httpx.Client.__init__ = patched_httpx_init

            orig_async_init = httpx.AsyncClient.__init__
            def patched_async_init(self, *args, **kwargs):
                kwargs["verify"] = False
                orig_async_init(self, *args, **kwargs)
            httpx.AsyncClient.__init__ = patched_async_init
        except Exception:
            pass
    except Exception:
        pass

# Automatically execute on import
apply_ssl_fix()
