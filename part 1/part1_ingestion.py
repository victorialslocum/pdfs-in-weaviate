import arxiv
import os
from PyPDF2 import PdfReader
from typing import List
import re
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.init import Auth
from dotenv import load_dotenv

load_dotenv()

weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]


def download_papers(query="machine learning", max_results=25, download_dir="pdfs"):
    """
    Downloads a subset of papers from arXiv.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    client = arxiv.Client()
    search = arxiv.Search(
        query = query,
        max_results = max_results,
        sort_by = arxiv.SortCriterion.Relevance
    )

    downloaded_files = []
    print(f"Downloading {max_results} papers for query '{query}'...")
    
    
    for result in client.results(search):
        # Clean filename to avoid issues
        filename = f"{result.entry_id.split('/')[-1]}.pdf"
        file_path = os.path.join(download_dir, filename)
        
        if not os.path.exists(file_path):
            result.download_pdf(dirpath=download_dir, filename=filename)
            print(f"Downloaded: {result.title}")
        else:
            print(f"Already exists: {result.title}")

        result_obj = {"title": result.title, "abstract": result.summary, "pdf_url": result.pdf_url, "date": str(result.updated), "authors": ", ".join([author.name for author in result.authors]), "file_path": file_path}    
        downloaded_files.append(result_obj)
        
    return downloaded_files

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using PyPDF2.
    """
    text = ""
    try:
        reader = PdfReader(pdf_path)
        # Extract text from the first few pages to avoid massive output
        num_pages = min(len(reader.pages), 3) 
        for i in range(num_pages):
            page = reader.pages[i]
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None
        
    return text


def chunk_text(text, doc_id, chunk_size=250, overlap_fraction=0.2):
    """
    Uses fixed size chunking with overlap to chunk raw PDF text. Returns a list of chunk objects (doc_id, chunk_id, text).
    """
    text = re.sub(r"\s+", " ", text)  # Replace multiple whitespces
    text_words = re.split(r"\s", text)  # Split by single whitespace

    overlap_int = int(chunk_size * overlap_fraction)
    chunks = []
    for i in range(0, len(text_words), chunk_size):
        chunk_words = text_words[max(i - overlap_int, 0): i + chunk_size]
        chunk = " ".join(chunk_words)
        chunks.append({"chunk_id": i, "doc_id": doc_id, "chunk_text": chunk})

    return chunks

def main():
    # 1. Download PDFs
    pdf_files = download_papers()

    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),
    )

    if not client.collections.exists("PDFchunks1"):
        client.collections.create(
            "PDFchunks1",
            description="A dataset that contains all the chunks of the PDFs (fixed size, overlap). The doc_id is the UUID of the PDF it belongs to in the ArxivPDFs collection.",
            vector_config=Configure.Vectors.text2vec_weaviate(),
            properties=[
                Property(name="chunk_id", description="The chunk id of the chunk", data_type=DataType.INT, skip_vectorization=True),
                Property(name="doc_id", description="The UUID of the PDF it belongs to in the ArxivPDFs collection", data_type=DataType.UUID, skip_vectorization=True),
                Property(name="chunk_text", description="The text of the chunk", data_type=DataType.TEXT),
            ],
        )
    
    if not client.collections.exists("ArxivPDFs"):
        client.collections.create(
            "ArxivPDFs",
            description="A dataset that contains all the PDFs downloaded from arXiv.",
            properties=[
                Property(name="title", description="The title of the PDF", data_type=DataType.TEXT),
                Property(name="abstract", description="The abstract of the PDF", data_type=DataType.TEXT),
                Property(name="pdf_url", description="The URL of the PDF", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="date", description="The date of the PDF", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="authors", description="The authors of the PDF", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="file_path", description="The file path of the PDF", data_type=DataType.TEXT, skip_vectorization=True),
            ],
        )

    chunks_collection = client.collections.use("PDFchunks1")
    pdfs_collection = client.collections.use("ArxivPDFs")

    print("\n--- Extracting Text ---\n")

    # 2. Extract Text
    for pdf_file in pdf_files:
        
        print(f"Processing: {pdf_file['file_path']}")
        content = extract_text_from_pdf(pdf_file["file_path"])
        
        if content:
            pdf_file["content"] = content

            doc_uuid = pdfs_collection.data.insert({
                "title": pdf_file["title"],
                "abstract": pdf_file["abstract"],
                "pdf_url": pdf_file["pdf_url"],
                "date": pdf_file["date"],
                "authors": pdf_file["authors"],
                "file_path": pdf_file["file_path"],
            })

            print(doc_uuid, " inserted")
            
            chunks = chunk_text(pdf_file["content"], doc_uuid)
            error_threshold = 10  # Max errors before aborting
            with chunks_collection.batch.fixed_size(batch_size=100) as batch:
                for obj in chunks:
                    batch.add_object(properties=obj)

                    if batch.number_errors > error_threshold:
                        print("Too many errors, aborting batch import")
                        break

            if chunks_collection.batch.failed_objects:
                for failed in chunks_collection.batch.failed_objects[:3]:
                    print(f"Error: {failed.message} for object: {failed.object_}")

            print(i, " chunks inserted")


    print("\n--- Ingestion Complete ---\n")
    client.close()


if __name__ == "__main__":
    main()
