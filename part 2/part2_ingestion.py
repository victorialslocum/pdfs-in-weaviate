import arxiv
import os
from typing import List
import re
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.init import Auth
from dotenv import load_dotenv
from docling.document_converter import DocumentConverter


load_dotenv()

weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]


def download_papers(query="vector database", max_results=5, download_dir="pdfs"):
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
    Extracts text from a PDF file using Docling.
    """
    text = ""
    try:
        converter = DocumentConverter()
        doc = converter.convert(pdf_path).document

        text = doc.export_to_markdown()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None
    print(text)    
    return text


def chunk_text(text, doc_id, chunk_size=250, overlap_fraction=0.2):
    """
    Uses markdown document-based chunking to chunk raw PDF text. Returns a list of chunk objects (doc_id, chunk_id, text).
    """
    # Normalize newlines
    text = text.replace('\r\n', '\n')
    
    # Split by headers (H1, H2, H3)
    # Iterate line by line to identify headers and group content
    lines = text.split('\n')
    
    sections = []
    current_section = []
    
    for line in lines:
        # Check for headers (e.g., "# Header", "## Header")
        if re.match(r'^#{1,3}\s', line):
            # If we have a current section accumulating, save it
            if current_section:
                sections.append("\n".join(current_section))
            # Start a new section with the header line
            current_section = [line]
        else:
            current_section.append(line)
            
    # Append the last section
    if current_section:
        sections.append("\n".join(current_section))
        
    chunks = []
    chunk_counter = 0
    
    for section in sections:
        section_text = section.strip()
        if not section_text:
            continue

        # Split section into words for size checking
        # Using simple whitespace splitting as in the original function
        section_words = re.split(r'\s+', section_text)
        
        if len(section_words) <= chunk_size:
            # If section fits in one chunk, add it
            chunks.append({
                "chunk_id": chunk_counter,
                "doc_id": doc_id,
                "chunk_text": section_text
            })
            chunk_counter += 1
        else:
            # If section is too big, split it with overlap
            overlap_int = int(chunk_size * overlap_fraction)
            for i in range(0, len(section_words), chunk_size - overlap_int):
                chunk_words = section_words[i : i + chunk_size]
                if not chunk_words:
                    break
                
                # Reconstruct text for this chunk
                chunk_text_sub = " ".join(chunk_words)
                chunks.append({
                    "chunk_id": chunk_counter,
                    "doc_id": doc_id,
                    "chunk_text": chunk_text_sub
                })
                chunk_counter += 1

    return chunks

def main():
    # 1. Download PDFs
    pdf_files = download_papers()

    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),
    )

    if not client.collections.exists("PDFchunks2"):
        client.collections.create(
            "PDFchunks2",
            description="A dataset that contains all the chunks of the PDFs (markdown document-based chunking). The doc_id is the UUID of the PDF it belongs to in the ArxivPDFs collection.",
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

    chunks_collection = client.collections.use("PDFchunks2")
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
