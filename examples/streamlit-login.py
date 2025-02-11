import streamlit as st
import os

if not st.experimental_user.is_logged_in:
    if st.button("Log in"):
        st.login()
else:
    if st.button("Log out"):
        st.logout()
    st.write(f"Hello, {st.experimental_user.name}!")
    st.json(st.experimental_user)
   # , {' '.join(st.experimental_user.keys())}!")

os.environ['STREAMLIT_SERVER_PORT'] = '7000'    