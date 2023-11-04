import os
from dotenv import load_dotenv
import json
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
import streamlit as st
from pydantic import BaseModel
from typing import Optional


# Load environment variables
load_dotenv()

# API keys
browserless_api_key = os.getenv("BROWSERLESS_API_KEY")
serp_api_key = os.getenv("SERP_API_KEY")

# Define your FastAPI app
app = FastAPI()

# Define a Pydantic model for the input data
class ResearchQuery(BaseModel):
    paper_title: str

# Define a function to search for the research paper
def search_paper(paper_title: str) -> Optional[str]:
    url = "https://google.serper.dev/search"
    query = f"{paper_title} filetype:pdf"

    payload = json.dumps({
        "q": query
    })

    headers = {
        'X-API-KEY': serp_api_key,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        search_results = response.json()
        for result in search_results.get('organic', []):
            title = result.get('title', '').lower()
            link = result.get('link', '').lower()
            # Check if the title suggests it's a PDF or if the link ends with .pdf
            if 'pdf' in title or link.endswith('.pdf'):
                return result['link']
        print("No direct PDF link found in the search results.")
    else:
        print(f"Search request failed with status code: {response.status_code}")

    return None

# Define a function to download the PDF
def download_pdf(pdf_url: str) -> Optional[str]:
    # Implement the logic to download the PDF and return its content
    pass

# Define a function to extract text from the PDF
def extract_text_from_pdf(pdf_content: str) -> str:
    # Implement the logic to extract text from the PDF content
    pass

# Define a function to summarize the text
def summarize_text(text: str) -> str:
    # Implement the logic to summarize the text
    pass

# Define the endpoint for the research agent
@app.post("/research")
def research_agent(query: ResearchQuery):
    # Use the functions defined above to perform the research task
    pdf_url = search_paper(query.paper_title)
    print("Url: ", pdf_url)
    if pdf_url:
        pdf_content = download_pdf(pdf_url)
        if pdf_content:
            text = extract_text_from_pdf(pdf_content)
            summary = summarize_text(text)
            return {"summary": summary}
    return {"error": "Research paper not found or could not be processed."}

# Streamlit web app function
def main():
    st.title("AI Research Agent")
    paper_title = st.text_input("Enter the title of the research paper you're looking for:")
    if paper_title:
        response = research_agent(ResearchQuery(paper_title=paper_title))
        if 'summary' in response:
            st.subheader("Summary")
            st.write(response['summary'])
        else:
            st.error("Could not find or process the requested research paper.")

if __name__ == '__main__':
    main()