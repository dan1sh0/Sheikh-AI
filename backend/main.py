import os
from typing import List, Dict, Optional
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import json
from dotenv import load_dotenv
import requests
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load environment variables
load_dotenv()

print(f"OpenAI API Key loaded: {os.getenv('OPENAI_API_KEY')[:10]}...")  # Only print first 10 chars for security
print(f"Hadith API Key loaded: {os.getenv('HADITH_API_KEY')[:10]}...")

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware with more specific settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IslamicChatbot:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = None
        self.qa_chain = None
        
        # Initialize the text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Add conversation history
        self.conversation_history = []
        self.max_history = 5  # Keep last 5 exchanges
        
        # Update prompt template to require full citations
        self.prompt_template = """You are a knowledgeable Islamic chatbot that provides accurate information from both the Quran and Hadith.

Guidelines:
1. Always structure your response in this exact format:

   [Summary]
   Brief overview of the topic and main points (2-3 sentences)

   ---Quranic Verses---
   
   Verse:
   
   [Insert Arabic text here, right-aligned]
   
   English: [Insert English translation here]
   
   Source: (Quran Surah:Ayah)

   ---Hadiths---
   
   Hadith:
   
   [Insert Arabic text here, right-aligned]
   
   English: [Insert English translation here]
   
   Narrator: [Insert narrator name here]
   Source: [Insert collection name, book/volume number, hadith number] (Grade: [Sahih/Hasan])

   [Conclusion]
   Detailed explanation or additional context about the verses and hadiths (2-3 sentences)

2. Always keep Arabic text:
   - On its own line
   - Right-aligned
   - Separated from English text
3. For verses mentioning Allah, add "Subhanahu wa Ta'ala (Glory be to Him)"
4. For mentions of Prophet Muhammad, add "ﷺ (peace be upon him)"

Context: {context}
Question: {question}

Answer: """
        
    def fetch_all_hadiths(self, collection: str, api_key: str, max_retries: int, retry_delay: int) -> List[str]:
        """Helper function to fetch all hadiths from a collection with pagination"""
        documents = []
        page = 1
        per_page = 25  # Default pagination value per API docs
        
        while True:
            for attempt in range(max_retries):
                try:
                    print(f"Processing {collection} - Page {page}...")
                    
                    # Construct API URL with parameters
                    params = {
                        'apiKey': api_key,
                        'book': collection,
                        'status': 'sahih,hasan',  # Only fetch authentic hadiths
                        'paginate': per_page,
                        'page': page
                    }
                    
                    response = requests.get(
                        "https://www.hadithapi.com/public/api/hadiths",
                        params=params,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Debug the response structure
                        print(f"Response status: {data.get('status', 'N/A')}")
                        print(f"Response message: {data.get('message', 'N/A')}")
                        
                        # Get hadiths from the response
                        hadiths = data.get('hadiths', [])
                        
                        if not hadiths:
                            print(f"No more hadiths found for {collection}")
                            return documents
                        
                        for hadith in hadiths:
                            # Extract hadith details
                            hadith_number = hadith.get('hadithNumber', 'N/A')
                            chapter = hadith.get('chapter', 'N/A')
                            status = hadith.get('status', '').lower()
                            arabic = hadith.get('hadithArabic', '')
                            english = hadith.get('hadithEnglish', '')
                            
                            # Format the hadith text
                            text = (
                                f"Hadith: {collection}\n"
                                f"Grade: {status.upper()}\n"
                                f"Number: {hadith_number}\n"
                                f"Chapter: {chapter}\n"
                                f"Arabic: {arabic}\n"
                                f"English: {english}"
                            )
                            documents.append(text)
                            print(f"Added {collection} hadith #{hadith_number}")
                        
                        # Move to next page
                        page += 1
                        # Add delay between pages
                        time.sleep(1)
                        break
                        
                    elif response.status_code == 401:
                        print("Error: Invalid API key")
                        return documents
                    elif response.status_code == 403:
                        print("Error: API key required")
                        return documents
                    elif response.status_code == 404:
                        print(f"Error: Book {collection} not found")
                        return documents
                    else:
                        print(f"Error: Unexpected status code {response.status_code}")
                        print("Response:", response.text)
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return documents
                        
                except Exception as e:
                    print(f"Error processing {collection} page {page}:")
                    print(f"Exception type: {type(e)}")
                    print(f"Exception message: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return documents

    def load_data(self) -> None:
        """Load and process both Quran and Hadith data from APIs"""
        documents = []
        max_retries = 3
        retry_delay = 2
        
        try:
            # 1. Fetch Quran data (keeping existing code)
            print("\nFetching Quran data...")
            total_surahs = 114
            
            for surah in range(1, total_surahs + 1):
                for attempt in range(max_retries):
                    try:
                        print(f"Processing Surah {surah}/114...")
                        response = requests.get(
                            f"http://api.alquran.cloud/v1/surah/{surah}/editions/quran-uthmani,en.asad",
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            for ayah_idx, ayah in enumerate(data['data'][0]['ayahs'], 1):
                                arabic_text = ayah['text']
                                english_text = data['data'][1]['ayahs'][ayah_idx-1]['text']
                                text = (
                                    f"Quran {surah}:{ayah_idx}\n"
                                    f"Arabic: {arabic_text}\n"
                                    f"English: {english_text}"
                                )
                                documents.append(text)
                            break  # Success, move to next surah
                        else:
                            print(f"Error fetching Surah {surah}: Status code {response.status_code}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                continue
                            
                    except requests.exceptions.RequestException as e:
                        print(f"Network error processing Surah {surah}: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
            
            print(f"\nSuccessfully processed {len(documents)} Quran verses!")
            
            # 2. Fetch Hadith data
            print("\nFetching Hadith data...")
            hadith_api_key = os.getenv('HADITH_API_KEY')
            if not hadith_api_key:
                print("Error: HADITH_API_KEY not found in environment variables")
                return
            
            # Add this debug line at the start of hadith fetching
            print(f"Using API key: {hadith_api_key[:10]}...")  # Only print first 10 chars for security
            
            # Using correct book slugs from API documentation
            collections = ['sahih-bukhari', 'sahih-muslim']
            for collection in collections:
                print(f"\nFetching complete {collection} collection...")
                
                # Update the API request
                url = "https://www.hadithapi.com/api/hadiths"
                params = {
                    'apiKey': hadith_api_key,
                    'book': collection,  # Changed back to 'book' instead of 'bookSlug'
                    'status': 'sahih'  # Simplified to just sahih for testing
                }
                
                # Add API key to URL as well (some APIs require both)
                if '?' not in url:
                    url = f"{url}?apiKey={hadith_api_key}"
                
                response = requests.get(
                    url,
                    params=params,
                    timeout=10,
                    headers={
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Get hadiths from the nested structure
                        hadiths_data = data.get('hadiths', {})
                        hadiths = hadiths_data.get('data', [])
                        current_page = hadiths_data.get('current_page', 1)
                        
                        if not hadiths:
                            print(f"No hadiths found for {collection}")
                            continue
                        
                        print(f"Found {len(hadiths)} hadiths on page {current_page}")
                        
                        for hadith in hadiths:
                            try:
                                # Extract book information
                                book_info = hadith.get('book', {})
                                book_name = book_info.get('bookName', collection)
                                writer_name = book_info.get('writerName', 'N/A')
                                
                                # Extract chapter information
                                chapter_info = hadith.get('chapter', {})
                                chapter_number = chapter_info.get('chapterNumber', 'N/A')
                                chapter_english = chapter_info.get('chapterEnglish', 'N/A')
                                chapter_arabic = chapter_info.get('chapterArabic', 'N/A')
                                
                                # Extract hadith details
                                text = (
                                    f"Hadith: {book_name}\n"
                                    f"Writer: {writer_name}\n"
                                    f"Grade: {hadith.get('status', 'N/A')}\n"
                                    f"Volume: {hadith.get('volume', 'N/A')}\n"
                                    f"Number: {hadith.get('hadithNumber', 'N/A')}\n"
                                    f"Chapter: {chapter_number} - {chapter_english}\n"
                                    f"Chapter (Arabic): {chapter_arabic}\n"
                                    f"Heading: {hadith.get('headingEnglish', '')}\n"
                                    f"Heading (Arabic): {hadith.get('headingArabic', '')}\n"
                                    f"Narrator: {hadith.get('englishNarrator', '')}\n"
                                    f"Arabic: {hadith.get('hadithArabic', '')}\n"
                                    f"English: {hadith.get('hadithEnglish', '')}\n"
                                    f"Reference: {book_name} Volume {hadith.get('volume', 'N/A')}, Hadith {hadith.get('hadithNumber', 'N/A')}"
                                )
                                documents.append(text)
                                print(f"Added {book_name} hadith #{hadith.get('hadithNumber', 'N/A')}")
                            
                            except Exception as e:
                                print(f"Error processing hadith: {str(e)}")
                                continue
                        
                        print(f"Completed page {current_page} of {collection}: {len(hadiths)} hadiths fetched")
                    
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
                        print("Response content:", response.text)
                        continue
                    
                elif response.status_code == 401:
                    print("Error: Invalid API key")
                    continue
                elif response.status_code == 403:
                    print("Error: API key required")
                    continue
                elif response.status_code == 404:
                    print(f"Error: Collection {collection} not found")
                    continue
                else:
                    print(f"Error: Unexpected status code {response.status_code}")
                    print("Response:", response.text)
                    continue
            
            print(f"\nTotal documents processed: {len(documents)}")
            
            # Create vector store (keeping existing code)
            try:
                print("\nCreating vector embeddings...")
                texts = self.text_splitter.create_documents(documents)
                self.vector_store = Chroma.from_documents(
                    documents=texts,
                    embedding=self.embeddings,
                    persist_directory="./data/chroma_db"
                )
                print("Vector store created successfully!")
                
            except Exception as e:
                print(f"Error creating vector store: {str(e)}")
                raise
            
        except Exception as e:
            print(f"Error processing data: {str(e)}")
            raise

    def setup_qa_chain(self) -> None:
        """Initialize the QA chain with custom prompt"""
        prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question"]
        )
        
        # Initialize ChatOpenAI with GPT-3.5-turbo
        llm = ChatOpenAI(
            temperature=0.2,
            model_name="gpt-3.5-turbo"
        )
        
        # Create the QA chain with simplified configuration
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(
                search_kwargs={"k": 10}
            ),
            chain_type_kwargs={
                "prompt": prompt
            }
        )
        
    def answer_question(self, question: str) -> Dict[str, str]:
        """Process a user question and return an answer with references"""
        if not self.qa_chain:
            return {
                "error": "QA chain not initialized. Please call setup_qa_chain() first.",
                "status": "error"
            }
            
        try:
            # Add basic input validation
            if not question.strip():
                return {
                    "error": "Please provide a valid question.",
                    "status": "error"
                }
            
            # Run the query with simplified input format
            response = self.qa_chain.invoke({
                "query": question
            })
            
            # Extract the answer from the response
            answer = response['result'] if isinstance(response, dict) else str(response)
            
            # Basic response validation
            if not answer or len(answer.strip()) < 10:
                return {
                    "error": "Generated response was invalid or too short.",
                    "status": "error"
                }
            
            return {
                "answer": answer,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "error": f"An error occurred: {str(e)}",
                "status": "error"
            }

# Initialize chatbot
chatbot = IslamicChatbot()

# Load data and setup chain on startup
@app.on_event("startup")
async def startup_event():
    try:
        chatbot.load_data()
        chatbot.setup_qa_chain()
        print("Islamic chatbot initialized successfully!")
    except Exception as e:
        print(f"Error initializing chatbot: {str(e)}")

class QuestionRequest(BaseModel):
    question: str

@app.post("/api/chat")
async def chat(request: QuestionRequest):
    try:
        response = chatbot.answer_question(request.question)
        if response.get("status") == "success":
            return {"answer": response["answer"]}
        else:
            raise HTTPException(status_code=400, detail=response.get("error"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="127.0.0.1",
        port=8000,
        reload=True  # Enable auto-reload for development
    )    