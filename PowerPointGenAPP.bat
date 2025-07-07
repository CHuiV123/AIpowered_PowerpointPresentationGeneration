@echo off
start cmd /k uvicorn ppt_api:app --reload --port 8080
start cmd /k streamlit run streamlit_app.py

