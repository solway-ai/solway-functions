import io
import os
import re

from pathlib import Path

import tempfile
#import textract
from pypdf import PdfReader

import tiktoken


def get_file_extension(filename):
    """ stable function to extract a file's extension """
    extension = Path(filename).suffix
    return extension[1:] if extension else None


def get_file_name(path):
    """ gets the last subsection of a string that follows the trailing / character"""
    return Path(path).name


def normalize_path(raw_parent:str, raw_child:str):
    """
    """
    path = '/%s/%s' % (raw_parent, raw_child.replace(os.path.sep, '/'))
    while '//' in path:
        path = path.replace('//', '/')
    return path.rstrip('/')


def num_tokens_from_string(string:str, encoding_name:str='cl100k_base') -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def clean_text(text):
    """" Strips redundant whitespace characters """
    stripped_text = re.sub(r'\s+', ' ', text).strip()
    return re.sub(r'[^\w\s,.!?\'"()\-:;]', '',stripped_text)


def parse_pdf(response_content) -> dict:
    """
        parses a pdf
        returns a dictionary where each key is a page number, and each value is a dictionary containing the pages raw text
        and the number of tokens
    """
    pdf_text = {}
    with io.BytesIO(response_content) as f:
        reader = PdfReader(f)
        for page_num in range(len(reader.pages)):
            page_text = clean_text(reader.pages[page_num].extract_text())
            pdf_text[page_num+1] = {
                "textIN": page_text,
                "numTokens": num_tokens_from_string(page_text)
            }
            
    return pdf_text


# def parse_docx(response_content:str) -> dict:
#     """
#         parses doc or docx file
#     """
#     with io.BytesIO(response_content) as f:

#         with tempfile.NamedTemporaryFile(suffix='.docx') as temp_docx:
#             # Write the byte content to the temporary file
#             temp_docx.write(f.getbuffer())
#             temp_docx.seek(0)  # Seek back to the beginning of the file
            
#             text = textract.process(temp_docx.name)
#             text = text.decode('utf-8')
#             text = clean_text(text)

#     return {
#         "textIN": text,
#         "numTokens": num_tokens_from_string(text)
#     }


def parse_files(raw_files:dict) -> dict:
    """
        parses each file in the raw_files dictionary
    """
    processed_files = {}
    for file_name, response in raw_files.items():
        ext = get_file_extension(file_name)
        if ext:
            if ext == 'pdf':
                processed_files[get_file_name(file_name)] = parse_pdf(response)
            # elif 'doc' in ext:
            #     processed_files[get_file_name(file_name)] = parse_docx(response)
            # elif ext == 'mp4':
            #     pass
            # elif ext == 'xlsx':
            #     processed_files[get_file_name(file_name)] = parse_xlsx(response)
            else:
                pass
        else:
            raise Exception

    return processed_files


# def create_folder(folder_name):
#     """ creates a sub directory in the project"""
#     # Get the current working directory
#     current_dir = os.getcwd()
    
#     # Define the new folder path
#     new_folder_path = os.path.join(current_dir, folder_name)
    
#     try:
#         # Create the new folder
#         os.makedirs(new_folder_path)
#         print(f"Folder '{folder_name}' created successfully at {new_folder_path}")
#     except FileExistsError:
#         print(f"Folder '{folder_name}' already exists at {new_folder_path}")
#     except Exception as e:
#         print(f"An error occurred: {e}")


# def parse_xlsx(response_content) -> dict:
#     """
#     loops through each sheet in an excel file
#     creates a dictionary for each sheet where each column is a key,
#     and the dictionary values are the columns rows in list format
#     """
#     with io.BytesIO(response_content) as f:

#         xls = pd.ExcelFile(f)
#         sheets_texts = {}

#         for sheet_name in xls.sheet_names:
#             column_texts = {}
#             df = pd.read_excel(f, sheet_name=sheet_name, engine='openpyxl')
#             for column in df.columns:
#                 texts = []
#                 for index, item in df[column].items():
#                     if isinstance(item, str):
#                         texts.append((index, clean_text(item)))

#                 column_texts[clean_text(column)] = texts
            
#             sheets_texts[sheet_name] = column_texts

#     return sheets_texts


# def download_dropbox_folder(dbx:dropbox.Dropbox, folder_path, files_downloaded=None):
#     """
#     downloads the files within a dropbox folder
#     """
#     if files_downloaded is None:
#         files_downloaded = {}
    
#     path = normalize_path(folder_path, "/")
    
#     try:
#         for entry in dbx.files_list_folder(path).entries:
#             if isinstance(entry, FileMetadata):  
#                 _, response = dbx.files_download(entry.id)
#                 files_downloaded[entry.path_display] = response.content

#             elif isinstance(entry, FolderMetadata): 
#                 subfolder_path = normalize_path(folder_path, entry.name)
#                 download_dropbox_folder(dbx, subfolder_path, files_downloaded)

#     except ApiError as err:
#         print(f'API error: {err}')
#         print(dbx.files_list_folder(path).entries)

#     except Exception as e:
#         print(f'Unexpected Error: {e}')

#     return files_downloaded


# import dropbox

# from dropbox.files import (
#     FileMetadata,
#     FolderMetadata
# )

# from dropbox.exceptions import ApiError
# import pandas as pd
