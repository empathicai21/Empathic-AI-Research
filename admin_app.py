"""
Admin Dashboard Streamlit App
Direct dashboard for viewing research data.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import streamlit as st

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables (DATABASE_URL, etc.)
# For managed Postgres (e.g., Supabase), ensure TLS (sslmode=require)
load_dotenv()
from src.database.db_manager import DatabaseManager
from src.ui.admin_dashboard import run_admin_dashboard

# Initialize database manager
db_manager = DatabaseManager("data/database/conversations.db")


def main():
    # Configure page
    st.set_page_config(page_title="Research Dashboard", page_icon="📊", layout="wide")

    admin_password = os.getenv("ADMIN_PASSWORD")

    # If a password is set, gate access and persist login in session_state
    if admin_password:
        if "admin_authenticated" not in st.session_state:
            st.session_state.admin_authenticated = False

        if not st.session_state.admin_authenticated:
            st.title("🔒 Admin Dashboard Login")
            pwd = st.text_input("Password", type="password")
            if st.button("Login"):
                if pwd == admin_password:
                    st.session_state.admin_authenticated = True
                    st.rerun()  # proceed to dashboard
                else:
                    st.error("Invalid password")
            # Stop rendering until authenticated
            return

    # Optional logout control in the sidebar
    with st.sidebar:
        if admin_password and st.session_state.get("admin_authenticated"):
            if st.button("Logout"):
                st.session_state.admin_authenticated = False
                st.rerun()

    # Render the dashboard (authenticated or no password set)
    run_admin_dashboard(db_manager)


if __name__ == "__main__":
    main()