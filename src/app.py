import sys
import os
from pathlib import Path

# Add the workspace root to sys.path to enable absolute imports of src.*
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import chromadb
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

from src.generate import generate_answer

# Load environment variables
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# App configurations
st.set_page_config(
    page_title="Yale Dining Assistant",
    page_icon="🍔",
    layout="wide"
)

# Premium UI CSS styling
st.markdown("""
    <style>
        .main-header {
            font-size: 2.8rem;
            color: #0A2240;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.2rem;
            color: #5C768D;
            margin-bottom: 2rem;
        }
        .source-card {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            background-color: #F8FAFC;
        }
        .source-title {
            font-weight: 600;
            color: #1E293B;
        }
        .source-meta {
            font-size: 0.85rem;
            color: #64748B;
        }
        .distance-badge {
            background-color: #E2E8F0;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

# 1. Cached resources initialization (SentenceTransformer and ChromaDB)
@st.cache_resource
def get_resources():
    db_dir = "data/chroma_db"
    collection_name = "yale_dining_guide"
    
    # Init ChromaDB
    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_collection(name=collection_name)
    
    # Init SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Init Groq Client
    groq_client = Groq(api_key=GROQ_API_KEY)
    
    return collection, model, groq_client

try:
    if not GROQ_API_KEY:
        st.error("Error: `GROQ_API_KEY` not found. Please ensure it is set in your `.env` file.")
        st.stop()
    collection, embed_model, groq_client = get_resources()
except Exception as e:
    st.error(f"Failed to initialize components: {e}")
    st.info("Did you run `embed_and_index.py` first to populate ChromaDB?")
    st.stop()

# 2. Sidebar setup with system instructions and evaluation questions
st.sidebar.markdown("<h3 style='color:#0A2240;'>Yale Dining Assistant</h3>", unsafe_allow_html=True)
st.sidebar.write("This tool uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions about Yale dining. All answers are strictly grounded in official sources and student culture articles.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Evaluation Questions**")
st.sidebar.write("Click any question below to test retrieval and grounded generation:")

eval_questions = [
    "How many residential dining halls does Yale describe as part of its dining system?",
    "What does the Full meal plan include for undergraduate students?",
    "Which meal plan is designed for off-campus undergraduate students, and what does it include?",
    "What makes Berkeley dining distinctive according to Yale Hospitality?",
    "What does the project corpus say about wait times at Yale dining halls?"
]

# Set query text in session state if user clicks a preset question
if "query_input" not in st.session_state:
    st.session_state.query_input = ""

def set_query(q):
    st.session_state.query_input = q

for idx, q in enumerate(eval_questions, 1):
    st.sidebar.button(f"Q{idx}: {q[:55]}...", key=f"q_btn_{idx}", on_click=set_query, args=(q,))

st.sidebar.markdown("---")
st.sidebar.caption("System Stack: sentence-transformers/all-MiniLM-L6-v2 | ChromaDB | Groq (llama-3.3-70b-versatile)")

# 3. Main Interface Layout
st.markdown("<div class='main-header'>Yale Campus Dining Assistant</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Grounded semantic search & AI assistance for residential dining, schedules, meal plans, and accommodations.</div>", unsafe_allow_html=True)

query = st.text_input("Ask a question about Yale Dining:", value=st.session_state.query_input, key="search_bar", placeholder="e.g., What is Berkeley's Thunder Brunch?")

# If there is a query, execute the RAG pipeline
if query:
    st.markdown("### Answer")
    with st.spinner("Retrieving sources and generating grounded answer..."):
        answer, sources = generate_answer(query, collection, embed_model, groq_client)
        
    st.markdown(answer)
    
    # 4. Citations & Sources UI
    st.markdown("---")
    with st.expander("🔍 View Retrieved Sources & Distance Scores", expanded=False):
        st.write("The following passages were retrieved from the vector database to build the response:")
        
        # Display the sources in columns or cards
        for rank, res in enumerate(sources, 1):
            meta = res["metadata"]
            dist = res["distance"]
            
            st.markdown(f"""
                <div class='source-card'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span class='source-title'>Rank {rank}: {meta['title']}</span>
                        <span class='distance-badge'>Distance: {dist:.4f}</span>
                    </div>
                    <div class='source-meta'>URL: <a href='{meta['url']}' target='_blank'>{meta['url']}</a></div>
                    <div style='margin-top: 8px; font-size: 0.9rem; color: #334155; line-height: 1.5; font-style: italic;'>
                        "{res['document']}"
                    </div>
                </div>
            """, unsafe_allow_html=True)
