import streamlit as st
import openai
import json
import os

st.title("GRC JSON Extractor with Function Calling 1")

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

    # Build prompt
    user_prompt = f"""
    You are a GRC expert. Analyze the following files and return JSON exactly matching the schema.
    Files: {', '.join([f['filename'] for f in files_content])}
    """

    # Define the function with full schema
    function_schema = {
        {
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
            "Questionnaire Name": { "type": "string", "minLength": 1 },
            "Assessment Based on": { "type": "string", "enum": ["Citations","Controls"] },
            "Add New Controls/Citations": { "type": "string", "enum": ["Yes","No"] },
            "Add New Questions": { "type": "string", "enum": ["Yes","No"] },
            "Module": { "type": "string", "enum": ["Audit","Compliance"] },
            "Welcome Note Required": { "type": "string", "enum": ["Yes","No"] },
            "Test Question for Compliance": { "type": ["string","null"], "enum": ["TOD","TOE", null] },
            "Compliance Test Type": { "type": ["string","null"], "enum": ["Assessment Question","Test Procedure", null] }
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
            "Section": { "type": "string", "minLength": 1 },
            "L1 Sub Section": { "type": ["string","null"] },
            "L2 Sub Section": { "type": ["string","null"] },
            "L3 Sub Section": { "type": ["string","null"] },
            "L4 Sub Section": { "type": ["string","null"] },
            "AD": { "type": "string", "minLength": 1 },
            "Citation": { "type": "string", "minLength": 1 },
            "Control ID": { "type": ["string","integer"] },
            "Question ID": { "type": "string", "minLength": 1 }
          },
          "required": ["Section","AD","Citation","Control ID","Question ID"]
        }
      },
      "New AD-Citation-Control": {
        "anyOf": [
          {
            "type": "array",
            "maxItems": 0
          },
          {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "AD Name": { "type": "string", "minLength": 1 },
                "AD Description": { "type": "string", "minLength": 1 },
                "Control ID": { "type": "string", "minLength": 1 },
                "Control": { "type": "string", "minLength": 1 },
                "Control Description": { "type": "string", "minLength": 1 },
                "Control Impact Zone": {
                  "type": "string",
                  "enum": ["A.10 Cryptography", "A.12 Operations security"]
                },
                "Citation": { "type": "string", "minLength": 1 },
                "Guidance": { "type": "string", "minLength": 1 }
              },
              "required": [
                "AD Name",
                "AD Description",
                "Control ID",
                "Control",
                "Control Description",
                "Control Impact Zone",
                "Citation",
                "Guidance"
              ]
            },
            "minItems": 1
          }
        ]
      },
      "New Questions Creation": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "Question ID": { "type": "string", "minLength": 1 },
            "Question Category": { "type": "string", "enum": ["Control","Risk Register"] },
            "Question Type": { "type": "string", "enum": ["Question","Risk Assessment"] },
            "Question Title": { "type": "string", "minLength": 1 },
            "Question Help": { "type": ["string","null"] },
            "Answer Sequence": { "type": "integer" },
            "Answer Title": { "type": "string", "minLength": 1 },
            "Is Comment Required": { "type": "string", "enum": ["Yes","No"] },
            "Is Doc Required": { "type": "string", "enum": ["Yes","No"] },
            "Document Help": { "type": ["string","null"] },
            "Score": { "type": "number" }
          },
          "required": ["Question ID","Question Category","Question Type","Question Title"]
        }
      }
    },
    "required": ["Questionnaire","Questionnaire Sections","New Questions Creation"]
  }
}
    }

    # Call OpenAI API with function calling
    response = openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": user_prompt}],
        functions=[function_schema],
        function_call={"name": "return_questionnaire"},
        temperature=0
    )

    # Extract JSON from function call
    try:
        function_response = response.choices[0].message["function_call"]["arguments"]
        result_json = json.loads(function_response)
        st.subheader("Parsed JSON")
        st.json(result_json)
    except Exception as e:
        st.error(f"Error parsing JSON: {e}")
        st.write("Raw response:")
        st.write(response)
