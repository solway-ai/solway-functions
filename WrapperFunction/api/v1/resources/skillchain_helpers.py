import copy

from typing import Tuple, Dict, List

#import pandas as pd

from openai import AsyncOpenAI


async def make_open_ai_request(client:AsyncOpenAI, system_prompt:str, user_message:str, model:str='gpt-4o', **request_kwargs):
    """
    calls openai chat completion endpoint with a specified
    system prompt and user message
    """
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        **request_kwargs,
    )
    return response


def build_string(string_dict:dict):
    """ creates an LLM friendly representation of the contents of a python dictionary """
    string = ''
    for key, value in string_dict.items():
        processed_key = key.capitalize()
        processed_key = processed_key.replace('_', ' ')
        string += processed_key
        string += ':\n- '
        string += '\n- '.join(value)
        string += '\n\n'
        
    return string


def build_skills(skill_prompts:dict, agent_internals):
    """ updates the template prompts with the generations """

    def build_prompt(base_prompt:str, agent_interals:dict):
        """ swaps out the symbols for their generated replacements"""
        prompt = base_prompt
        for _, value in agent_interals.items():
            prompt = prompt.replace(value['marker'], value['replacement'])
        
        return prompt

    updated_skills = copy.deepcopy(skill_prompts)
    for key, _ in skill_prompts.items():
        updated_skills[key] = build_prompt(updated_skills[key], agent_internals)
    
    return updated_skills


def build_advanced_skills(skill_prompts):
    """ Updates prompts that use previous model outputs """
    
    updated_skills = copy.deepcopy(skill_prompts)
    for key in skill_prompts.keys():
        if key != 'role':
            updated_skills[key] = updated_skills['role'] + updated_skills[key]
    
    del updated_skills["role"]
    return updated_skills


def update_internals(context:dict, agent_internals:dict):
    """updates the agent dictionary with the context dict"""
    updated_internals = dict()
    for key, _ in agent_internals.items():
        updated_internals[key]= agent_internals[key]
        updated_internals[key]['replacement'] = context.get(key, '')
    return updated_internals


def chunk_document_naive(encoder:object, document:str, chunksize:int=40000, overlap:int=1250):
    """ chunks a document into chunks with an overlap """
    
    tokens = encoder.encode(document)
    chunks = []
    start = 0

    while start < len(tokens) - overlap:

        # Determine the end of the current chunk
        if start == 0:
            end = start + chunksize 
        else:
            end = start + chunksize - overlap
        
        end = min(end, len(tokens))

        chunk = tokens[start:end]
        chunks.append(chunk)

        # Move the start for the next chunk
        if start == 0:
            start = end
        else:
            start = end - overlap 

    return chunks


# def get_all_textIN(document_name, parsed_pdf:dict) -> str:
#     """
#     the documents are parsed as dictionaries to preserve page number
#     this documents gets all the raw text as one
#     """
#     format_string = document_name.upper() + "PAGE NUMBER: "
#     try:
#         return ' '.join([format_string + idx + "\n\n" + page.get("textIN") for idx, page in parsed_pdf.items()])
#     except Exception as e:
#         print(e)
#         print(parsed_pdf)


# def get_all_numTokens(parsed_pdf:dict) -> str:
#     """
#     the documents are parsed as dictionaries to preserve page number
#     this documents gets all the raw text as one
#     """
#     total_tokens = 0
#     try:
#         for idx, page in parsed_pdf.items():
#             total_tokens += int(page.get('numTokens'))

#     except Exception as e:
#         print(e)
#         print(parsed_pdf)

#     return total_tokens


# def pd_list_val_to_idx(df:pd.DataFrame, col:str) -> Tuple[Dict[int, str], Dict[int, List[float]]]:
#     """ flattens the list of chunks / embs, returns a datastructure for use in retrieval"""
#     outer_list = df[col].tolist()
#     all_eles = [
#         ele for eles in outer_list for ele in eles
#     ]
#     return {idx:ele for idx, ele in enumerate(all_eles)}


# def corpus_statistics(processed_files:dict) -> None:
#     """
#     calculates the total number of tokens in the corpus
#     and the estimated cost per skill
#     """

#     total_tokens = 0
#     total_document_tokens = 0

#     # if the extension is a .xlsx, the value will be a dict
#     # all other extensions will be a string
#     for key, value in processed_files.items():
        
#         total_tokens += num_tokens_from_string(key)

#         if isinstance(value, dict):
#             for _, inner_value in value.items():

#                 if isinstance(inner_value, dict):      
#                     for _, inner_inner_value in inner_value.items():
#                         if isinstance(inner_inner_value, list):
#                             for ele in inner_inner_value:
#                                 if isinstance(ele, str):
#                                     total_document_tokens += num_tokens_from_string(ele)

#                 elif isinstance(inner_value, str):
#                     total_document_tokens += num_tokens_from_string(inner_value)
            
#         elif isinstance(value, str):
#             total_document_tokens += num_tokens_from_string(value)

#     print(f"Total Project Tokens: {total_document_tokens}")
#     print(f"Total Cost per Skill: ~${round((total_document_tokens / 1000) * .03, 4)}")