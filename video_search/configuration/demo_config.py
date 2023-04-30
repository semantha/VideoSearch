from dataclasses import dataclass

@dataclass
class DemoConfig:
    page_title: str = "🔎 Semantha VideoSearch"
    page_icon: str = "favicon.png"
    initial_sidebar_state: str = "collapsed"
    prompt: str = "Enter your question and I will look for a matching video position."
