import json
import datetime
import logging

import azure.functions as func

from SolwayAPI import app as api

app = func.AsgiFunctionApp(
    app=api, 
    http_auth_level=func.AuthLevel.ANONYMOUS
)
