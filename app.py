import streamlit as st
import json
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import sys
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Outreach AI Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define paths
RESULTS_DIR = Path("outreach_results")
ALL_RESULTS_FILE = RESULTS_DIR / "all_results.json"
PROGRESS_FILE = RESULTS_DIR / "progress.txt"

# Create results directory if it doesn't exist
os.makedirs(RESULTS_DIR, exist_ok=True)

# Helper functions
def load_results():
    """Load current results from JSON file"""
    if ALL_RESULTS_FILE.exists():
        with open(ALL_RESULTS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def load_progress():
    """Load the progress log"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return f.read()
    return ""

def run_outreach_process():
    """Run the outreach process in the background"""
    try:
        st.session_state.process = subprocess.Popen(
            [sys.executable, "-m", "outreach_ai.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        st.session_state.process_running = True
        st.session_state.output_lines = []
    except Exception as e:
        st.error(f"Failed to start process: {str(e)}")
        st.session_state.process_running = False

# Initialize session state
if 'process_running' not in st.session_state:
    st.session_state.process_running = False
if 'process' not in st.session_state:
    st.session_state.process = None
if 'output_lines' not in st.session_state:
    st.session_state.output_lines = []
if 'show_tab' not in st.session_state:
    st.session_state.show_tab = "dashboard"

# Sidebar for controls
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/mail-automation.png", width=80)
    st.title("Outreach AI")
    
    st.header("Navigation")
    tabs = ["Dashboard", "Companies", "Contacts", "Emails", "Logs", "Settings"]
    selected_tab = st.radio("Select", tabs, key="tab_selector")
    st.session_state.show_tab = selected_tab.lower()
    
    st.markdown("---")
    
    st.header("Controls")
    
    if not st.session_state.process_running:
        if st.button("▶️ Start Outreach Process", use_container_width=True):
            run_outreach_process()
    else:
        if st.button("⏹️ Stop Process", use_container_width=True):
            if st.session_state.process:
                st.session_state.process.terminate()
                st.session_state.process_running = False
                st.session_state.process = None
                st.success("Process stopped")
    
    st.markdown("---")
    
    # In the sidebar of app.py
with st.sidebar:
    st.header("Filters")
    excluded_locations = st.multiselect(
        "Exclude Locations", 
        ["New York", "Midwest", "California", "Texas", "Remote"],
        default=["New York", "Midwest"]
    )

    # When starting the process
    if st.button("Start Process"):
        # Pass filters as environment variables
        os.environ["EXCLUDED_LOCATIONS"] = json.dumps(excluded_locations)
        run_outreach_process()

    
    st.header("Upload")
    uploaded_excel = st.file_uploader("Companies Excel", type=["xlsx"])
    if uploaded_excel:
        # Save the uploaded file
        with open("outreach_ai/data/companies.xlsx", "wb") as f:
            f.write(uploaded_excel.getbuffer())
        st.success("Excel file uploaded successfully!")
    
    with st.expander("Upload Resumes"):
        uploaded_resume = st.file_uploader("Resume Files", type=["pdf", "docx"], accept_multiple_files=True)
        if uploaded_resume:
            # Ensure resume directory exists
            os.makedirs("outreach_ai/resumes", exist_ok=True)
            
            # Save each uploaded resume
            for resume in uploaded_resume:
                with open(f"outreach_ai/resumes/{resume.name}", "wb") as f:
                    f.write(resume.getbuffer())
            st.success(f"{len(uploaded_resume)} resume(s) uploaded successfully!")

# Main content area
if st.session_state.show_tab == "dashboard":
    # Dashboard Tab
    st.title("Dashboard")
    
    # Top metrics
    results = load_results()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Companies", len(results))
    
    with col2:
        successful = sum(1 for r in results if r.get("status") in ["success", "partial"])
        st.metric("Successful Companies", successful)
    
    with col3:
        contacts = sum(r.get("contacts_processed", 0) for r in results)
        st.metric("Total Contacts", contacts)
    
    with col4:
        emails_sent = sum(r.get("contacts_successful", 0) for r in results)
        st.metric("Emails Sent", emails_sent)
    
    # Progress bar
    if results:
        st.subheader("Overall Progress")
        progress_pct = successful / len(results) if len(results) > 0 else 0
        st.progress(progress_pct)
        st.caption(f"{progress_pct:.1%} Complete")
    
    # Charts and visualizations
    st.subheader("Status Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if results:
            status_counts = {}
            for r in results:
                status = r.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.pie(
                status_counts.values(), 
                labels=status_counts.keys(), 
                autopct='%1.1f%%',
                colors=['#4CAF50', '#FFC107', '#F44336', '#9C27B0']
            )
            ax.set_title("Company Status")
            st.pyplot(fig)
        else:
            st.info("No data available yet")
    
    with col2:
        if st.session_state.process_running:
            st.subheader("Process Status")
            st.success("Outreach process is running")
            
            # Read the last few lines of the progress file
            progress_text = load_progress()
            last_lines = "\n".join(progress_text.split("\n")[-10:])
            st.text_area("Recent Progress", last_lines, height=200)
        else:
            st.subheader("Process Status")
            st.warning("Outreach process is not running")
            st.caption("Click 'Start Outreach Process' in the sidebar to begin")

elif st.session_state.show_tab == "companies":
    # Companies Tab
    st.title("Companies Status")
    
    results = load_results()
    
    if results:
        # Convert to DataFrame for display
        df = pd.DataFrame(results)
        
        # Clean up columns
        display_columns = ["company", "status", "contacts_processed", "contacts_successful"]
        display_df = df[display_columns].copy() if all(col in df.columns for col in display_columns) else df
        
        # Add color coding
        def color_status(val):
            if val == "success":
                return "background-color: #d4edda"
            elif val == "partial":
                return "background-color: #fff3cd"
            elif val == "failed":
                return "background-color: #f8d7da"
            else:
                return ""
        
        # Show the styled dataframe
        st.dataframe(
            display_df.style.applymap(color_status, subset=["status"]),
            use_container_width=True,
            height=400
        )
        
        # Company details section
        if display_df.shape[0] > 0:
            st.subheader("Company Details")
            selected_company = st.selectbox(
                "Select a company to view details",
                options=display_df["company"].tolist()
            )
            
            # Show selected company details
            company_data = next((r for r in results if r.get("company") == selected_company), None)
            if company_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.json(company_data)
                
                with col2:
                    st.subheader("Contact Results")
                    if "contact_results" in company_data:
                        for idx, contact in enumerate(company_data["contact_results"]):
                            with st.expander(f"Contact {idx+1}: {contact.get('contact', {}).get('name', 'Unknown')}"):
                                st.json(contact)
    else:
        st.info("No company data available yet")

elif st.session_state.show_tab == "contacts":
    # Contacts Tab
    st.title("All Contacts")
    
    # Get all contact data from individual files
    contacts_dir = RESULTS_DIR / "contacts"
    all_contacts = []
    
    if contacts_dir.exists():
        contact_files = list(contacts_dir.glob("*.json"))
        
        for file in contact_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    if "key_contacts" in data:
                        company_name = data.get("company", file.stem)
                        for contact in data["key_contacts"]:
                            contact["company"] = company_name
                            all_contacts.append(contact)
            except:
                pass
    
    if all_contacts:
        # Convert to DataFrame
        contacts_df = pd.DataFrame(all_contacts)
        
        # Show table
        st.dataframe(contacts_df, use_container_width=True)
        
        # Export option
        if st.button("Export Contacts CSV"):
            csv = contacts_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "contacts.csv",
                "text/csv",
                key='download-csv'
            )
    else:
        st.info("No contacts found yet")

elif st.session_state.show_tab == "emails":
    # Emails Tab
    st.title("Sent Emails")
    
    # Get all email data from individual files
    emails_dir = RESULTS_DIR / "emails"
    all_emails = []
    
    if emails_dir.exists() and emails_dir.is_dir():
        email_files = list(emails_dir.glob("*.json"))
        
        for file in email_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    data["filename"] = file.stem
                    all_emails.append(data)
            except:
                pass
    
    if all_emails:
        # Show email list
        for idx, email in enumerate(all_emails):
            with st.expander(f"Email {idx+1}: {email.get('subject', 'No Subject')}"):
                st.write(f"**To:** {email.get('to', 'Unknown')}")
                st.write(f"**Subject:** {email.get('subject', 'No Subject')}")
                st.write(f"**Resume:** {email.get('resume', 'None')}")
                st.write(f"**Status:** {email.get('status', 'Unknown')}")
                st.write(f"**Sent at:** {email.get('timestamp', 'Unknown')}")
                
                st.write("**Body:**")
                st.text_area("", email.get("body", ""), height=200, key=f"email_body_{idx}")
    else:
        st.info("No emails sent yet")

elif st.session_state.show_tab == "logs":
    # Logs Tab
    st.title("Process Logs")
    
    # Display the progress file
    progress_text = load_progress()
    
    if progress_text:
        st.text_area("Progress Log", progress_text, height=600)
        
        if st.button("Refresh Logs"):
            st.experimental_rerun()
    else:
        st.info("No logs available yet")
    
    # Live process output if running
    if st.session_state.process_running and st.session_state.process:
        st.subheader("Live Process Output")
        
        output_container = st.empty()
        
        # Read output lines from subprocess
        while st.session_state.process.poll() is None:
            line = st.session_state.process.stdout.readline()
            if line:
                st.session_state.output_lines.append(line.strip())
                output_container.text_area(
                    "Output", 
                    "\n".join(st.session_state.output_lines[-100:]),
                    height=400
                )
            time.sleep(0.1)
        
        # Process has completed
        st.session_state.process_running = False
        st.success("Process completed")

elif st.session_state.show_tab == "settings":
    # Settings Tab
    st.title("Settings")
    
    with st.form("settings_form"):
        st.subheader("Email Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            email_address = st.text_input("Email Address", value=os.getenv("EMAIL_ADDRESS", ""))
            smtp_server = st.text_input("SMTP Server", value=os.getenv("SMTP_SERVER", "smtp.gmail.com"))
        
        with col2:
            email_password = st.text_input("Email Password", type="password", value="*********")
            smtp_port = st.text_input("SMTP Port", value=os.getenv("SMTP_PORT", "587"))
        
        st.subheader("Process Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            use_local_llm = st.checkbox("Use Local LLM", value=True)
            local_llm_model = st.text_input("Local LLM Model", value=os.getenv("LOCAL_LLM_MODEL", "mistral:latest"))
        
        with col2:
            delay_min = st.number_input("Min Delay (seconds)", value=30, min_value=5)
            delay_max = st.number_input("Max Delay (seconds)", value=60, min_value=10)
        
        submit = st.form_submit_button("Save Settings")
        
        if submit:
            # Update .env file with new settings
            env_content = [
                f"EMAIL_ADDRESS={email_address}",
                f"SMTP_SERVER={smtp_server}",
                f"SMTP_PORT={smtp_port}",
                f"USE_LOCAL_LLM={'true' if use_local_llm else 'false'}",
                f"LOCAL_LLM_MODEL={local_llm_model}",
                f"DELAY_MIN={delay_min}",
                f"DELAY_MAX={delay_max}"
            ]
            
            # Keep existing EMAIL_PASSWORD if not changed
            if email_password != "*********":
                env_content.append(f"EMAIL_PASSWORD={email_password}")
            
            # Write to .env file
            with open(".env", "w") as f:
                f.write("\n".join(env_content))
            
            st.success("Settings saved!")
    
    # Test SMTP Connection
    st.subheader("Test Email Connection")
    test_email = st.text_input("Test Email Address")
    
    if st.button("Test Connection"):
        if test_email:
            with st.spinner("Testing connection..."):
                try:
                    # Import the send_email function
                    sys.path.append(".")
                    from outreach_ai.agents.send_email import send_email
                    
                    result = send_email(
                        recipient_email=test_email,
                        subject="Test Email from Outreach AI",
                        body_text="This is a test email from your Outreach AI application.",
                        attachment_path=None
                    )
                    
                    if result:
                        st.success("Test email sent successfully!")
                    else:
                        st.error("Failed to send test email. Check your SMTP settings.")
                except Exception as e:
                    st.error(f"Error testing email: {str(e)}")
        else:
            st.warning("Please enter a test email address")

# Footer
st.markdown("---")
st.caption("Outreach AI Dashboard | Created with Streamlit")