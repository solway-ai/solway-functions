import io
import os
import re
import json

from pathlib import Path

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


def parse_pdf(stream) -> dict:
    """
        parses a pdf
        returns a dictionary where each key is a page number, and each value is a dictionary containing the pages raw text
        and the number of tokens
    """
    pdf_text = {}
    with io.BytesIO(stream) as f:
        reader = PdfReader(f)
        for page_num in range(len(reader.pages)):
            page_text = clean_text(reader.pages[page_num].extract_text())
            pdf_text[page_num+1] = {
                "textIN": page_text,
                "numTokens": num_tokens_from_string(page_text)
            }
            
    return pdf_text


def parse_files(raw_files:dict) -> dict:
    """
        parses each file in the raw_files dictionary
    """
    processed_files = {}
    for file_name, stream in raw_files.items():
        ext = get_file_extension(file_name)
        if ext:
            if ext == 'pdf':
                processed_files[get_file_name(file_name)] = parse_pdf(stream)

            elif ext == 'json':
                processed_files[get_file_name(file_name)] = json.loads(stream)
            else:
                pass
        else:
            raise Exception

    return processed_files




