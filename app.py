#!/usr/bin/env python3
"""
FloatChat RAG - Streamlit Web Interface with LangChain

A web-based chat interface to explore Argo oceanographic float data using AI.
"""

import os
import sys
import re
from pathlib import Path

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.prompts import ChatPromptTemplate
from langchain_classic.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from plotly.subplots import make_subplots

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore
from sqlalchemy import create_engine, text
import pandas as pd
import json

SQL_MAX_ROWS = 200
PLOT_MAX_ROWS = 500

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


def normalize_agent_response(response) -> str:
    """Convert varied model payload formats into clean display text."""
    if response is None:
        return "I couldn't generate a response for that request."

    if isinstance(response, str):
        cleaned = response.strip()
        return cleaned or "I couldn't generate a response for that request."

    if isinstance(response, list):
        parts = [normalize_agent_response(item) for item in response]
        merged = "\n".join(part for part in parts if part)
        return merged.strip() or "I couldn't generate a response for that request."

    if isinstance(response, dict):
        if isinstance(response.get("text"), str):
            return normalize_agent_response(response["text"])
        if "content" in response:
            return normalize_agent_response(response["content"])
        return json.dumps(response, indent=2)

    return str(response)


def apply_sql_guardrails(sql: str, max_rows: int = SQL_MAX_ROWS) -> tuple[str | None, str | None]:
    """Enforce SELECT-only SQL and cap large result sets."""
    cleaned_sql = re.sub(r"\s+", " ", sql.strip()).rstrip(";")
    if not cleaned_sql:
        return None, "Query is empty. Please provide a SELECT statement."

    if ";" in cleaned_sql:
        return None, "Only a single SELECT query is allowed."

    lowered = cleaned_sql.lower()
    if not lowered.startswith("select"):
        return None, "Only SELECT queries are allowed."

    blocked_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "attach",
        "detach",
        "pragma",
        "vacuum",
    ]
    if any(re.search(rf"\b{keyword}\b", lowered) for keyword in blocked_keywords):
        return None, "Query contains blocked SQL keywords."

    limit_match = re.search(r"\blimit\s+(\d+)\b", lowered)
    if limit_match:
        requested_limit = int(limit_match.group(1))
        if requested_limit > max_rows:
            cleaned_sql = re.sub(r"(?i)\blimit\s+\d+\b", f"LIMIT {max_rows}", cleaned_sql, count=1)
    else:
        cleaned_sql = f"{cleaned_sql} LIMIT {max_rows}"

    return cleaned_sql, None


def safe_json_load(value):
    """Parse JSON safely and return a dict/list or None."""
    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str):
        return None

    try:
        return json.loads(value)
    except Exception:
        return None


def build_figures_from_payload(payload: dict) -> list[tuple[go.Figure, str]]:
    """Build Plotly figure(s) from a chart payload."""
    chart_type = payload.get("chart_type")
    figures: list[tuple[go.Figure, str]] = []

    if chart_type == "map_profiles":
        points = payload.get("points", [])
        if not points:
            return figures

        df = pd.DataFrame(points)
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.drop_duplicates(subset=["float_id", "cycle_number", "latitude", "longitude", "datetime"], keep="first")
        min_lat = float(payload.get("min_lat", df["latitude"].min()))
        max_lat = float(payload.get("max_lat", df["latitude"].max()))
        min_lon = float(payload.get("min_lon", df["longitude"].min()))
        max_lon = float(payload.get("max_lon", df["longitude"].max()))

        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        lat_span = max(0.1, max_lat - min_lat)
        lon_span = max(0.1, max_lon - min_lon)
        span = max(lat_span, lon_span)

        if span <= 2:
            zoom = 6
        elif span <= 5:
            zoom = 5
        elif span <= 10:
            zoom = 4
        elif span <= 20:
            zoom = 3
        else:
            zoom = 2

        fig = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            color="float_id",
            hover_data=["datetime", "cycle_number"],
            title=payload.get("title", "Profile Locations"),
            zoom=zoom,
            center={"lat": center_lat, "lon": center_lon},
            mapbox_style="carto-positron",
        )
        fig.update_traces(marker=dict(size=12, opacity=0.9))

        if {"float_id", "latitude", "longitude"}.issubset(df.columns):
            for float_id, group in df.groupby("float_id"):
                group = group.sort_values(by=["datetime", "cycle_number"], na_position="last")
                if len(group) > 1:
                    fig.add_trace(
                        go.Scattermapbox(
                            lat=group["latitude"],
                            lon=group["longitude"],
                            mode="lines",
                            name=f"{float_id} trajectory",
                            showlegend=False,
                            line={"width": 2},
                            hoverinfo="skip",
                        )
                    )

        fig.update_layout(
            height=560,
            margin=dict(l=10, r=10, t=50, b=10),
            legend_title_text="Float ID",
        )
        figures.append((fig, payload.get("interpretation", "Map shows profile locations in the selected bounds.")))
        return figures

    if chart_type == "profile_temp_sal":
        depths = payload.get("depth", [])
        temperatures = payload.get("temperature", [])
        salinity = payload.get("salinity", [])
        if not depths:
            return figures

        subplot = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Temperature Profile", "Salinity Profile"),
            shared_yaxes=True,
        )
        subplot.add_trace(
            go.Scatter(x=temperatures, y=depths, mode="lines+markers", name="Temperature (°C)"),
            row=1,
            col=1,
        )
        subplot.add_trace(
            go.Scatter(x=salinity, y=depths, mode="lines+markers", name="Salinity (PSU)"),
            row=1,
            col=2,
        )
        subplot.update_yaxes(title_text="Depth (dbar)", autorange="reversed", row=1, col=1)
        subplot.update_yaxes(autorange="reversed", row=1, col=2)
        subplot.update_xaxes(title_text="Temperature (°C)", row=1, col=1)
        subplot.update_xaxes(title_text="Salinity (PSU)", row=1, col=2)
        subplot.update_layout(title=payload.get("title", "Temperature and Salinity Profile"), height=500)
        figures.append((subplot, payload.get("interpretation", "Profiles show temperature and salinity versus depth.")))
        return figures

    if chart_type == "time_series":
        points = payload.get("points", [])
        if not points:
            return figures

        df = pd.DataFrame(points)
        fig = px.line(
            df,
            x="datetime",
            y="value",
            markers=True,
            title=payload.get("title", "Time Series"),
            labels={"value": payload.get("y_label", "Value"), "datetime": "Datetime"},
        )
        figures.append((fig, payload.get("interpretation", "Trend shows variation over cycles/time.")))
        return figures

    return figures


def render_chart_payloads(chart_payloads: list[dict], key_prefix: str = "chart"):
    """Render chart payloads in Streamlit."""
    for payload_index, payload in enumerate(chart_payloads):
        figures = build_figures_from_payload(payload)
        for figure_index, (figure, interpretation) in enumerate(figures):
            chart_key = f"{key_prefix}_{payload_index}_{figure_index}"
            st.plotly_chart(figure, use_container_width=True, key=chart_key)
            if interpretation:
                st.caption(interpretation)


def render_chart_payloads_safe(chart_payloads: list[dict], key_prefix: str = "chart") -> bool:
    """Render chart payloads safely without failing the full response path."""
    if not chart_payloads:
        return True

    try:
        render_chart_payloads(chart_payloads, key_prefix=key_prefix)
        return True
    except Exception as error:
        st.warning(f"Chart rendering failed for this response, but data retrieval succeeded. Reason: {error}")
        return False


def extract_chart_payloads(intermediate_steps) -> list[dict]:
    """Extract chart payloads from tool observations."""
    payloads = []
    for step in intermediate_steps or []:
        if not isinstance(step, tuple) or len(step) < 2:
            continue

        action, observation = step
        tool_name = getattr(action, "tool", "")
        if tool_name not in {
            "map_profiles_by_bounds",
            "plot_profile_temp_sal",
            "plot_time_series",
            "get_profiles_by_location",
        }:
            continue

        parsed = safe_json_load(observation)
        if isinstance(parsed, dict):
            if tool_name == "get_profiles_by_location" and isinstance(parsed.get("profiles"), list):
                payloads.append(
                    {
                        "chart_type": "map_profiles",
                        "title": "Profiles by Geographic Bounds",
                        "points": parsed.get("profiles", []),
                        "min_lat": parsed.get("bounding_box", {}).get("min_lat", -30),
                        "max_lat": parsed.get("bounding_box", {}).get("max_lat", 30),
                        "min_lon": parsed.get("bounding_box", {}).get("min_lon", 30),
                        "max_lon": parsed.get("bounding_box", {}).get("max_lon", 120),
                        "interpretation": (
                            f"Showing {parsed.get('profile_count', 0)} profile rows in the selected location window."
                        ),
                    }
                )
                continue

            if isinstance(parsed.get("chart_payload"), dict):
                payloads.append(parsed["chart_payload"])
            elif parsed.get("chart_type"):
                payloads.append(parsed)

    return payloads


def extract_float_id_from_prompt(user_prompt: str) -> str | None:
    """Extract float ID from free-form prompt text."""
    match = re.search(r"\b(\d{7,})\b", user_prompt)
    return match.group(1) if match else None


def extract_bounds_from_prompt(user_prompt: str) -> tuple[float, float, float, float] | None:
    """Extract latitude/longitude bounds from prompt if present."""
    text_lower = user_prompt.lower()
    lat_match = re.search(r"latitude\s*(-?\d+(?:\.\d+)?)\s*(?:to|\-|\.\.)\s*(-?\d+(?:\.\d+)?)", text_lower)
    lon_match = re.search(r"longitude\s*(-?\d+(?:\.\d+)?)\s*(?:to|\-|\.\.)\s*(-?\d+(?:\.\d+)?)", text_lower)

    if lat_match and lon_match:
        min_lat, max_lat = sorted([float(lat_match.group(1)), float(lat_match.group(2))])
        min_lon, max_lon = sorted([float(lon_match.group(1)), float(lon_match.group(2))])
        return min_lat, max_lat, min_lon, max_lon

    if "arabian sea" in text_lower:
        return 15.0, 20.0, 60.0, 70.0

    if "equator" in text_lower:
        return -10.0, 10.0, 30.0, 120.0

    return None


def load_gemini_api_keys() -> list[str]:
    """Load configured Gemini API keys from env with stable priority order."""
    keys: list[str] = []

    primary = os.getenv("GOOGLE_API_KEY", "").strip()
    if primary and primary != "your_google_api_key_here":
        keys.append(primary)

    numbered: list[tuple[int, str]] = []
    for env_name, env_value in os.environ.items():
        match = re.fullmatch(r"GOOGLE_API_KEY_(\d+)", env_name)
        if not match:
            continue
        value = (env_value or "").strip()
        if not value or value == "your_google_api_key_here":
            continue
        numbered.append((int(match.group(1)), value))

    for _, value in sorted(numbered, key=lambda item: item[0]):
        if value not in keys:
            keys.append(value)

    csv_keys = os.getenv("GOOGLE_API_KEYS", "")
    if csv_keys:
        for value in [part.strip() for part in csv_keys.split(",")]:
            if value and value != "your_google_api_key_here" and value not in keys:
                keys.append(value)

    return keys


def is_quota_error_message(error_text: str) -> bool:
    lowered = error_text.lower()
    return (
        "resource_exhausted" in lowered
        or "quota" in lowered
        or "429" in error_text
    )


class AllGeminiKeysExhaustedError(RuntimeError):
    """Raised when every configured Gemini key fails with quota errors."""


GEMINI_API_KEYS = load_gemini_api_keys()


def try_direct_demo_route(user_prompt: str):
    """Execute deterministic demo-safe tool routes without LLM, when prompt intent is clear."""
    text_lower = user_prompt.lower()
    tools_used = []
    chart_payloads = []

    try:
        if "trend" in text_lower and any(param in text_lower for param in ["salinity", "temperature", "pressure"]):
            float_id = extract_float_id_from_prompt(user_prompt)
            if not float_id:
                return None

            parameter = "salinity" if "salinity" in text_lower else "temperature" if "temperature" in text_lower else "pressure"
            trend_obj = safe_json_load(plot_time_series.invoke({"float_id": float_id, "parameter": parameter}))
            if not isinstance(trend_obj, dict):
                return None

            if isinstance(trend_obj.get("chart_payload"), dict):
                chart_payloads.append(trend_obj["chart_payload"])

            message = trend_obj.get("message")
            if not message and chart_payloads:
                message = f"Showing {parameter} trend over time for float {float_id}."

            tools_used.append("plot_time_series")
            return message or "Trend data generated.", tools_used, chart_payloads

        if "profile" in text_lower and "temperature" in text_lower and "salinity" in text_lower:
            float_id = extract_float_id_from_prompt(user_prompt)
            if not float_id:
                return None

            profile_obj = safe_json_load(plot_profile_temp_sal.invoke({"float_id": float_id}))
            if not isinstance(profile_obj, dict):
                return None

            if isinstance(profile_obj.get("chart_payload"), dict):
                chart_payloads.append(profile_obj["chart_payload"])

            message = profile_obj.get("message")
            if not message and chart_payloads:
                message = f"Showing temperature and salinity profile for float {float_id}."

            tools_used.append("plot_profile_temp_sal")
            return message or "Profile plot generated.", tools_used, chart_payloads

        explicit_map_request = any(token in text_lower for token in ["map", "plot", "visual", "chart"])
        wants_map = any(token in text_lower for token in ["map", "location", "bounds", "latitude", "longitude", "arabian sea"])
        wants_summary = any(token in text_lower for token in ["what data", "all profiles", "summaris", "summary"])

        if wants_summary:
            stats_obj = safe_json_load(get_statistics.invoke({}))
            if isinstance(stats_obj, dict) and stats_obj.get("profile_count") is not None:
                tools_used.append("get_statistics")
                message = (
                    f"Dataset summary: {stats_obj.get('profile_count')} profiles, "
                    f"{stats_obj.get('measurement_count')} measurements, "
                    f"{stats_obj.get('float_count')} floats, "
                    f"date range {stats_obj.get('date_range', {}).get('earliest')} to {stats_obj.get('date_range', {}).get('latest')}."
                )

                if explicit_map_request:
                    bounds = extract_bounds_from_prompt(user_prompt)
                    if bounds is not None:
                        min_lat, max_lat, min_lon, max_lon = bounds
                        map_obj = safe_json_load(
                            map_profiles_by_bounds.invoke(
                                {
                                    "min_lat": min_lat,
                                    "max_lat": max_lat,
                                    "min_lon": min_lon,
                                    "max_lon": max_lon,
                                }
                            )
                        )
                        if isinstance(map_obj, dict) and isinstance(map_obj.get("chart_payload"), dict):
                            chart_payloads.append(map_obj["chart_payload"])
                            point_count = len(map_obj["chart_payload"].get("points", []))
                            message += f" Showing {point_count} profile points for the requested geographic window."
                            tools_used.append("map_profiles_by_bounds")

                return message, tools_used, chart_payloads

        if wants_map:
            bounds = extract_bounds_from_prompt(user_prompt)
            if bounds is not None:
                min_lat, max_lat, min_lon, max_lon = bounds
                map_obj = safe_json_load(
                    map_profiles_by_bounds.invoke(
                        {
                            "min_lat": min_lat,
                            "max_lat": max_lat,
                            "min_lon": min_lon,
                            "max_lon": max_lon,
                        }
                    )
                )
                if isinstance(map_obj, dict) and isinstance(map_obj.get("chart_payload"), dict):
                    chart_payloads.append(map_obj["chart_payload"])
                    point_count = len(map_obj["chart_payload"].get("points", []))
                    message = f"Showing {point_count} profile points for the requested geographic window."
                    tools_used.append("map_profiles_by_bounds")
                    return message, tools_used, chart_payloads

    except Exception:
        return None

    return None


@st.cache_data(ttl=600)
def cached_statistics_data() -> dict:
    """Cached stats snapshot for demo responsiveness."""
    with db_engine.connect() as conn:
        profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()
        measurement_count = conn.execute(text("SELECT COUNT(*) FROM measurements")).scalar()
        float_count = conn.execute(text("SELECT COUNT(DISTINCT float_id) FROM profiles")).scalar()
        date_range = conn.execute(
            text("SELECT MIN(datetime) as min_date, MAX(datetime) as max_date FROM profiles")
        ).fetchone()

    return {
        "profile_count": profile_count,
        "measurement_count": measurement_count,
        "float_count": float_count,
        "date_range": {
            "earliest": str(date_range[0]) if date_range and date_range[0] else None,
            "latest": str(date_range[1]) if date_range and date_range[1] else None,
        },
    }


@st.cache_data(ttl=600)
def cached_profiles_by_location_data(min_lat: float, max_lat: float, min_lon: float, max_lon: float, limit: int) -> dict:
    """Cached geographic profile retrieval."""
    with db_engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT * FROM profiles
                WHERE latitude BETWEEN :min_lat AND :max_lat
                AND longitude BETWEEN :min_lon AND :max_lon
                ORDER BY datetime DESC
                LIMIT :limit
                """
            ),
            conn,
            params={
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon,
                "limit": limit,
            },
        )

    return {
        "bounding_box": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        },
        "profile_count": len(df),
        "profiles": df.to_dict(orient="records"),
    }


@st.cache_data(ttl=600)
def cached_map_profiles_data(min_lat: float, max_lat: float, min_lon: float, max_lon: float, limit: int) -> dict:
    """Cached map payload source retrieval."""
    with db_engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT float_id, cycle_number, datetime, latitude, longitude
                FROM profiles
                WHERE latitude BETWEEN :min_lat AND :max_lat
                  AND longitude BETWEEN :min_lon AND :max_lon
                ORDER BY datetime DESC
                LIMIT :limit
                """
            ),
            conn,
            params={
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon,
                "limit": limit,
            },
        )

    return {
        "points": df.to_dict(orient="records"),
        "float_count": int(df["float_id"].nunique()) if not df.empty else 0,
    }


@st.cache_data(ttl=600)
def cached_profile_plot_data(float_id: str, cycle_number: int | None) -> dict:
    """Cached source retrieval for profile temperature/salinity plotting."""
    with db_engine.connect() as conn:
        if cycle_number is None:
            profile_row = conn.execute(
                text(
                    """
                    SELECT profile_id, cycle_number, datetime
                    FROM profiles
                    WHERE float_id = :float_id
                    ORDER BY datetime DESC
                    LIMIT 1
                    """
                ),
                {"float_id": float_id},
            ).fetchone()
        else:
            profile_row = conn.execute(
                text(
                    """
                    SELECT profile_id, cycle_number, datetime
                    FROM profiles
                    WHERE float_id = :float_id AND cycle_number = :cycle_number
                    ORDER BY datetime DESC
                    LIMIT 1
                    """
                ),
                {"float_id": float_id, "cycle_number": cycle_number},
            ).fetchone()

        if not profile_row:
            return {"profile_found": False}

        profile_id = profile_row[0]
        resolved_cycle = int(profile_row[1]) if profile_row[1] is not None else None
        profile_datetime = str(profile_row[2]) if profile_row[2] is not None else "unknown"

        measurements = pd.read_sql(
            text(
                """
                SELECT pressure, level, temperature, salinity
                FROM measurements
                WHERE float_id = :float_id AND profile_id = :profile_id
                ORDER BY pressure ASC, level ASC
                """
            ),
            conn,
            params={"float_id": float_id, "profile_id": profile_id},
        )

    return {
        "profile_found": True,
        "profile_datetime": profile_datetime,
        "resolved_cycle": resolved_cycle,
        "measurements": measurements.to_dict(orient="records"),
    }


@st.cache_data(ttl=600)
def cached_trend_data(float_id: str, parameter: str, limit: int) -> dict:
    """Cached source retrieval for time-series trend plotting."""
    with db_engine.connect() as conn:
        df = pd.read_sql(
            text(
                f"""
                SELECT p.datetime, p.cycle_number, AVG(m.{parameter}) AS value
                FROM profiles p
                JOIN measurements m ON p.profile_id = m.profile_id AND p.float_id = m.float_id
                WHERE p.float_id = :float_id
                  AND p.datetime IS NOT NULL
                  AND m.{parameter} IS NOT NULL
                GROUP BY p.datetime, p.cycle_number
                ORDER BY p.datetime
                LIMIT :limit
                """
            ),
            conn,
            params={"float_id": float_id, "limit": limit},
        )

    return {
        "points": df.to_dict(orient="records"),
        "count": len(df),
    }


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
        return json.dumps(cached_statistics_data(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_float_details(float_id: str) -> str:
    """Get detailed information about a specific float including all profiles and measurements."""
    try:
        with db_engine.connect() as conn:
            profiles_df = pd.read_sql(
                text("""
                    SELECT * FROM profiles
                    WHERE float_id = :float_id
                    ORDER BY datetime DESC
                """),
                conn,
                params={"float_id": float_id},
            )
            measurements_df = pd.read_sql(
                text("""
                    SELECT * FROM measurements
                    WHERE float_id = :float_id
                    LIMIT 100
                """),
                conn,
                params={"float_id": float_id},
            )

            if profiles_df.empty:
                return json.dumps(
                    {
                        "message": f"No profiles found for float_id '{float_id}'.",
                        "suggestion": "Try get_statistics to list available float IDs.",
                    },
                    indent=2,
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
        safe_sql, error = apply_sql_guardrails(sql)
        if error:
            return json.dumps({"error": error, "max_rows": SQL_MAX_ROWS})
        
        with db_engine.connect() as conn:
            df = pd.read_sql(text(safe_sql), conn)

            if df.empty:
                return json.dumps(
                    {
                        "query": safe_sql,
                        "row_count": 0,
                        "message": "No rows matched this query.",
                        "suggestion": "Try broader date/location bounds or use get_statistics first.",
                    },
                    indent=2,
                )

            result = {
                "query": safe_sql,
                "row_count": len(df),
                "max_rows": SQL_MAX_ROWS,
                "results": df.to_dict(orient="records"),
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_profiles_by_location(min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> str:
    """Find profiles within a geographic bounding box defined by latitude and longitude ranges."""
    try:
        result = cached_profiles_by_location_data(min_lat, max_lat, min_lon, max_lon, SQL_MAX_ROWS)
        if result["profile_count"] == 0:
            result["message"] = "No profiles found in this geographic window."
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_profiles_by_date(start_date: str, end_date: str) -> str:
    """Find profiles within a date range. Dates should be in YYYY-MM-DD format."""
    try:
        with db_engine.connect() as conn:
            df = pd.read_sql(
                text("""
                    SELECT * FROM profiles
                    WHERE datetime BETWEEN :start_date AND :end_date
                    ORDER BY datetime
                    LIMIT :limit
                """),
                conn,
                params={"start_date": start_date, "end_date": end_date, "limit": SQL_MAX_ROWS},
            )

            if df.empty:
                return json.dumps(
                    {
                        "date_range": {"start": start_date, "end": end_date},
                        "profile_count": 0,
                        "message": "No profiles found in this date range.",
                    },
                    indent=2,
                )

            result = {
                "date_range": {"start": start_date, "end": end_date},
                "profile_count": len(df),
                "profiles": df.to_dict(orient="records"),
            }
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def map_profiles_by_bounds(min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> str:
    """Create a map of profile points within latitude/longitude bounds."""
    try:
        map_data = cached_map_profiles_data(min_lat, max_lat, min_lon, max_lon, PLOT_MAX_ROWS)

        chart_payload = {
            "chart_type": "map_profiles",
            "title": "Profiles by Geographic Bounds",
            "points": map_data["points"],
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
            "interpretation": (
                f"Showing {len(map_data['points'])} profiles from {map_data['float_count']} float(s) "
                "inside the selected map bounds."
            ),
        }
        return json.dumps({"chart_payload": chart_payload}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def plot_profile_temp_sal(float_id: str, cycle_number: int | None = None) -> str:
    """Plot depth-vs-temperature and depth-vs-salinity for a float profile (inverted depth axis)."""
    try:
        cached_profile = cached_profile_plot_data(float_id, cycle_number)

        if not cached_profile.get("profile_found"):
            return json.dumps(
                {
                    "message": f"No profile found for float {float_id} with the requested cycle.",
                    "suggestion": "Try a different float_id or omit cycle_number to use the latest profile.",
                },
                indent=2,
            )

        resolved_cycle = cached_profile.get("resolved_cycle")
        profile_datetime = cached_profile.get("profile_datetime", "unknown")
        measurements = pd.DataFrame(cached_profile.get("measurements", []))

        if measurements.empty:
            return json.dumps(
                {
                    "message": "Measurement rows are missing for this profile.",
                    "suggestion": "Try another float profile with available measurements.",
                },
                indent=2,
            )

        measurements["depth"] = measurements["pressure"].fillna(measurements["level"])
        measurements = measurements.dropna(subset=["depth", "temperature", "salinity"])

        if measurements.empty:
            return json.dumps(
                {
                    "message": "No complete temperature+salinity+depth rows were found for this profile.",
                },
                indent=2,
            )

        chart_payload = {
            "chart_type": "profile_temp_sal",
            "title": f"Float {float_id} | Cycle {resolved_cycle} | {profile_datetime}",
            "depth": measurements["depth"].tolist(),
            "temperature": measurements["temperature"].tolist(),
            "salinity": measurements["salinity"].tolist(),
            "interpretation": "Depth axis is inverted (surface at top), showing vertical temperature and salinity structure.",
        }
        return json.dumps({"chart_payload": chart_payload}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def plot_time_series(float_id: str, parameter: str) -> str:
    """Plot time/cycle trend for one parameter: temperature, salinity, or pressure."""
    try:
        normalized = parameter.strip().lower()
        if normalized not in {"temperature", "salinity", "pressure"}:
            return json.dumps(
                {"error": "Parameter must be one of: temperature, salinity, pressure."},
                indent=2,
            )

        trend_data = cached_trend_data(float_id, normalized, PLOT_MAX_ROWS)
        if trend_data["count"] == 0:
            return json.dumps(
                {"message": f"No {normalized} trend data found for float {float_id}."},
                indent=2,
            )

        chart_payload = {
            "chart_type": "time_series",
            "title": f"Float {float_id} {normalized.title()} Trend",
            "y_label": f"Mean {normalized.title()}",
            "points": trend_data["points"],
            "interpretation": f"Trend summarizes profile-level mean {normalized} across time/cycles for float {float_id}.",
        }
        return json.dumps({"chart_payload": chart_payload}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Initialize LangChain agent
@st.cache_resource
def init_agent(api_key: str):
    """Initialize LangChain agent with tools"""
    tools = [
        search_profiles,
        get_statistics,
        get_float_details,
        query_database,
        get_profiles_by_location,
        get_profiles_by_date,
        map_profiles_by_bounds,
        plot_profile_temp_sal,
        plot_time_series,
    ]
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=api_key,
        temperature=0,
        max_retries=3,
        timeout=None
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an oceanography assistant helping users explore Argo float data.
        
You have access to tools to search profiles, get statistics, query the database, filter by location/date, and generate plots.

CRITICAL INSTRUCTIONS:
1. SEMANTIC SEARCH: If the user asks for concepts like "warm water", ALWAYS use `search_profiles` first.
2. MAP FIRST RULE: If the user asks to show profiles in a location, map, region, or latitude/longitude bounds, use `map_profiles_by_bounds` (not `get_profiles_by_location`) unless they explicitly ask for a table.
3. DATABASE SCHEMA: 
   - Table `profiles`: profile_id, float_id, cycle_number, datetime, latitude, longitude
   - Table `measurements`: float_id, profile_id, level, pressure, temperature, salinity
4. SQL RULES: Only use standard SELECT queries. Do not use PRAGMA.
5. MISSING DATA RULE: If `query_database` returns 0 rows, DO NOT try again. Simply tell the user: "I found the profile metadata, but the exact temperature measurements are currently missing from the database."

When presenting results:
- Be concise and clear
- Format data in readable Markdown tables
- If a plotting tool is used, briefly explain what the plot shows.
"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=4,
        return_intermediate_steps=True
    )
    
    return agent_executor


def invoke_agent_with_key_rotation(prompt: str):
    """Invoke agent, rotating through configured Gemini keys on quota errors."""
    if not GEMINI_API_KEYS:
        raise RuntimeError("No Gemini API keys configured.")

    key_count = len(GEMINI_API_KEYS)
    start_index = int(st.session_state.get("gemini_key_index", 0)) % key_count
    last_quota_error: Exception | None = None

    for attempt in range(key_count):
        key_index = (start_index + attempt) % key_count
        api_key = GEMINI_API_KEYS[key_index]
        executor = init_agent(api_key)
        try:
            result = executor.invoke({"input": prompt})
            st.session_state.gemini_key_index = key_index
            rotated = key_index != start_index
            return result, rotated, key_index
        except Exception as exc:
            if is_quota_error_message(str(exc)):
                last_quota_error = exc
                continue
            raise

    raise AllGeminiKeysExhaustedError(str(last_quota_error) if last_quota_error else "All configured Gemini keys are exhausted.")


if not GEMINI_API_KEYS:
    st.error("⚠️ No Gemini API keys found in environment variables!")
    st.info("Set one or more keys using `GOOGLE_API_KEY`, `GOOGLE_API_KEY_2`, ... or `GOOGLE_API_KEYS=key1,key2`.")
    st.stop()


# Sidebar
with st.sidebar:
    st.markdown("### 🌊 FloatChat RAG")
    st.markdown("Explore oceanographic data with AI")
    
    st.markdown("---")
    
    # Quick stats
    st.markdown("### 📊 Quick Stats")
    try:
        stats = cached_statistics_data()

        col1, col2 = st.columns(2)
        col1.metric("Profiles", f"{stats['profile_count']:,}")
        col2.metric("Floats", stats["float_count"])
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
        - **map_profiles_by_bounds**: Geographic map
        - **plot_profile_temp_sal**: Temp/salinity vs depth
        - **plot_time_series**: Parameter trend over time
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
for message_index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("route_mode"):
            st.caption(f"Mode: {message['route_mode']}")

        if "chart_payloads" in message and message["chart_payloads"]:
            render_chart_payloads(
                message["chart_payloads"],
                key_prefix=f"history_{message_index}_{message['role']}",
            )
        
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
                tools_used = []
                chart_payloads = []
                route_mode = "Agent"

                result, key_rotated, key_index = invoke_agent_with_key_rotation(prompt)
                response = normalize_agent_response(result.get("output"))

                if key_rotated:
                    route_mode = "Agent (Key Rotation Retry)"
                    st.warning(f"Primary Gemini key hit quota; switched to backup key #{key_index + 1} and retried successfully.")

                if "intermediate_steps" in result:
                    tools_used = [step[0].tool for step in result["intermediate_steps"]]
                chart_payloads = extract_chart_payloads(result.get("intermediate_steps", []))

                if "max iterations" in response.lower() and "agent stopped" in response.lower():
                    direct_route = try_direct_demo_route(prompt)
                    if direct_route is not None:
                        response, tools_used, chart_payloads = direct_route
                        route_mode = "Direct Tool Route (Agent Iteration Fallback)"
                        st.warning("Agent reached max iterations. Showing deterministic tool-based fallback response.")
                
                st.markdown(response)
                st.caption(f"Mode: {route_mode}")
                if chart_payloads:
                    render_chart_payloads_safe(chart_payloads, key_prefix="live_response")
                
                # Show tools used
                if tools_used:
                    tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in tools_used])
                    st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)
                
                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "tools_used": tools_used,
                    "chart_payloads": chart_payloads,
                    "route_mode": route_mode,
                })
                
            except Exception as e:
                error_text = str(e)
                all_keys_exhausted = isinstance(e, AllGeminiKeysExhaustedError)
                is_quota_error = all_keys_exhausted or is_quota_error_message(error_text)

                if is_quota_error:
                    direct_route = try_direct_demo_route(prompt)
                    if direct_route is not None:
                        response, tools_used, chart_payloads = direct_route
                        if all_keys_exhausted:
                            st.warning("All configured Gemini keys are quota-exhausted. Showing deterministic tool-based fallback response.")
                        else:
                            st.warning("Gemini quota is currently exhausted. Showing deterministic tool-based fallback response.")
                        st.markdown(response)
                        st.caption("Mode: Direct Tool Route (Quota Fallback)")
                        if chart_payloads:
                            render_chart_payloads_safe(chart_payloads, key_prefix="live_quota_fallback")
                        if tools_used:
                            tools_html = "".join([f'<span class="tool-badge">{tool}</span>' for tool in tools_used])
                            st.markdown(f"**Tools used:** {tools_html}", unsafe_allow_html=True)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "tools_used": tools_used,
                            "chart_payloads": chart_payloads,
                            "route_mode": "Direct Tool Route (Quota Fallback)",
                        })
                    else:
                        if all_keys_exhausted:
                            error_msg = (
                                "All configured Gemini API keys are currently exhausted (429 RESOURCE_EXHAUSTED). "
                                "Please retry after cooldown or add another key."
                            )
                        else:
                            error_msg = (
                                "Gemini API quota is currently exhausted (429 RESOURCE_EXHAUSTED). "
                                "Please retry after cooldown or switch API key/project."
                            )
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                else:
                    error_msg = "I hit an unexpected error while processing that request. Please try a simpler prompt or one of the example queries."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.875rem;">
    Built with Streamlit + LangChain + Google Gemini | Data from Argo Float Program
</div>
""", unsafe_allow_html=True)
