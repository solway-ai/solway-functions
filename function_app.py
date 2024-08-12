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

# app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# @app.route(route="HttpTrigger", auth_level=func.AuthLevel.ANONYMOUS)
# def HttpTrigger(req: func.HttpRequest) -> func.HttpResponse:


#     logging.info(f'Sys path: {sys.path}')
#     logging.info(f'Python version: {sys.version}')
#     logging.info(f'Installed packages: {os.system("pip freeze")}')

#     try:
#         from SolwayAPI.api.v1.core.chain_prompts import research_questions
#         from SolwayAPI.api.v1.resources.notion import create_child_notion_page

#         logging.info('Imported research_questions successfully.')
#         logging.info(str(research_questions))
#         return func.HttpResponse(f"Succes: {research_questions}", status_code=200)
    
#     except ImportError as e:
#         logging.error(f'Failed to import: {e}')
#         return func.HttpResponse(f"Import error: {str(e)}", status_code=500)