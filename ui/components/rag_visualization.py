# ui/components/rag_visualization.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import json

from ui.state_manager import state_manager
from ui.components.common import display_error, display_info
from config.logging_config import get_module_logger

# Create a logger for this module
logger = get_module_logger("rag_visualization")

def render_rag_analytics_tab(app_components: Dict[str, Any]):
    """Render the RAG analytics and visualization tab.
    
    Args:
        app_components: Dictionary with application components
    """
    st.header("RAG Pipeline Analytics")
    
    # Check if RAG pipeline is initialized
    rag_chain = app_components.get("rag_chain")
    if not rag_chain:
        display_info("RAG pipeline not initialized. Please initialize the pipeline first.")
        return
    
    # Create tabs for different visualizations
    viz_tabs = st.tabs(["Pipeline Overview", "Document Retrieval", "Performance", "Debug"])
    
    with viz_tabs[0]:
        render_pipeline_overview(app_components)
    
    with viz_tabs[1]:
        render_retrieval_analysis(app_components)
    
    with viz_tabs[2]:
        render_performance_analysis(app_components)
    
    with viz_tabs[3]:
        render_debug_info(app_components)

def render_pipeline_overview(app_components: Dict[str, Any]):
    """Render the RAG pipeline overview.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("RAG Pipeline Overview")
    
    # Get pipeline components
    rag_chain = app_components.get("rag_chain")
    vector_store = app_components.get("vector_store")
    
    # Create metrics row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Count documents in vector store
        doc_count = 0
        if vector_store and hasattr(vector_store, "vectorstore"):
            if hasattr(vector_store.vectorstore, "_collection"):
                try:
                    doc_count = vector_store.vectorstore._collection.count()
                except:
                    pass
        
        st.metric(
            label="Documents in Index",
            value=doc_count
        )
    
    with col2:
        # Count queries processed
        queries = state_manager.get("rag_queries", [])
        
        st.metric(
            label="Queries Processed",
            value=len(queries)
        )
    
    with col3:
        # Average query time
        avg_time = 0
        if queries:
            times = [q.get("execution_time", 0) for q in queries]
            if times:
                avg_time = sum(times) / len(times)
        
        st.metric(
            label="Avg. Query Time",
            value=f"{avg_time:.2f}s"
        )
    
    # Draw pipeline flow diagram
    st.subheader("Pipeline Flow")
    
    # Create and display the pipeline diagram using Plotly
    fig = create_pipeline_diagram()
    st.plotly_chart(fig, use_container_width=True)
    
    # Component details
    with st.expander("Pipeline Component Details", expanded=False):
        st.json({
            "LLM Model": getattr(rag_chain, "model_name", "Unknown") if rag_chain else "Not initialized",
            "Vector Store Type": type(vector_store).__name__ if vector_store else "Not initialized",
            "Retrieval Strategy": "Similarity Search",
            "Document Count": doc_count,
            "Pipeline Status": "Operational" if rag_chain else "Not initialized"
        })

def create_pipeline_diagram():
    """Create a pipeline flow diagram.
    
    Returns:
        Plotly figure
    """
    # Create a Sankey diagram for the RAG pipeline
    labels = ["Document", "Chunking", "Embedding", "Vector DB", "Query", "Retrieval", "LLM", "Response"]
    
    # Define the source and target for each link
    source = [0, 1, 2, 4, 3, 5, 6]
    target = [1, 2, 3, 5, 5, 6, 7]
    
    # Define the value (thickness) of each link
    value = [1, 1, 1, 1, 1, 1, 1]
    
    # Define colors for the links
    colors = ["rgba(31, 119, 180, 0.4)", "rgba(31, 119, 180, 0.4)", 
              "rgba(31, 119, 180, 0.4)", "rgba(255, 127, 14, 0.4)", 
              "rgba(31, 119, 180, 0.4)", "rgba(31, 119, 180, 0.4)", 
              "rgba(31, 119, 180, 0.4)"]
    
    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
          pad=15,
          thickness=20,
          line=dict(color="black", width=0.5),
          label=labels
        ),
        link=dict(
          source=source,
          target=target,
          value=value,
          color=colors
        )
    )])
    
    # Update the layout
    fig.update_layout(
        title_text="RAG Pipeline Flow",
        font_size=12,
        height=400
    )
    
    return fig

def render_retrieval_analysis(app_components: Dict[str, Any]):
    """Render the document retrieval analysis.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("Document Retrieval Analysis")
    
    # Get queries from state
    queries = state_manager.get("rag_queries", [])
    
    if not queries:
        st.info("No queries have been processed yet.")
        return
    
    # Create metrics row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Average documents retrieved
        avg_docs = 0
        if queries:
            doc_counts = [len(q.get("source_documents", [])) for q in queries]
            if doc_counts:
                avg_docs = sum(doc_counts) / len(doc_counts)
        
        st.metric(
            label="Avg. Docs Retrieved",
            value=f"{avg_docs:.1f}"
        )
    
    with col2:
        # Top document source
        doc_sources = {}
        for q in queries:
            for doc in q.get("source_documents", []):
                source = doc.metadata.get("source", "Unknown")
                doc_sources[source] = doc_sources.get(source, 0) + 1
        
        top_source = max(doc_sources.items(), key=lambda x: x[1])[0] if doc_sources else "None"
        
        st.metric(
            label="Top Document Source",
            value=top_source
        )
    
    with col3:
        # Zero result queries
        zero_docs = sum(1 for q in queries if len(q.get("source_documents", [])) == 0)
        zero_pct = (zero_docs / len(queries)) * 100 if queries else 0
        
        st.metric(
            label="Zero Result Queries",
            value=f"{zero_pct:.1f}%"
        )
    
    # Create a documents by query visualization
    st.subheader("Documents Retrieved by Query")
    
    # Prepare data
    query_data = []
    for i, q in enumerate(queries[-10:], 1):  # Show only the last 10 queries
        query_text = q.get("metadata", {}).get("query", f"Query {i}")
        query_text = query_text[:50] + "..." if len(query_text) > 50 else query_text
        doc_count = len(q.get("source_documents", []))
        query_data.append({"Query": query_text, "Documents": doc_count})
    
    if query_data:
        df = pd.DataFrame(query_data)
        fig = px.bar(df, x="Query", y="Documents", title="Documents Retrieved per Query")
        st.plotly_chart(fig, use_container_width=True)
    
    # Show distribution of document sources
    if doc_sources:
        st.subheader("Document Source Distribution")
        source_df = pd.DataFrame({"Source": list(doc_sources.keys()), "Count": list(doc_sources.values())})
        fig = px.pie(source_df, values="Count", names="Source", title="Document Sources")
        st.plotly_chart(fig, use_container_width=True)

def render_performance_analysis(app_components: Dict[str, Any]):
    """Render the performance analysis.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("RAG Performance Analysis")
    
    # Get queries from state
    queries = state_manager.get("rag_queries", [])
    
    if not queries:
        st.info("No queries have been processed yet.")
        return
    
    # Create metrics row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Total execution time
        total_time = sum(q.get("execution_time", 0) for q in queries)
        
        st.metric(
            label="Total Execution Time",
            value=f"{total_time:.2f}s"
        )
    
    with col2:
        # Average execution time
        avg_time = total_time / len(queries) if queries else 0
        
        st.metric(
            label="Avg. Execution Time",
            value=f"{avg_time:.2f}s"
        )
    
    with col3:
        # Max execution time
        max_time = max(q.get("execution_time", 0) for q in queries) if queries else 0
        
        st.metric(
            label="Max Execution Time",
            value=f"{max_time:.2f}s"
        )
    
    # Create execution time trend chart
    st.subheader("Execution Time Trend")
    
    # Prepare data
    time_data = []
    for i, q in enumerate(queries, 1):
        time_data.append({"Query Index": i, "Execution Time (s)": q.get("execution_time", 0)})
    
    if time_data:
        df = pd.DataFrame(time_data)
        fig = px.line(df, x="Query Index", y="Execution Time (s)", title="Query Execution Time Trend")
        st.plotly_chart(fig, use_container_width=True)
    
    # Create a histogram of execution times
    st.subheader("Execution Time Distribution")
    
    if time_data:
        times = [q.get("execution_time", 0) for q in queries]
        fig = px.histogram(times, title="Execution Time Distribution")
        fig.update_layout(xaxis_title="Execution Time (s)", yaxis_title="Frequency")
        st.plotly_chart(fig, use_container_width=True)

def render_debug_info(app_components: Dict[str, Any]):
    """Render debug information for the RAG pipeline.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("RAG Pipeline Debug Information")
    
    # Get pipeline components
    rag_chain = app_components.get("rag_chain")
    vector_store = app_components.get("vector_store")
    
    # Show the most recent query with details
    st.write("### Most Recent Query")
    
    queries = state_manager.get("rag_queries", [])
    if queries:
        latest_query = queries[-1]
        
        # Show query details
        st.write(f"**Query:** {latest_query.get('metadata', {}).get('query', 'Unknown')}")
        st.write(f"**Execution Time:** {latest_query.get('execution_time', 0):.4f}s")
        st.write(f"**Documents Retrieved:** {len(latest_query.get('source_documents', []))}")
        
        # Show source documents
        with st.expander("Source Documents", expanded=False):
            for i, doc in enumerate(latest_query.get("source_documents", []), 1):
                st.markdown(f"**Document {i}**")
                st.write(f"Source: {doc.metadata.get('source', 'Unknown')}")
                st.text(doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content)
                st.markdown("---")
        
        # Show generated response
        with st.expander("Generated Response", expanded=False):
            st.markdown(latest_query.get("result", "No response available"))
    else:
        st.info("No queries have been processed yet.")
    
    # Add a manual query execution tool for debugging
    st.write("### Debug Query Tool")
    debug_query = st.text_area("Enter a query to test", placeholder="Enter your query here...")
    
    if st.button("Execute Debug Query"):
        if debug_query and rag_chain:
            with st.spinner("Processing debug query..."):
                try:
                    # Record start time
                    start_time = __import__('time').time()
                    
                    # Execute query
                    response = rag_chain.run(debug_query)
                    
                    # Calculate execution time
                    execution_time = __import__('time').time() - start_time
                    
                    # Store in state
                    if "rag_queries" not in state_manager.get_state():
                        state_manager.set("rag_queries", [])
                    
                    # Add to queries
                    state_manager.append("rag_queries", response)
                    
                    # Display results
                    st.success(f"Query executed in {execution_time:.4f}s")
                    st.rerun()
                except Exception as e:
                    display_error(f"Error executing query: {str(e)}")
        else:
            display_error("Please enter a query and ensure RAG pipeline is initialized")
    
    # System information
    with st.expander("System Information", expanded=False):
        system_info = {
            "Vector Store Type": type(vector_store).__name__ if vector_store else "Not initialized",
            "LLM Provider": "OpenAI" if rag_chain else "Not initialized",
            "Total Queries": len(queries),
            "Index Size": f"{doc_count} documents" if 'doc_count' in locals() else "Unknown",
            "Python Version": __import__('sys').version,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        st.json(system_info)
    
    # Add a button to clear RAG query history
    if st.button("Clear RAG Query History"):
        state_manager.set("rag_queries", [])
        st.success("RAG query history cleared")
        st.rerun()