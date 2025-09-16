"""
Main Streamlit application for the Clinic Synthesizer Operator.
Provides UI for manifest submission and synthesis job management.
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

from .db import query_all, query_one, execute, DatabaseError
from .http import billing_client, review_client, HTTPError
from .manifest_validation import validate_manifest, ManifestValidationError

# Page config
st.set_page_config(
    page_title="Clinic Synthesizer Operator",
    page_icon="🏥",
    layout="wide"
)

# Helper functions
def load_jobs() -> pd.DataFrame:
    """Load synthesis jobs from database."""
    try:
        jobs = query_all("""
            SELECT 
                job_id,
                clinic_name,
                status,
                created_at,
                completed_at,
                record_count,
                error_message
            FROM synthesis_jobs
            ORDER BY created_at DESC
        """)
        return pd.DataFrame(jobs)
    except DatabaseError as e:
        st.error(f"Failed to load jobs: {str(e)}")
        return pd.DataFrame()

def submit_job(manifest: dict) -> None:
    """Submit a new synthesis job."""
    try:
        # Validate manifest
        validate_manifest(manifest)
        
        # Check billing status
        billing_status = billing_client.get(f"/clinics/{manifest['clinic_name']}/billing")
        if not billing_status.get("active"):
            st.error("Clinic billing status is not active")
            return
            
        # Submit for review
        review = review_client.post("/reviews", json={
            "clinic_name": manifest["clinic_name"],
            "manifest": manifest
        })
        
        if review["status"] == "approved":
            # Create job record
            execute("""
                INSERT INTO synthesis_jobs 
                (clinic_name, status, record_count, manifest)
                VALUES (%s, 'pending', %s, %s)
            """, (
                manifest["clinic_name"],
                manifest["record_count"],
                manifest
            ))
            st.success("Job submitted successfully!")
        else:
            st.warning(f"Review status: {review['status']}\nReason: {review.get('reason', 'No reason provided')}")
            
    except ManifestValidationError as e:
        st.error("Invalid manifest:")
        for err in e.validation_errors:
            st.error(f"- {err}")
            
    except HTTPError as e:
        st.error(f"API error: {str(e)}")
        if e.response_text:
            st.error(f"Response: {e.response_text}")
            
    except DatabaseError as e:
        st.error(f"Database error: {str(e)}")

# Main UI
st.title("Clinic Synthesizer Operator")

# Job submission form
with st.expander("Submit New Job", expanded=True):
    st.write("Create a new synthesis job by providing a manifest:")
    
    # Basic form fields
    clinic_name = st.text_input("Clinic Name")
    record_count = st.number_input("Number of Records", min_value=1, value=100)
    output_format = st.selectbox("Output Format", ["csv", "json", "parquet"])
    
    # Dynamic patient requirements
    st.subheader("Patient Requirements")
    requirements = []
    
    for i in range(st.number_input("Number of Patient Types", min_value=1, value=1, max_value=10)):
        st.write(f"Patient Type {i+1}")
        col1, col2 = st.columns(2)
        
        with col1:
            min_age = st.number_input(f"Min Age #{i+1}", min_value=0, value=18)
            conditions = st.text_input(f"Conditions #{i+1} (comma-separated)")
            
        with col2:
            max_age = st.number_input(f"Max Age #{i+1}", min_value=0, value=65)
            medications = st.text_input(f"Medications #{i+1} (comma-separated)", value="")
        
        requirements.append({
            "age_range": {"min": min_age, "max": max_age},
            "conditions": [c.strip() for c in conditions.split(",") if c.strip()],
            "medications": [m.strip() for m in medications.split(",") if m.strip()]
        })
    
    if st.button("Submit Job"):
        manifest = {
            "clinic_name": clinic_name,
            "record_count": record_count,
            "output_format": output_format,
            "patient_requirements": requirements
        }
        submit_job(manifest)

# Job status dashboard
st.subheader("Synthesis Jobs")
jobs_df = load_jobs()

if not jobs_df.empty:
    # Status counts
    status_counts = jobs_df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    
    st.write("Job Status Overview")
    chart = alt.Chart(status_counts).mark_bar().encode(
        x="status",
        y="count",
        color="status"
    ).properties(height=200)
    st.altair_chart(chart, use_container_width=True)
    
    # Jobs table
    st.write("Recent Jobs")
    st.dataframe(
        jobs_df,
        column_config={
            "created_at": st.column_config.DatetimeColumn("Created"),
            "completed_at": st.column_config.DatetimeColumn("Completed"),
            "status": st.column_config.SelectboxColumn(
                "Status",
                help="Current job status",
                width="small",
                options=["pending", "running", "completed", "failed"]
            )
        },
        hide_index=True
    )
else:
    st.info("No jobs found")