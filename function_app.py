import logging
import azure.functions as func

# from SolwayAPI import app as api

# app = func.AsgiFunctionApp(
#     app=api, 
#     http_auth_level=func.AuthLevel.ANONYMOUS
# )

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="HttpTrigger", auth_level=func.AuthLevel.ANONYMOUS)
def HttpTrigger(req: func.HttpRequest) -> func.HttpResponse:
    try:
        from SolwayAPI.api.v1.core.chain_prompts import research_questions
        logging.info('Imported successfully.')
        return {
            "prompt": research_questions
        }
    except ImportError as e:
        logging.error(f'Failed to import: {e}')
        return func.HttpResponse(f"Import error: {str(e)}", status_code=500)