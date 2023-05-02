import ast

import streamlit as st
from streamlit_player import st_player

from .abstract_page import AbstractPage

import time


class SearchPage(AbstractPage):
    def __init__(self, sidebar, semantha, demo_config):
        self.__sidebar = sidebar
        self.__semantha = semantha
        self.__dummy = ""
        self.__demo_config = demo_config

    def display_page(self):
        # I find that the prompt is not needed
        # st.write(
        #     self.__demo_config.prompt
        # )
        # display a search input
        if self.__sidebar.get_enter_to_submit():
            search_string = self.__search_form()
            _, _, col, _, _ = st.columns(5)
            button = col.button("🔍 Search")
            if button or self.__dummy != search_string:
                self.__search(search_string)
        else:
            with st.form(key="search_form"):
                search_string = self.__search_form()
                _, _, col, _, _ = st.columns(5)
                button = col.form_submit_button("🔍 Search")
            if button:
                self.__search(search_string)

    def __search_form(self):
        if st.session_state.control:
            search_string = self.__keyword_search_form()
        else:
            search_string = self.__semantic_search_form()

        return search_string

    def __semantic_search_form(self):
        return st.text_area(
            label="Search",
            value="",
            placeholder="Enter your question here ...",
            label_visibility="collapsed",
        )

    def __keyword_search_form(self):
        return st.text_input(
            label="Suche",
            value="",
            placeholder="Gib hier deine Stichwörter ein...",
            label_visibility="collapsed",
        )

    def __search(self, search_string):
        tags = "base,11"
        if search_string == "":
            st.error("Bitte gib zuerst eine Frage ein!", icon="🕵🏻")
        else:
            self.__content_search(search_string, tags)

    def __content_search(self, search_string, tags):
        with st.spinner("🕵🏻 Looking for a matching video ..."):
            results = self.__semantha.query_library(
                search_string,
                tags=tags,
                max_matches=self.__sidebar.get_max_matches(),
                ranking_strategy=self.__sidebar.get_ranking_strategy(),
                sparse_filter_size=self.__sidebar.get_filter_size(),
                alpha=self.__sidebar.get_alpha(),
                filter_duplicates=self.__sidebar.get_filter_duplicates(),
                threshold=self.__sidebar.get_threshold()
            )
            if results.empty:
                self.__no_match_handling(search_string)
            else:
                self.__match_handling(search_string, results)

    def __match_handling(self, search_string, results):
        video_string = "Matching video" if len(results) == 1 else "Matching videos"
        st.success(
            f"Done! I have found **{len(results)}** {video_string} for you!",
            icon="🕵🏻",
        )
        if self.__sidebar.get_enable_usage_tracking():
            self.__semantha.add_to_library(
                content=search_string, tag=st.session_state.user_id
            )

        if not self.__sidebar.get_show_videos_below_each_other():
            st.session_state["tabs"] = ["Video 1"]
            for i, row in results.iterrows():
                if i >= 2:
                    st.session_state["tabs"].append(f"Video {i}")

            tabs = st.tabs(st.session_state["tabs"])
        for i, row in results.iterrows():
            if self.__sidebar.get_show_videos_below_each_other():
                self.__display_results_below_each_other(results, i, row)
            else:
                self.__display_result_in_tabs(results, i, row, tabs)
        if self.__sidebar.get_debug():
            self.__debug_view(results)

    def __debug_view(self, results):
        with st.expander("Results", expanded=False):
            st.write(results)

    def __no_match_handling(self, search_string):
        st.error(
            "I couldn't find a matching video. ",
            icon="🕵🏻",
        )
        if self.__sidebar.get_enable_usage_tracking():
            self.__semantha.add_to_library(
                content=search_string, tag=st.session_state.user_id + ",no_match"
            )

    def __display_result_in_tabs(self, results, i, row, tabs):
        video_id, start, content, category, video = self.__get_result_info(
            results, i, row
        )
        with tabs[i - 1]:
            self.__display_video(video_id, start, content, category, video)

    def __display_results_below_each_other(self, results, i, row):
        video_id, start, content, category, video, similarity = self.__get_result_info(
            results, i, row
        )
        st.subheader(f"Video {i} of {len(results)} ({similarity}%)")
        self.__display_video(video_id, start, content, category, video)
        if i >= 1 and i < len(results):
            self.__display_horizontal_line()

    def __display_horizontal_line(self):
        st.markdown(
            """<hr style="height:2px;border:none;color:#333;background-color:#333;" /> """,
            unsafe_allow_html=True,
        )

    def __display_video(self, video_url, start, content, category, video):
        if not st.session_state.control:
            st.markdown(f'💬 **The reference says:** "_{content}..._"')
        st.markdown(f"🏷️ **Tags:** _{category}_")
        st_player(f"{str(video_url)}&rel=0", height=400, key=f"{video_url}_{time.time_ns()}", config={
            "vimeo": {
                "playerOptions": {
                    "color": "#BE25BE",
                    "title": False,
                }
            }
        })
        st.markdown(f"📺 **Video:** _{video}_")

    def __get_result_info(self, results, i, row):
        results.at[i, "Metadata"] = ast.literal_eval(row["Metadata"])
        video_id = results.at[i, "Metadata"]["url"]
        start = 0   # if st.session_state.control else results.at[i, "Metadata"]["start"]
        content = results.at[i, "Content"]
        category = results.at[i, "Tags"]
        category = [tag for tag in category if tag not in ["base", "11"]]
        category = ", ".join(category)
        video = results.at[i, "Name"].split("_")[0]
        similarity = results.at[i, "Similarity"]
        return video_id, start, content, category, video, similarity
