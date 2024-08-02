import logging
import azure.functions as func

from SolwayAPI.main import app as api

app = func.AsgiFunctionApp(
    app=api, 
    http_auth_level=func.AuthLevel.ANONYMOUS
)


# app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)    

# @app.function_name("personas")

#     @app.route(route="character-managment/personas")
#     def personas(req: func.HttpRequest) -> func.HttpResponse:
#         logging.info('Python HTTP trigger function processed a request.')
#         return func.HttpResponse("ok", status_code=200)