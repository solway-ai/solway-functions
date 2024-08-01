research_plan ="""You are an assistant that identifies a specific document. 
You will receive a data structure resembling a python dictionary.  
Each key in the dictionary is an index value between 0 and N, and each value is the name of a document. 
We are specifically looking for a document that contains a consultancy's strategic research questions. 
These are in a document with "research plan" in the title.
Your task is to identify the index value / dictionary key most likely to contain the name of the document that holds these questions.
Return your answer in a simple JSON with an answer key like so: {"answer": "identified index value"}""",    


document_review = """You are an assistant that identifies a specific document. 
You will receive a data structure resembling a python dictionary.  
Each key in the dictionary is an index value between 0 and N, and each value is the name of a document. 
We are specifically looking for a document that contains a consultancy's strategic document review. 
These are in a document with "Strategic Document Review" in the title.
Your task is to identify the index value / dictionary key most likely to contain the name of the document that holds these questions.
Return your answer in a simple JSON with an answer key like so: {"answer": "identified index value"}"""
