import streamlit
from video_search import DemoConfig, VideoSearch

demo_config = DemoConfig()
video_search = VideoSearch(demo_config)

if __name__ == "__main__":
    streamlit.session_state.control = False
    video_search.display_page()
