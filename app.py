#!/usr/bin/env python3
"""
FloatChat RAG - Streamlit Web Interface with LangChain

A web-based chat interface to explore Argo oceanographic float data using AI.
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore
from sqlalchemy import create_engine, text
import pandas as pd
import json

# Page config
st.set_page_config(
    page_title="FloatChat RAG",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #64748b;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .tool-badge {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.25rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


# Initialize components
@st.cache_resource
def init_components():
    """Initialize database connections and embedder"""
    try:
        # Disable ChromaDB telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        embedder = ArgoMetadataEmbedder()
        chroma_store = ArgoChromaStore()
        db_engine = create_engine("sqlite:///data/databases/argo_data.db")
        
        return embedder, chroma_store, db_engine
    except Exception as e:
        st.error(f"Failed to initialize components: {e}")
        st.stop()


embedder, chroma_store, db_engine = init_components()


# Define LangChain tools
@tool
def search_profiles(query: str, limit: int = 5) -> str:
    """Search Argo profiles using semantic search. Use natural language queries like 'warm water floats' or 'profiles near the equator'."""
    try:
        results = chroma_store.search(query, embedder, k=limit)
        output = {"query": query, "results": []}
        
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            output["results"].append({"description": doc, "metadata": meta})
        
        return json.dumps(output, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_statistics() -> str:
    """Get database statistics including profile count, measurement count, float count, and date ranges."""
    try:
        with db_engine.connect() as conn:
            profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()
            measurement_count = conn.execute(text("SELECT COUNT(*) FROM measurements")).scalar()
            float_count = conn.execute(text("SELECT COUNT(DISTINCT float_id) FROM profiles")).scalar()
            
            date_range = conn.execute(
                text("SELECT MIN(datetime) as min_date, MAX(datetime) as max_date FROM profiles")
            ).fetchone()
            
            stats = {
                "profile_count": profile_count,
                "measurement_count": measurement_count,
                "float_count": float_count,
                "date_range": {
                    "earliest": str(date_range[0]) if date_range[0] else None,
                    "latest": str(date_range[1]) if date_range[1] else None,
                },
            }
            
            return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_float_details(float_id: str) -> str:
    """Get detailed information about a specific float including all profiles and measurements."""
    try:
        with db_engine.connect() as conn:
            profiles_df = pd.read_sql(
                f"SELECT * FROM profiles WHERE float_id = '{float_id}'", conn
            )
            measurements_df = pd.read_sql(
                f"SELECT * FROM measurements WHERE float_id = '{float_id}' LIMIT 100", conn
            )
            
            result = {
                "float_id": float_id,
                "profile_count": len(profiles_df),
                "profiles": profiles_df.to_dict(orient="records"),
                "sample_measurements": measurements_df.to_dict(orient="records"),
            }
            
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def query_database(sql: str) -> str:
    """Execute a SQL query on the database. Only SELECT queries are allowed."""
    try:
        sql = sql.strip()
        if not sql.upper().startswith("SELECT"):
            return json.dumps({"error": "Only SELECT queries are allowed"})
        
        with db_engine.connect() as conn:
            df = pd.read_sql(sql, conn)
            result = {
                "query": sql,
                "row_count": len(df),
                "results": df.to_dict(orient="records"),
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_profiles_by_location(min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> str:
    """Find profiles within a geographic bounding box defined by latitude and longitude ranges."""
    try:
        query = f"""
        SELECT * FROM profiles
        WHERE latitude BETWEEN {min_lat} AND {max_lat}
        AND longitude BETWEEN {min_lon} AND {max_lon}
        """
        
        with db_engine.connect() as conn:
            df = pd.read_sql(query, conn)
            result = {
                "bounding_box": {
                    "min_lat": min_lat,
                    "max_lat": max_lat,
                    "min_lon": min_lon,
                    "max_lon": max_lon,
                },
                "profile_count": len(df),
                "profiles": df.to_dict(orient="records"),
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_profiles_by_date(start_date: str, end_date: str) -> str:
    """Find profiles within a date range. Dates should be in YYYY-MM-DD format."""
    try:
        query = f"""
        SELECT * FROM profiles
        WHERE datetime BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY datetime
        """
        
        with db_engine.connect() as conn:
            df = pd.read_sql(query, conn)
            result = {
                "date_range": {"start": start_date, "end": end_date},
                "profile_count": len(df),
                "profiles": df.to_dict(orient="records"),
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Initialize LangChain agent
@st.cache_resource
def init_agent():
    """Initialize LangChain agent with tools"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("⚠️ ANTHROPIC_API_KEY not found in environment variables!")
        st.info("Create a `.env` file with: `ANTHROPIC_API_KEY=your_key_here`")
        st.stop()
    
    tools = [
        search_profiles,
        get_statistics,
        get_float_details,
        query_database,
        get_profiles_by_location,
        get_profiles_by_date,
    ]
    
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        api_key=api_key,
        temperature=0
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an oceanography assistant helping users explore Argo float data.
        
You have access to tools to search profiles, get statistics, query the database, and filter by location/date.

When presenting results:
- Be concise and clear
- Highlight interesting patterns
- Suggest follow-up queries
- Format data in readable tables when appropriate

The database contains real Argo float data from 1997-2001 with temperature, salinity, and pressure measurements."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )
    
    return agent_executor


agent_executor = init_agent()


# Sidebar
with st.sidebar:
    st.markdown("### 🌊 FloatChat RAG")
    st.markdown("Explore oceanographic data with AI")
    
    st.markdown("---")
    
    # Quick stats
    st.markdown("### 📊 Quick Stats")
    try:
        with db_engine.connect() as conn:
            profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()
            float_count = conn.execute(text("SELECT COUNT(DISTINCT float_id) FROM profiles")).scalar()
            
            col1, col2 = st.columns(2)
            col1.metric("Profiles", f"{profile_count:,}")
            col2.metric("Floats", float_count)
    except Exception as e:
        st.error(f"Error loading stats: {e}")
    
    st.markdown("---")
    
    # Example queries
    st.markdown("### 💡 Example Queries")
    examples = [
        "What ocean data do we have?",
        "Show me warm water profiles",
        "Get details for float 13857",
        "Profiles from the Atlantic Ocean",
        "Show me profiles from 1998",
    ]
    
    for example in examples:
        if st.button(example, key=f"example_{example}", use_container_width=True):
            st.session_state.example_query = example
    
    st.markdown("---")
    
    # Tools info
    with st.expander("🛠️ Available Tools"):
        st.markdown("""
        - **search_profiles**: Semantic search
        - **get_statistics**: Database stats
        - **get_float_details**: Float info
        - **query_database**: Custom SQL
        - **get_profiles_by_location**: Geographic filter
        - **get_profiles_by_date**: Date filter
        """)
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# Main content
st.markdown('<h1 class="main-header">🌊 FloatChat RAG</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Explore Argo oceanographic float data using natural language</p>', unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show tools used
        if "tools_used" in message and message["tools_used"]:
            tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in message["tools_used"]])
            st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)

# Handle example query from sidebar
if "example_query" in st.session_state:
    prompt = st.session_state.example_query
    del st.session_state.example_query
else:
    prompt = st.chat_input("Ask about ocean data...")

# Process user input
if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = agent_executor.invoke({"input": prompt})
                response = result["output"]
                
                # Extract tools used
                tools_used = []
                if "intermediate_steps" in result:
                    tools_used = [step[0].tool for step in result["intermediate_steps"]]
                
                st.markdown(response)
                
                # Show tools used
                if tools_used:
                    tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in tools_used])
                    st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)
                
                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "tools_used": tools_used
                })
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.875rem;">
    Built with Streamlit + LangChain + Claude | Data from Argo Float Program
</div>
""", unsafe_allow_html=True)
