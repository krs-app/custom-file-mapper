import streamlit as st
import openai
import json
import pdfplumber
import pandas as pd

st.title("GRC JSON Extractor with ChatGPT Function Calling (PDF + Excel)")

# Input OpenAI API key
openai.api_key = st.text_input("Enter your OpenAI API Key", type="password")

uploaded_files = st.file_uploader(
    "Upload PDFs or Excel files",
    type=["pdf", "xlsx"],
    accept_multiple_files=True
)

if st.button("Generate JSON") and uploaded_files and openai.api_key:
    files_content = []

    # 1️⃣ Extract content from each file
    for f in uploaded_files:
        if f.name.lower().endswith(".pdf"):
            # PDF extraction
            text = ""
            with pdfplumber.open(f) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            files_content.append({"filename": f.name, "content": text})
        elif f.name.lower().endswith(".xlsx"):
            # Excel extraction
            excel_data = pd.read_excel(f, sheet_name=None)
            text = ""
            for sheet_name, df in excel_data.items():
                text += f"Sheet: {sheet_name}\n"
                text += df.fillna("").to_csv(index=False) + "\n"
            files_content.append({"filename": f.name, "content": text})

    # 2️⃣ Build prompt
    user_prompt = f"""
    You are a GRC expert. Analyze the following files and return JSON exactly matching schema:
    
    Files:
    {json.dumps([{f['filename']: f['content'][:2000]} for f in files_content], indent=2)}
    
    Identify AD, Citations, Controls, Questions, Expected Answer, Score, etc.
    Include 'Answer Sentiment' for each answer. Follow the JSON schema strictly.
    """

    # 3️⃣ Full function schema
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
                            "Add New Controls/Citations": {"type": "string", "enum": ["Yes","No"]},
                            "Add New Questions": {"type": "string", "enum": ["Yes","No"]},
                            "Module": {"type": "string", "enum": ["Audit","Compliance"]},
                            "Welcome Note Required": {"type": "string", "enum": ["Yes","No"]},
                            "Test Question for Compliance": {"type": ["string","null"], "enum":["TOD","TOE", None]},
                            "Compliance Test Type": {"type": ["string","null"], "enum":["Assessment Question","Test Procedure", None]}
                        },
                        "required":["Questionnaire Name","Assessment Based on","Add New Controls/Citations",
                                    "Add New Questions","Module","Welcome Note Required"]
                    }
                },
                "Questionnaire Sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Section":{"type":"string"},
                            "L1 Sub Section":{"type":["string","null"]},
                            "L2 Sub Section":{"type":["string","null"]},
                            "L3 Sub Section":{"type":["string","null"]},
                            "L4 Sub Section":{"type":["string","null"]},
                            "AD":{"type":"string"},
                            "Citation":{"type":"string"},
                            "Control ID":{"type":["string","integer"]},
                            "Question ID":{"type":"string"}
                        },
                        "required":["Section","AD","Citation","Control ID","Question ID"]
                    }
                },
                "New AD-Citation-Control": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "AD Name":{"type":"string"},
                            "AD Description":{"type":"string"},
                            "Control ID":{"type":"string"},
                            "Control":{"type":"string"},
                            "Control Description":{"type":"string"},
                            "Control Impact Zone":{"type":"string","enum":["A.10 Cryptography","A.12 Operations security"]},
                            "Citation":{"type":"string"},
                            "Guidance":{"type":"string"}
                        },
                        "required":["AD Name","AD Description","Control ID","Control",
                                   "Control Description","Control Impact Zone","Citation","Guidance"]
                    }
                },
                "New Questions Creation": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Question ID":{"type":"string"},
                            "Question Category":{"type":"string","enum":["Control","Risk Register"]},
                            "Question Type":{"type":"string","enum":["Question","Risk Assessment"]},
                            "Question Title":{"type":"string"},
                            "Question Help":{"type":["string","null"]},
                            "Answer Sequence":{"type":"integer"},
                            "Answer Title":{"type":"string"},
                            "Answer Sentiment":{"type":"string","enum":["Positive","Negative","Neutral"]},
                            "Is Comment Required":{"type":"string","enum":["Yes","No"]},
                            "Is Doc Required":{"type":"string","enum":["Yes","No"]},
                            "Document Help":{"type":["string","null"]},
                            "Score":{"type":"number"}
                        },
                        "required":["Question ID","Question Category","Question Type","Question Title"]
                    }
                }
            },
            "required":["Questionnaire","Questionnaire Sections","New Questions Creation"]
        }
    }

    # 4️⃣ Call GPT
    try:
        response = openai.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role":"user","content":user_prompt}],
            functions=[function_schema],
            function_call={"name":"return_questionnaire"}
        )

        func_args = response.choices[0].message.function_call.arguments
        result_json = json.loads(func_args)

        st.subheader("Parsed JSON")
        st.json(result_json)

    except Exception as e:
        st.error(f"Error: {e}")
        if 'response' in locals():
            st.write(response)
