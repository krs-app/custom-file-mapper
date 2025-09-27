import streamlit as st
import openai
import json
import pandas as pd
from PyPDF2 import PdfReader

st.set_page_config(page_title="GRC JSON Extractor", layout="wide")
st.title("GRC JSON Extractor with Function Calling")

# Input OpenAI API key
openai.api_key = st.text_input("Enter your OpenAI API Key", type="password")

# File uploader (multiple files)
uploaded_files = st.file_uploader(
    "Upload PDFs or Excel files",
    type=["pdf", "xlsx"],
    accept_multiple_files=True
)

def extract_file_content(f):
    """Extract text from PDF or Excel"""
    if f.name.endswith(".pdf"):
        reader = PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    elif f.name.endswith(".xlsx"):
        xls = pd.ExcelFile(f)
        sheets_content = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
            sheets_content[sheet] = df.fillna("").to_dict(orient="records")
        return sheets_content
    else:
        return ""

def post_process_questionnaire(data_json):
    """Ensure same Question ID for same questions and sort answers by sentiment"""
    question_map = {}
    counter = 1

    for q in data_json.get("New Questions Creation", []):
        title = q["Question Title"].strip()
        # Assign Question ID if new
        if title not in question_map:
            question_map[title] = f"N_{counter:02d}"
            counter += 1
        q["Question ID"] = question_map[title]

        # Assign Answer Sequence based on Answer Sentiment
        sentiment = q.get("Answer Sentiment", "Neutral")
        if sentiment == "Positive":
            q["Answer Sequence"] = 1
        elif sentiment == "Negative":
            q["Answer Sequence"] = 2
        else:
            q["Answer Sequence"] = 3

    # Sort answers so Positive -> Negative -> Neutral
    data_json["New Questions Creation"].sort(key=lambda x: x["Answer Sequence"])
    return data_json

# Button to process files
if st.button("Generate JSON") and uploaded_files and openai.api_key:
    files_content = []
    for f in uploaded_files:
        content = extract_file_content(f)
        files_content.append({"filename": f.name, "content": content})

    # Build the user prompt
    user_prompt = f"""
    You are a GRC expert. You are tasked with generating ONE combined questionnaire 
    based on all uploaded files (PDFs and Excel sheets). Do NOT create separate 
    questionnaires per file or sheet. Merge all relevant AD, Citations, Controls, 
    Questions, Expected Answers, and Scores into a single questionnaire JSON. 

    Follow the JSON schema strictly.

    Rules:
    1. Auto-fill Question IDs with prefix 'N_' in incremental order (N_01, N_02, ...). 
       - Same question gets same Question ID.
    2. Include 'Answer Sentiment' for each answer: Positive, Negative, Neutral.
    3. Assign Answer Sequence based on sentiment: Positive -> 1, Negative -> 2, Neutral -> 3.
    4. Only one questionnaire output is allowed.
    5. Strictly follow the schema: Questionnaire, Questionnaire Sections, New AD-Citation-Control, New Questions Creation.

    Files uploaded (partial content for context):
    {json.dumps([{f['filename']: str(f['content'])[:2000]} for f in files_content], indent=2)}
    """

    # Define the function schema
    function_schema = {
        "name": "return_questionnaire",
        "description": "Return the final questionnaire JSON exactly matching schema",
        "parameters": {
            "type": "object",
            "properties": {
                "Questionnaire": {"type": "array"},
                "Questionnaire Sections": {"type": "array"},
                "New AD-Citation-Control": {"type": "array"},
                "New Questions Creation": {"type": "array"}
            },
            "required": ["Questionnaire","Questionnaire Sections","New Questions Creation"]
        }
    }

    try:
        # Call GPT function
        response = openai.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": user_prompt}],
            functions=[function_schema],
            function_call={"name": "return_questionnaire"}
        )

        # Extract JSON from function call
        function_response = response.choices[0].message.function_call.arguments
        result_json = json.loads(function_response)

        # Post-process Question IDs and Answer Sequence
        result_json = post_process_questionnaire(result_json)

        st.subheader("Parsed JSON")
        st.json(result_json)

    except Exception as e:
        st.error(f"Error parsing JSON: {e}")
