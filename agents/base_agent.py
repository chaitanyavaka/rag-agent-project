from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Abstract base class for all agents in the system."""
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def process_message(self, message):
        """Process an incoming message and return a response message."""
        pass