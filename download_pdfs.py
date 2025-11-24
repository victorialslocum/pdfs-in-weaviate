import os
import arxiv

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

if __name__ == "__main__":
    download_papers()
