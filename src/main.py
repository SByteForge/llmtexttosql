import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import database
import llm as llm_module
from utils import load_config

load_dotenv()

CONFIG = load_config(os.path.join(os.path.dirname(__file__), "config.yaml"))

st.set_page_config(page_title="Database Q/A App", page_icon=":bookmark_tabs:")
st.image(os.path.join(os.path.dirname(__file__), "..", "logo.jpg"), width=100)
st.title("Skillcrub Database :red[Q/A App]  :open_book:")


@st.cache_resource
def get_db():
    return database.get_database(CONFIG)


@st.cache_resource
def get_llm():
    return llm_module.get_llm(CONFIG)


db = get_db()

with st.expander("Available tables"):
    st.code(db.get_table_info(), language="sql")

question = st.text_input(":violet[Question: ]")
submit = st.button("Submit")

if question and submit:
    with st.spinner("Thinking..."):
        try:
            result = llm_module.ask(
                get_llm(), db, question,
                max_rows=CONFIG["database"].get("max_result_rows", 200),
            )
        except Exception as e:
            result = {"error": f"Unexpected error: {e}"}

    if "error" in result:
        st.error(result["error"])
        if result.get("sql"):
            with st.expander("Generated SQL"):
                st.code(result["sql"], language="sql")
        if result.get("rows"):
            st.dataframe(pd.DataFrame(result["rows"], columns=result["columns"]))
    else:
        st.header("Answer")
        st.write(result["answer"])

        with st.expander("Generated SQL"):
            st.code(result["sql"], language="sql")

        if result["rows"]:
            st.dataframe(pd.DataFrame(result["rows"], columns=result["columns"]))
