# Empathic AI Chatbot Research Platform

A production-ready research platform for comparing empathy modalities in AI-powered mental health conversations.

## 📋 Overview

This platform enables researchers to compare four distinct empathy approaches in AI chatbot conversations:
- **Emotional Empathy**: Feeling with users through emotional resonance
- **Cognitive Empathy**: Understanding perspectives through logical analysis
- **Motivational Empathy**: Empowering users toward positive change
- **Neutral Control**: Standard AI without specialized empathy training

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- API key from OpenAI

### Installation

1. **Clone or download the project**
```bash
cd empathic_ai_research

https://empathic-ai-research-bxpwkxy7gbmbpxvlwybpp9.streamlit.app/

streamlit run src/app.py  #Run the participant chat app

streamlit run admin_app.py  #Run the admin dashboard (local)

python scripts\setup_database.py --verify  #Verify remote DB (Postgres, e.g., Supabase)

python .\check_database.py  #Verify local SQLite (when no DATABASE_URL is set)

python .\tests\test_async_db.py  #Async Postgres connectivity sanity check (managed Postgres, e.g., Supabase)

python scripts\setup_database.py --reset --yes  #Local SQLite reset