import streamlit as st


class PageManager:
    def __init__(self, demo_config):
        if "page" not in st.session_state:
            st.session_state.page = 0

    @staticmethod
    def nextpage():
        st.session_state.page += 1

    @staticmethod
    def restart():
        st.session_state.page = 0
