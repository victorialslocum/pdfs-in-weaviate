import weaviate
from weaviate.agents.query import QueryAgent
from weaviate.classes.init import Auth
import os
from dotenv import load_dotenv

load_dotenv()

weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
)

qa = QueryAgent(
    client=client, collections=["ArxivPDFs", "PDFchunks1"]
)

response = qa.ask("What are some common themes in machine learning over the last decade?")
print("sources: ", response.sources)
print("final answer: ", response.final_answer)