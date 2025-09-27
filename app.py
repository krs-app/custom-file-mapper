import streamlit as st
import openai
import json

st.title("GRC JSON Extractor with Function Calling 1")

# Input OpenAI API key
openai.api_key = st.text_input("Enter your OpenAI API Key", type="password")

# File uploader (multiple files)
uploaded_files = st.file_uploader(
    "Upload PDFs or Excel files",
    type=["pdf", "xlsx"],
    accept_multiple_files=True
)

if st.button("Generate JSON") and uploaded_files:
    files_content = []
    for f in uploaded_files:
        content = f.read()
        try:
            content_text = content.decode("latin1")
        except Exception:
            content_text = str(content)
        files_content.append({"filename": f.name, "content": content_text})

    user_prompt = f"""
    You are a GRC expert. Analyze the following files and return JSON exactly matching the schema.
    Files: {', '.join([f['filename'] for f in files_content])}
    """

    # Function schema compatible with OpenAI
    function_schema = {
        "name": "return_questionnaire",
        "description": "Return the final questionnaire JSON exactly matching schema",
        "parameters": {
            "type": "object",
            "properties": {
                "Questionnaire": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Questionnaire Name": {"type": "string", "minLength": 1},
                            "Assessment Based on": {"type": "string", "enum": ["Citations", "Controls"]},
                            "Add New Controls/Citations": {"type": "string", "enum": ["Yes", "No"]},
                            "Add New Questions": {"type": "string", "enum": ["Yes", "No"]},
                            "Module": {"type": "string", "enum": ["Audit", "Compliance"]},
                            "Welcome Note Required": {"type": "string", "enum": ["Yes", "No"]},
                            "Test Question for Compliance": {"type": ["string", "null"], "enum": ["TOD", "TOE", None]},
                            "Compliance Test Type": {"type": ["string", "null"], "enum": ["Assessment Question", "Test Procedure", None]}
                        },
                        "required": [
                            "Questionnaire Name",
                            "Assessment Based on",
                            "Add New Controls/Citations",
                            "Add New Questions",
                            "Module",
                            "Welcome Note Required"
                        ]
                    }
                },
                "Questionnaire Sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Section": {"type": "string", "minLength": 1},
                            "L1 Sub Section": {"type": ["string", "null"]},
                            "L2 Sub Section": {"type": ["string", "null"]},
                            "L3 Sub Section": {"type": ["string", "null"]},
                            "L4 Sub Section": {"type": ["string", "null"]},
                            "AD": {"type": "string", "minLength": 1},
                            "Citation": {"type": "string", "minLength": 1},
                            "Control ID": {"type": ["string", "integer"]},
                            "Question ID": {"type": "string", "minLength": 1}
                        },
                        "required": ["Section", "AD", "Citation", "Control ID", "Question ID"]
                    }
                },
                "New AD-Citation-Control": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "AD Name": {"type": "string", "minLength": 1},
                            "AD Description": {"type": "string", "minLength": 1},
                            "Control ID": {"type": "string", "minLength": 1},
                            "Control": {"type": "string", "minLength": 1},
                            "Control Description": {"type": "string", "minLength": 1},
                            "Control Impact Zone": {"type": "string", "enum": ["A.10 Cryptography", "A.12 Operations security"]},
                            "Citation": {"type": "string", "minLength": 1},
                            "Guidance": {"type": "string", "minLength": 1}
                        },
                        "required": [
                            "AD Name","AD Description","Control ID","Control",
                            "Control Description","Control Impact Zone","Citation","Guidance"
                        ]
                    }
                },
                "New Questions Creation": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Question ID": {"type": "string", "minLength": 1},
                            "Question Category": {"type": "string", "enum": ["Control", "Risk Register"]},
                            "Question Type": {"type": "string", "enum": ["Question", "Risk Assessment"]},
                            "Question Title": {"type": "string", "minLength": 1},
                            "Question Help": {"type": ["string", "null"]},
                            "Answer Sequence": {"type": "integer"},
                            "Answer Title": {"type": "string", "minLength": 1},
                            "Answer Sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]},
                            "Is Comment Required": {"type": "string", "enum": ["Yes", "No"]},
                            "Is Doc Required": {"type": "string", "enum": ["Yes", "No"]},
                            "Document Help": {"type": ["string", "null"]},
                            "Score": {"type": "number"}
                        },
                        "required": ["Question ID", "Question Category", "Question Type", "Question Title"]
                    }
                }
            },
            "required": ["Questionnaire", "Questionnaire Sections", "New Questions Creation"]
        }
    }

    # Call OpenAI API
    try:
        response = openai.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": user_prompt}],
            functions=[function_schema],
            function_call={"name": "return_questionnaire"},
            temperature=0
        )

        function_response = response.choices[0].message["function_call"]["arguments"]
        result_json = json.loads(function_response)

        st.subheader("Parsed JSON")
        st.json(result_json)

    except Exception as e:
        st.error(f"Error parsing JSON: {e}")
        if 'response' in locals():
            st.write("Raw response:")
            st.write(response)
