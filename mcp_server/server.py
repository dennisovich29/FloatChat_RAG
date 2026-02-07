#!/usr/bin/env python3
"""
FloatChat RAG MCP Server

Provides LLM access to Argo oceanographic float data via Model Context Protocol.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from sqlalchemy import create_engine, text

# Disable ChromaDB telemetry to avoid write issues in sandboxed environments
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = "data/databases/argo_data.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Initialize components
app = Server("floatchat-rag")
embedder = None
chroma_store = None
db_engine = None


def init_components():
    """Initialize database connections and embedder"""
    global embedder, chroma_store, db_engine

    try:
        logger.info("Initializing FloatChat RAG MCP Server...")
        
        # Initialize embedder
        embedder = ArgoMetadataEmbedder()
        
        # Initialize ChromaDB with absolute path to avoid sandbox issues
        import chromadb
        
        # Get absolute path to vector_db
        vector_db_path = Path(__file__).parent.parent / "data" / "vector_db"
        vector_db_path = str(vector_db_path.absolute())
        
        logger.info(f"Using ChromaDB path: {vector_db_path}")
        
        # Create ChromaDB client with absolute path
        chroma_client = chromadb.PersistentClient(path=vector_db_path)
        
        # Initialize store manually to use our client
        chroma_store = ArgoChromaStore.__new__(ArgoChromaStore)
        chroma_store.client = chroma_client
        chroma_store.collection = chroma_client.get_or_create_collection(
            name="argo_profiles", metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize database engine with absolute path
        db_path_abs = Path(__file__).parent.parent / DB_PATH
        db_url_abs = f"sqlite:///{db_path_abs.absolute()}"
        db_engine = create_engine(db_url_abs)
        
        logger.info("✓ Components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise


# ============================================================================
# RESOURCES
# ============================================================================


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="argo://profiles/recent",
            name="Recent Argo Profiles",
            description="Last 20 oceanographic profiles from the database",
            mimeType="application/json",
        ),
        Resource(
            uri="argo://database/schema",
            name="Database Schema",
            description="Schema information for profiles and measurements tables",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content"""

    if uri == "argo://profiles/recent":
        query = """
        SELECT float_id, cycle_number, latitude, longitude, datetime, data_center
        FROM profiles
        ORDER BY datetime DESC
        LIMIT 20
        """
        with db_engine.connect() as conn:
            df = pd.read_sql(query, conn)
            return df.to_json(orient="records", indent=2)

    elif uri == "argo://database/schema":
        schema_info = {
            "tables": {
                "profiles": {
                    "description": "Oceanographic profile metadata",
                    "columns": [
                        "float_id",
                        "cycle_number",
                        "latitude",
                        "longitude",
                        "datetime",
                        "data_center",
                    ],
                },
                "measurements": {
                    "description": "Individual measurements from profiles",
                    "columns": [
                        "float_id",
                        "cycle_number",
                        "pressure",
                        "temperature",
                        "salinity",
                        "depth",
                    ],
                },
            }
        }
        return json.dumps(schema_info, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")


# ============================================================================
# TOOLS
# ============================================================================


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_profiles",
            description="Search Argo profiles using semantic search. Use natural language queries like 'warm water floats' or 'profiles near the equator'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_statistics",
            description="Get database statistics including profile count, measurement count, float count, and date ranges.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_float_details",
            description="Get detailed information about a specific float including all profiles and measurements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "float_id": {
                        "type": "string",
                        "description": "Float ID to retrieve details for",
                    }
                },
                "required": ["float_id"],
            },
        ),
        Tool(
            name="query_database",
            description="Execute a SQL query on the database. Only SELECT queries are allowed. Use this for custom data analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL SELECT query to execute"}
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="get_profiles_by_location",
            description="Find profiles within a geographic bounding box defined by latitude and longitude ranges.",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_lat": {"type": "number", "description": "Minimum latitude"},
                    "max_lat": {"type": "number", "description": "Maximum latitude"},
                    "min_lon": {"type": "number", "description": "Minimum longitude"},
                    "max_lon": {"type": "number", "description": "Maximum longitude"},
                },
                "required": ["min_lat", "max_lat", "min_lon", "max_lon"],
            },
        ),
        Tool(
            name="get_profiles_by_date",
            description="Find profiles within a date range. Dates should be in YYYY-MM-DD format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                },
                "required": ["start_date", "end_date"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute tool calls"""

    try:
        if name == "search_profiles":
            query = arguments["query"]
            limit = arguments.get("limit", 5)

            results = chroma_store.search(query, embedder, k=limit)

            output = {"query": query, "results": []}

            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                output["results"].append({"description": doc, "metadata": meta})

            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        elif name == "get_statistics":
            with db_engine.connect() as conn:
                # Profile count
                profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()

                # Measurement count
                measurement_count = conn.execute(text("SELECT COUNT(*) FROM measurements")).scalar()

                # Float count
                float_count = conn.execute(
                    text("SELECT COUNT(DISTINCT float_id) FROM profiles")
                ).scalar()

                # Date range
                date_range = conn.execute(
                    text(
                        "SELECT MIN(datetime) as min_date, MAX(datetime) as max_date FROM profiles"
                    )
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

                return [TextContent(type="text", text=json.dumps(stats, indent=2))]

        elif name == "get_float_details":
            float_id = arguments["float_id"]

            with db_engine.connect() as conn:
                # Get profiles
                profiles_df = pd.read_sql(
                    f"SELECT * FROM profiles WHERE float_id = '{float_id}'", conn
                )

                # Get measurements
                measurements_df = pd.read_sql(
                    f"SELECT * FROM measurements WHERE float_id = '{float_id}' LIMIT 100", conn
                )

                result = {
                    "float_id": float_id,
                    "profile_count": len(profiles_df),
                    "profiles": profiles_df.to_dict(orient="records"),
                    "sample_measurements": measurements_df.to_dict(orient="records"),
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "query_database":
            sql = arguments["sql"].strip()

            # Security: Only allow SELECT queries
            if not sql.upper().startswith("SELECT"):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "Only SELECT queries are allowed"}, indent=2),
                    )
                ]

            with db_engine.connect() as conn:
                df = pd.read_sql(sql, conn)

                result = {
                    "query": sql,
                    "row_count": len(df),
                    "results": df.to_dict(orient="records"),
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_profiles_by_location":
            min_lat = arguments["min_lat"]
            max_lat = arguments["max_lat"]
            min_lon = arguments["min_lon"]
            max_lon = arguments["max_lon"]

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

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_profiles_by_date":
            start_date = arguments["start_date"]
            end_date = arguments["end_date"]

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

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [
                TextContent(
                    type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2)
                )
            ]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run the MCP server"""
    init_components()

    async with stdio_server() as (read_stream, write_stream):
        logger.info("FloatChat RAG MCP Server running on stdio")
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
