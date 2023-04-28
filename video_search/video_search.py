from .pages.page_manager import PageManager
from .pages.search_page import SearchPage
from .pages.sidebar import Sidebar
import streamlit as st

from video_search.search.semantha import Semantha


class VideoSearch:
    def __init__(self, demo_config):
        self.__semantha = Semantha(demo_config)
        self.__page_manager = PageManager(demo_config)
        self.__sidebar = Sidebar(self.__page_manager, demo_config)
        self.__search_page = SearchPage(self.__sidebar, self.__semantha, demo_config)
        self.__pages = [self.__search_page]

    def display_page(self):
        self.__configure_page()
        self.__sidebar.display_page()

        placeholder = st.empty()

        for i in range(len(self.__pages)):
            if st.session_state.page == i:
                with placeholder.container():
                    self.__pages[i].display_page()

    @staticmethod
    def __configure_page():
        st.config.set_option("theme.primaryColor", "#BE25BE")
        st.set_page_config(
            page_title="🕵🏻 AI Video Search for Learning Management Systems",
            page_icon="favicon.png",
            initial_sidebar_state="collapsed",
        )
        # display a title
        st.header("🕵🏻 AI Video Search for Learning Management Systems")
