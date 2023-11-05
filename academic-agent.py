import os
from dotenv import load_dotenv
import json
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
import streamlit as st
from pydantic import BaseModel
from typing import Optional
import fitz 
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI

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
    try:
        # Send a GET request to the PDF URL
        response = requests.get(pdf_url)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Get the PDF content
            pdf_content = response.content
            
            # Extract the filename from the URL and ensure it ends with .pdf
            local_filename = pdf_url.split('/')[-1]
            if not local_filename.lower().endswith('.pdf'):
                local_filename += '.pdf'
            
            # Ensure the filename is valid and does not contain invalid characters
            local_filename = "".join(i for i in local_filename if i not in r'\/:*?"<>|')
            
            # Save the PDF to a file
            with open(local_filename, 'wb') as pdf_file:
                pdf_file.write(pdf_content)
            
            # Return the local filename where the PDF was saved
            return local_filename
        else:
            print(f"Failed to download the PDF: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        print(f"An error occurred while downloading the PDF: {e}")
        return None

# Define a function to extract text from the PDF
def extract_text_from_pdf(pdf_path: str) -> str:
    # Open the PDF file
    with fitz.open(pdf_path) as pdf:
        text = ""
        # Iterate over each page in the PDF
        for page in pdf:
            # Extract text from the page and add it to the text variable
            text += page.get_text()
    
    return text

# Define a function to summarize the text
def summarize_text(text: str) -> str:
    # Implement the logic to summarize the text
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k-0613")

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n"], chunk_size=10000, chunk_overlap=500)
    
    docs = text_splitter.create_documents([text])
    
    map_prompt = """
    Write a summary of the following text:
    "{text}"
    SUMMARY:
    """
    
    map_prompt_template = PromptTemplate(
        template=map_prompt, input_variables=["text"])

    summary_chain = load_summarize_chain(
        llm=llm,
        chain_type='map_reduce',
        map_prompt=map_prompt_template,
        combine_prompt=map_prompt_template,
        verbose=True
    )

    output = summary_chain.run(input_documents=docs)
    return output

# Define the endpoint for the research agent
@app.post("/research")
def research_agent(query: ResearchQuery):
    # Use the functions defined above to perform the research task
    pdf_url = search_paper(query.paper_title)
    print("Url: ", pdf_url)
    if pdf_url:
        pdf_content = download_pdf(pdf_url)
        print("PDF content: ", pdf_content)
        if pdf_content:
            text = extract_text_from_pdf(pdf_content)
            print("Text: ", text)
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