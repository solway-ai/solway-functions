import sys
import os
import logging
import azure.functions as func

from SolwayAPI import app as api


logging.basicConfig(level=logging.INFO)

app = func.AsgiFunctionApp(
    app=api, 
    http_auth_level=func.AuthLevel.ANONYMOUS
)

