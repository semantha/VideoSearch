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
        self.__demo_config = demo_config

    def display_page(self):
        self.__configure_page()
        self.__sidebar.display_page()

        placeholder = st.empty()

        for i in range(len(self.__pages)):
            if st.session_state.page == i:
                with placeholder.container():
                    self.__pages[i].display_page()

    def __configure_page(self):
        st.config.set_option("theme.primaryColor", "#BE25BE")
        st.set_page_config(
            page_title=self.__demo_config.page_title,
            page_icon=self.__demo_config.page_icon,
            initial_sidebar_state=self.__demo_config.initial_sidebar_state,
        )
        # display a title
        st.header(self.__demo_config.page_title)
