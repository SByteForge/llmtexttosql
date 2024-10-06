import streamlit as st

st.set_page_config(page_title="Database Q/A App", page_icon="bookmark_tab:")
st.image("logo.jpg", width=100)

st.title('Skillcrub Database:red[Q/A App]   :ope_bok:')

question=st.text_input(":violet[Question: ]")
submit=st.button("Submit")

if question and submit:
    st.header("Answer")
    st.write("respose")