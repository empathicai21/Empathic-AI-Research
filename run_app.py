"""
Application Launcher
Starts the participant-facing Streamlit application.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first (e.g., OPENAI_API_KEY, DATABASE_URL)
# For Supabase (Postgres), include sslmode=require in DATABASE_URL if needed
load_dotenv()

# Add src directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """
    Check if environment is properly configured.
    Verifies required files and environment variables exist.
    """
    errors = []
    
    # Check if .env file exists
    env_file = project_root / '.env'
    if not env_file.exists():
        errors.append("❌ .env file not found. Copy .env.template to .env and add your API key.")
    
    # Check if config exists
    config_file = project_root / 'config' / 'app_config.yaml'
    if not config_file.exists():
        errors.append("❌ config/app_config.yaml not found.")
    
    # Check if database directory exists
    db_dir = project_root / 'data' / 'database'
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Created database directory")
    
    # Check if exports directory exists
    export_dir = project_root / 'data' / 'exports'
    if not export_dir.exists():
        export_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Created exports directory")
    
    # Report errors
    if errors:
        print("\n⚠️  CONFIGURATION ERRORS:\n")
        for error in errors:
            print(f"  {error}")
        print("\nPlease fix these issues before running the app.\n")
        return False
    
    return True


def main():
    """Main launcher function."""
    print("=" * 60)
    print("EMPATHIC AI RESEARCH PLATFORM")
    print("=" * 60)
    print()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("✓ Environment check passed")
    print("✓ Starting Streamlit application...")
    print()
    print("The application will open in your default web browser.")
    print("Press Ctrl+C to stop the application.")
    print()
    print("=" * 60)
    print()
    
    # Run Streamlit app
    os.system('streamlit run src/app.py')


if __name__ == "__main__":
    main()