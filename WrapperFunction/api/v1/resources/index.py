import os
import json
import copy
from typing import List, Union

import tiktoken
import voyageai
from voyageai import Client

from langchain_core.documents import Document
from langchain_voyageai import VoyageAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

from openai import AsyncOpenAI

import numpy as np
import pandas as pd

from api.v1.core.chain_prompts import prompts

from solway_pipeline.api.v1.resources.skillchain_helpers import (

    chunk_document_naive,
    get_all_textIN,
    get_all_numTokens,
    pd_list_val_to_idx
)


class IndexChain:

    def __init__(self, text_splitter:SemanticChunker, prompts:dict):
        

        self.encoding = tiktoken.get_encoding(encoding_name="cl100k_base")
        self.text_splitter = text_splitter
        self.prompts = prompts
        
    
    def create_chunks_for_index(self, file:dict, file_name:str, text_splitter:SemanticChunker=None):
        """ chunks a document, includes metadata"""
        chunks = text_splitter.split_documents([Document(page_content=page.get('textIN'), metadata={"page_number":idx}) for idx, page in file.items()])
        chunks = [{"text": chunk.page_content, "title":file_name, "page_number": chunk.metadata['page_number']} for chunk in chunks]
        return chunks 


    def get_embeddings(self, chunks:List[dict], batchsize:int=100) -> list:
        """embeds a list of texts with the voyager client"""

        batches = [chunk.get("text") for chunk in chunks]
        batches = [batches[step:step+batchsize] for step in range(0, len(batches), batchsize)]

        embeddings = []
        for batch in batches:
            embeddings.append(self.vo_client.embed(batch, model="voyage-large-2-instruct", input_type="document").embeddings)
        
        return [
            emb for embs in embeddings for emb in embs
        ]
        
    
    def create_documents_df(self) -> pd.DataFrame:
        """ runs the skills on the data"""

        df = pd.DataFrame(columns=['document', 'pages'], data=self.artifacts['raw_data'].items())[:3]

        df['textIN'] = df.apply(lambda row: get_all_textIN(row['document'], row['pages']), axis=1)
        df['numTokens'] = df['pages'].apply(get_all_numTokens)

        df = df.drop(df.index[int(self.internals['research_plan_idx'])])

        df.reset_index(inplace=True)

        df['chunks'] = df.apply(lambda row: self.create_chunks_for_index(row['pages'], row['document'], splitter), axis=1)
        df['chunks_embeddings'] = df.apply(lambda row: self.get_embeddings(row['chunks']), axis=1)

        print("writing documents df")
        df.to_json(f"{self.folder_name}/documents_df.json", orient="records")

        return df


    def get_documents_df(self, overwrite_documents:bool) -> pd.DataFrame:

        if not os.path.exists(f"{self.folder_name}/documents_df.json"):
            self.create_documents_df()
        
        if overwrite_documents:
            self.create_documents_df()

        print("reading documents df")
        self.docs_df = pd.DataFrame(json.load(open(f"{self.folder_name}/documents_df.json")))


    def contiguous_generation(base_prompt:str, replacement:str):
        """ replaces a component of a prompt, with a previous generation"""
        return base_prompt.replace('*', replacement)


    async def create_skill_completion(self, row, prompt, output_folder, model, token_thresh:int, overwrite_skills:bool, contiguous_on:str=None):
        """ iteratively calls gpt-4 with a passed set of prompts """
        
        directory_path = os.getcwd() + '/' + output_folder
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
        
        name = row['document']
        text = row['textIN']
        num_tokens = row['numTokens']
        
        if int(num_tokens) > token_thresh:

            chunks = chunk_document_naive(self.encoding, text)        
            text = [self.encoding.decode(chunk) for chunk in chunks]

            if "action_items" in output_folder  or "quotes" in output_folder:
                if 'summarization' in row.index:
                    text = [row['summarization'] + self.encoding.decode(chunk) for chunk in chunks]

        if contiguous_on:
            prompt = self.contiguous_generation(prompt, str(row[contiguous_on]))
        
        oai_responses = []
        if isinstance(text, str):            
            oai_response = await self.make_open_ai_request(prompt, text, model)            
            response = oai_response.choices[0].message.content
        
        else:
            for chunk in text:
                oai_response = await self.make_open_ai_request(prompt, chunk, model)
                oai_responses.append(oai_response)
            
            try:
                response = '\n\n'.join([resp.choices[0].message.content for resp in oai_responses if 'sorry' not in resp.choices[0].message.content])
            except Exception as e:
                print(f"Unexpected Error: {e}")
            
        
        if overwrite_skills:
            with open(f'{output_folder}/{name}.json', 'w') as outF:
                document = {
                    "document": name,
                    "textIN": text,
                    "openai_response": [resp.model_dump_json() for resp in oai_responses] if len(oai_responses) > 0 else oai_response.model_dump_json() 
                }
                json.dump(document, outF)
            
        return response


    async def run_skill_chain(self, skills, write_master_json:bool, file_name:str, num_samples:int, overwrite_skills:bool) -> Union[pd.DataFrame, None]:
        """ 
        runs the specified skills on the documents dataframe 
        returns a dataframe if all skill / document pairs complete successfully
        """
        
        if not num_samples:
            num_samples = self.docs_df.shape[0]
        
        run_df = self.docs_df[:num_samples].copy()

        for skill in skills:

            prompt = self.prompts['skill_prompts'][skill]
            skill_completions = []
            for _, row in run_df.iterrows():

                if '*' not in prompt:
                    completion = await self.create_skill_completion(
                        row=row, prompt=prompt, output_folder=self.folder_name+"/skills/"+skill, model='gpt-4o', token_thresh=40000
                    )
                else:
                    completion = await self.create_skill_completion(
                        row=row, prompt=prompt, output_folder=self.folder_name+"/skills/"+skill,  model='gpt-4o', token_thresh=40000, contiguous_on='keypoints'
                    )

                skill_completions.append(completion)
            
            if len(skill_completions) == run_df.shape[0]:
                
                run_df[skill] = skill_completions
                
                if write_master_json:
                    run_df.to_json(file_name)

                return run_df


    def cosine_similarity(self, a, b):
        """ similarity metrics to compare embeddings"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


    def get_indices(self, overwrite_indices):
        """ """
        if not os.path.exists(f"{self.folder_name}/chunks2idx.json") or overwrite_indices:
            chunks2idx = pd_list_val_to_idx(self.docs_df, 'chunks') 
            with open(f"{self.folder_name}/chunks2idx.json", 'w') as outF:
                json.dump(chunks2idx, outF)
        
        if not os.path.exists(f"{self.folder_name}/embs2idx.json") or overwrite_indices:
            embs2idx = pd_list_val_to_idx(self.docs_df, 'chunks_embeddings')
            with open(f"{self.folder_name}/embs2idx.json", 'w') as outF:
                json.dump(embs2idx, outF)


        self.chunks2idx = json.load(open(f"{self.folder_name}/chunks2idx.json"))
        self.embs2idx = json.load(open(f"{self.folder_name}/embs2idx.json"))
        self.vector_store = {idx:np.array(emb) for idx, emb in self.embs2idx.items()}


    def num_tokens_from_string(self, string: str, encoding_name: str = 'cl100k_base') -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    

    async def create_research_question_answers(self, rq_path:str, top_n:int) -> None:
        """ answers each research question in the proposal, writest oaj  son"""
        questions = self.internals['context']['research_questions'].split("\n")
        questions = [q.strip('- ') for q in questions[1:] if q]

        q_embs = vo.embed(questions, model="voyage-large-2-instruct", input_type="document").embeddings

        responses = []
        for idx, question in enumerate(questions):

            # Calculate similarity between the user question & each chunk
            similarities = [self.cosine_similarity(q_embs[idx], chunk) for chunk in self.embs2idx.values()]
            sorted_indices = np.argsort(similarities)[::-1]
            top_indices = sorted_indices[:top_n]
            top_chunks_after_retrieval = [self.chunks2idx[str(i)] for i in top_indices]
    
            context = ''
            for chunk in top_chunks_after_retrieval:
                context += f"!!! START CHUNK !!! DOCUMENT NAME TO REFERENCE: {chunk.get('title')} PAGE NUMBER TO REFERENCE: {chunk.get('page_number')} DOCUMENT TEXT: {chunk.get('text')} !!! END CHUNK !!!"

            sys_prompt = self.prompts['skill_prompts']['rq_answering'].replace("?", question)

            print(sys_prompt)
            response = await self.make_open_ai_request(sys_prompt, context)
            responses.append(response.choices[0].message.content)
        
        rqs = {q:r for q, r in zip(questions, responses)}

        print("creating research questions directory")
        if not os.path.exists(rq_path):
            os.makedirs(rq_path, exist_ok=True)

        print("writing research questions")
        with open(rq_path+"research_questions.json", "w") as outF:
            json.dump(rqs, outF)


    async def get_research_question_answers(self, rq_path:str, top_n:int, overwrite_rqs:bool) -> dict:
        """ """
        print(rq_path)
        if not os.path.exists(rq_path+"research_questions.json"):
            await self.create_research_question_answers(rq_path, top_n)
        
        if overwrite_rqs:
            await self.create_research_question_answers(rq_path, top_n)
        
        print("reading research questions")
        return json.load(open(rq_path+"research_questions.json"))


    async def __call__(
        self, 
        skills:Union[str, List[str]]='*', 
        samples:int=None, 
        top_n:int=30,

        overwrite_prompts:bool=False,
        overwrite_documents:bool=False,
        overwrite_indices:bool=False,
        overwrite_rqs:bool=False,
        overwrite_skills:bool=False):
        """ runs the key functions of the class """

        if skills != '*':
            for skill in skills:
                if skill not in self.prompts['skill_prompts'].keys():
                    raise SkillMissingError

        await self.get_internals(project_has_labels, overwrite_internals, overwrite_prompts)
        
        self.get_documents_df(overwrite_documents)
        self.get_indices(overwrite_indices)

        self.rqs = await self.get_research_question_answers(
            rq_path=f"{self.folder_name}/skills/research_questions/", 
            top_n=top_n, overwrite_rqs=overwrite_rqs
        )

        self.run_df = await self.run_skill_chain(
            skills=skills, 
            num_samples=samples, 
            overwrite_skills=overwrite_skills,
            write_master_json=True, 
            file_name=self.folder_name+'/completions.json'
        )

        return self.internals, self.run_df, self.rqs


        # if not os.path.exists(f"{output_folder_name}/prompts.json") or overwrite_prompts:

        #     self.prompts['skill_prompts'] = build_advanced_skills(
        #         build_skills(self.prompts['skill_prompts'], context['agent_internals'])
        #     )

        #     print("writing prompts")
        #     with open(f"{output_folder_name}/prompts.json", 'w') as outF:
        #         json.dump(self.prompts, outF)


        # print("reading prompts")
        # prompts = json.load(open(f"{output_folder_name}/prompts.json"))



# chunker = SemanticChunker(
#     VoyageAIEmbeddings(
#         voyage_api_key=VOYAGE_API_KEY, model="voyage-large-2-instruct"
#     ),
#     breakpoint_threshold_type="percentile"
# )


# @app.get("/") 
# async def skillchain():   

#     skillchain = SolwaySkillChain(
#         oai_async_client, vo, chunker,
#         copy.deepcopy(solway_pipeline.prompts.prompts),
#         folder_name #"Sub-project #1 (Existing Practice Review)",
       
#     )

#     await skillchain()
#   return {}