#!/usr/bin/env python3
"""
FloatChat RAG - Streamlit Web Interface with Ollama (FREE!)

A web-based chat interface using Ollama for 100% free local LLM inference.
No API key required, works offline!
"""

import os
import sys
from pathlib import Path

import streamlit as st

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_ollama import ChatOllama
from sqlalchemy import create_engine, text
import pandas as pd
import json

# Page config
st.set_page_config(
    page_title="FloatChat RAG (Free)",
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
    .free-badge {
        background-color: #10b981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-left: 1rem;
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
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        embedder = ArgoMetadataEmbedder()
        chroma_store = ArgoChromaStore()
        db_engine = create_engine("sqlite:///data/databases/argo_data.db")
        
        return embedder, chroma_store, db_engine
    except Exception as e:
        st.error(f"Failed to initialize components: {e}")
        st.stop()


embedder, chroma_store, db_engine = init_components()


# Define LangChain tools (same as before)
@tool
def search_profiles(query: str, limit: int = 5) -> str:
    """Search Argo profiles using semantic search."""
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
    """Get database statistics."""
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
    """Get detailed information about a specific float."""
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
    """Execute a SQL query. Only SELECT queries allowed.
    
    IMPORTANT: The only tables are `profiles` and `measurements`.
    DO NOT use `argo_float_data`. It does not exist.
    """
    try:
        sql = sql.strip()
        if not sql.upper().startswith("SELECT"):
            return json.dumps({"error": "Only SELECT queries are allowed"})
        
        # Guard against hallucinated table
        if "argo_float_data" in sql:
            return json.dumps({"error": "Table 'argo_float_data' does not exist. Use 'profiles' or 'measurements'."})

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
    """Find profiles within a geographic bounding box."""
    try:
        query = f"""
        SELECT * FROM profiles
        WHERE latitude BETWEEN {min_lat} AND {max_lat}
        AND longitude BETWEEN {min_lon} AND {max_lon}
        """
        with db_engine.connect() as conn:
            df = pd.read_sql(query, conn)
            result = {
                "bounding_box": {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
                "profile_count": len(df),
                "profiles": df.to_dict(orient="records"),
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_profiles_by_date(start_date: str, end_date: str) -> str:
    """Find profiles within a date range (YYYY-MM-DD format)."""
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


# Initialize Ollama agent
@st.cache_resource
def init_agent_v2():  # Renamed to force cache reload
    """Initialize LangChain agent with Ollama (FREE!)"""
    
    tools = [
        search_profiles,
        get_statistics,
        get_float_details,
        query_database,
        get_profiles_by_location,
        get_profiles_by_date,
    ]
    
    # Use Ollama - 100% FREE, no API key needed!
    llm = ChatOllama(
        model="llama3.2:3b",  # Fast, good quality
        temperature=0,
        base_url="http://localhost:11434"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an oceanography assistant helping users explore Argo float data.

**DATABASE SCHEMA:**
The database has two tables:
1. `profiles` table:
   - `float_id` (TEXT)
   - `cycle_number` (INTEGER)
   - `datetime` (TEXT)
   - `latitude` (REAL)
   - `longitude` (REAL)
   - `data_center` (TEXT)

2. `measurements` table:
   - `float_id` (TEXT)
   - `cycle_number` (INTEGER)
   - `pres` (REAL) - Pressure/Depth
   - `temp` (REAL) - Temperature
   - `psal` (REAL) - Salinity

**RULES:**
1. ALWAYS use the tools provided. DO NOT guess.
2. For "what do we have?", call `get_statistics`.
3. For "search" or specific topics like "warm water", use `search_profiles`.
4. For SQL queries via `query_database`:
   - ONLY use table names `profiles` and `measurements`.
   - `argo_float_data` DOES NOT EXIST.
   - Example: SELECT * FROM profiles LIMIT 5
5. Be concise.

The database contains real Argo float data from 1997-2001."""),
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

# ... (rest of main logic) ...

# Initialize agent
try:
    agent_executor = init_agent_v2()  # Updated function name
except Exception as e:
    st.error(f"Failed to initialize agent: {e}")
    st.stop()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "tools_used" in message and message["tools_used"]:
            tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in message["tools_used"]])
            st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)

# Helper to handle example queries properly
def set_example_query(query):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = agent_executor.invoke({"input": query})
                response = result["output"]
                
                tools_used = []
                if "intermediate_steps" in result:
                    tools_used = [step[0].tool for step in result["intermediate_steps"]]
                
                st.markdown(response)
                
                if tools_used:
                    tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in tools_used])
                    st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "tools_used": tools_used
                })
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Sidebar examples logic updated
with st.sidebar:
    # ... (existing sidebar logic) ...
    # Instead of setting state, just run directly? No, streamlit reruns.
    # Proper way:
    
    st.markdown("### 💡 Example Queries")
    examples = [
        "What ocean data do we have?",
        "Show me warm water profiles",
        "Get details for float 13857",
        "Profiles from 1998",
    ]
    
    for example in examples:
        if st.button(example, key=f"ex_{example}", use_container_width=True):
             # Just set into session state to handle AFTER rendering input? no.
             # Run helper function directly, then rerun
             set_example_query(example)
             st.rerun()

# Always show chat input at bottom
prompt = st.chat_input("Ask about ocean data...")

if prompt:
    # Same logic as helper
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = agent_executor.invoke({"input": prompt})
                response = result["output"]
                
                tools_used = []
                if "intermediate_steps" in result:
                    tools_used = [step[0].tool for step in result["intermediate_steps"]]
                
                st.markdown(response)
                
                if tools_used:
                    tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in tools_used])
                    st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "tools_used": tools_used
                })
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.875rem;">
    Built with Streamlit + LangChain + Ollama (100% Free!) | Data from Argo Float Program
</div>
""", unsafe_allow_html=True)
