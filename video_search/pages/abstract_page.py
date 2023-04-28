from abc import ABC, abstractmethod


class AbstractPage(ABC):
    @abstractmethod
    def display_page(self):
        pass
