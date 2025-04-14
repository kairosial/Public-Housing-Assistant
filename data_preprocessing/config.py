import pymupdf4llm
import pandas as pd
import re
import os, time
from io import StringIO
from llama_index.core.schema import Document
from bs4 import BeautifulSoup
from openai import AzureOpenAI
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from glob import glob

# 🔑 .env 로드
load_dotenv()
embedding_api_key = os.getenv("Embedding_API_KEY")
embedding_endpoint = os.getenv("Embedding_ENDPOINT")
gpt_api_key = os.getenv('OPENAI_API_KEY')
gpt_endpoint = os.getenv('OPENAI_ENDPOINT')
BLOB_CONN_STR = os.getenv('BLOB_CONN_STR')
DI_ENDPOINT = os.getenv('DI_ENDPOINT')
DI_API_KEY = os.getenv('DI_API_KEY')

# 📁 경로 설정
BLOB_CONTAINER_NAME = "pdf-container"
# PDF_FOLDER = r"E:\work\MS_project_2\code\테이블처리o\data\pdfs/d"
# MD_FOLDER = r"E:\work\MS_project_2\code\테이블처리o\data\markdowns"
PDF_FOLDER = r".\data\pdf"
MD_FOLDER = r".\data\markdown"
TXT_FOLDER = r".\data\text"
os.makedirs(MD_FOLDER, exist_ok=True)

# ✅ 클라이언트 초기화
blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
container_client = blob_service.get_container_client(BLOB_CONTAINER_NAME)
if not container_client.exists():
    container_client.create_container()

di_client = DocumentIntelligenceClient(endpoint=DI_ENDPOINT, credential=AzureKeyCredential(DI_API_KEY))

# pymu
special_chars = ['•', '■', '※']
