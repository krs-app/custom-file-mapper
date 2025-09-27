import streamlit as st
import openai
import json
import os

st.title("GRC JSON Extractor")

# Input OpenAI API key
openai.api_key = st.text_input("Enter your OpenAI API Key", type="password")

# File uploader (multiple files)
uploaded_files = st.file_uploader(
    "Upload PDFs or Excel files",
    type=["pdf", "xlsx"],
    accept_multiple_files=True
)

# Button to process files
if st.button("Generate JSON") and uploaded_files:
    # Read files
    files_content = []
    for f in uploaded_files:
        content = f.read()
        files_content.append({"filename": f.name, "content": content.decode("latin1")})

    # Build prompt for ChatGPT
    prompt = f"""
    You are a GRC expert. Analyze the following files and return JSON matching the schema:
    Files: {', '.join([f['filename'] for f in files_content])}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result_text = response.choices[0].message.content
        st.subheader("Raw JSON from ChatGPT")
        st.code(result_text)

        # Try to parse JSON
        result_json = json.loads(result_text)
        st.subheader("Parsed JSON")
        st.json(result_json)

    except Exception as e:
        st.error(f"Error: {e}")
