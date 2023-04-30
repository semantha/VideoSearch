from .abstract_page import AbstractPage
import streamlit as st

from video_search.search.semantha import DenseOnlyRanking, SparseFilterDenseRanking, HybridRanking

_DENSE_ONLY_RANKING = "DenseOnlyRanking"
_SPARSE_FILTER_DENSE_RANKING = "SparseFilterDenseRanking"
_HYBRID_RANKING = "HybridRanking"
_HORIZONTAL_LINE = (
    """<hr style="height:1px;border:none;color:#333;background-color:#333;" /> """
)


class Sidebar(AbstractPage):
    def __init__(self, page_manager, demo_config):
        self.__page_manager = page_manager
        self.__max_matches = 5
        self.__ranking_strategy = _HYBRID_RANKING
        self.__filter_size = 10
        self.__threshold = 0.7
        self.__alpha = 0.7
        self.__enable_usage_tracking = False
        self.__enter_to_submit = True
        self.__debug = False
        self.__filter_duplicates = True
        self.__show_videos_below_each_other = True
        self.__playlists = ["IBM Engineering Lifecycle Management"]

    def get_max_matches(self):
        return self.__max_matches

    def get_threshold(self):
        return self.__threshold

    def get_ranking_strategy(self):
        if self.__ranking_strategy == _DENSE_ONLY_RANKING:
            return DenseOnlyRanking
        elif self.__ranking_strategy == _SPARSE_FILTER_DENSE_RANKING:
            return SparseFilterDenseRanking
        elif self.__ranking_strategy == _HYBRID_RANKING:
            return HybridRanking
        else:
            raise ValueError(f"Unknown ranking strategy '{self.__ranking_strategy}'")

    def get_filter_size(self):
        return self.__filter_size

    def get_alpha(self):
        return self.__alpha

    def get_enable_usage_tracking(self):
        return self.__enable_usage_tracking

    def get_debug(self):
        return self.__debug

    def get_filter_duplicates(self):
        return self.__filter_duplicates

    def get_enter_to_submit(self):
        return self.__enter_to_submit

    def get_show_videos_below_each_other(self):
        return self.__show_videos_below_each_other

    def display_page(self):
        with st.sidebar:
            st.header("⚙️ Settings")
            self.__playlists = st.multiselect(
                "Playlists",
                options=[
                    "IBM Engineering Lifecycle Management",
                    ],
                default=["IBM Engineering Lifecycle Management"],
            )

            self.__max_matches = st.slider(
                "Maximum matches", min_value=1, max_value=10, value=5
            )
            self.__threshold = st.slider(
                "Threshold", min_value=0.0, max_value=1.0, value=0.7
            )
            # st.write("Klicke hier um die Seite neuzustarten:")
            # if st.session_state.page >= 2:
            #     st.button("📹 Video", on_click=self.__show_video_page)
            # st.button("🔄 Neustart", on_click=self.restart)
            # self.__show_horizontal_line()
            # self.__debug = st.checkbox("🐞 Debug Mode", value=False)
            # self.__show_horizontal_line()
            # st.subheader("IDs zum Testen:")
            # st.markdown("**ohne KI**: _UiiZP2H_")
            # st.markdown("**mit KI**:  _igCY5s4_")
            # if self.__debug:
            #     self.__debug_information()

    def __debug_information(self):
        st.subheader("🐞 Debug Settings")
        self.__show_horizontal_line()
        self.__enter_to_submit = st.checkbox(
            "Enable 'Press Enter to Submit'", value=True
        )
        self.__enable_usage_tracking = st.checkbox("Enable Usage Tracking", value=True)
        self.__show_horizontal_line()
        self.__max_matches = st.slider(
            "Maximum matches", min_value=0, max_value=10, value=5
        )
        self.__show_videos_below_each_other = st.checkbox(
            "Show videos below each other", value=True
        )
        self.__show_horizontal_line()
        self.__ranking_strategy = st.radio(
            "Ranking Strategy",
            options=[
                "HybridRanking",
                "DenseOnlyRanking",
                "SparseFilterDenseRanking",
            ],
        )
        if (
            self.__ranking_strategy == _SPARSE_FILTER_DENSE_RANKING
            or self.__ranking_strategy == _HYBRID_RANKING
        ):
            self.__filter_size = st.slider(
                "Sparse filter size", min_value=0, max_value=10, value=10
            )
        if self.__ranking_strategy == _HYBRID_RANKING:
            self.__alpha = st.slider(
                "Alpha", min_value=0.0, max_value=2.0, step=0.05, value=0.7
            )

    def __show_horizontal_line(self):
        st.markdown(_HORIZONTAL_LINE, unsafe_allow_html=True)

    def restart(self):
        st.session_state.clear()
        self.__page_manager.restart()

    def __show_video_page(self):
        st.session_state.page = 1
