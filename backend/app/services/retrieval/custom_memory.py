from typing import List, Dict, Optional
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

class WindowedInMemoryHistory(BaseChatMessageHistory):
    """
    Backed by a list of dicts/messages, keeps only the last max_k messages.
    Bridges FastAPI dict-based history and LangChain BaseMessage objects.
    """
    def __init__(self, messages_list: list = None, max_k: Optional[int] = 4):
        self._messages = messages_list if messages_list is not None else []
        self.max_k = max_k

    @property
    def messages(self) -> List[BaseMessage]:
        result = []
        for msg in self._messages:
            if isinstance(msg, dict):
                if "Human" in msg:
                    result.append(HumanMessage(content=msg["Human"]))
                elif "AI" in msg:
                    result.append(AIMessage(content=msg["AI"]))
            elif isinstance(msg, BaseMessage):
                result.append(msg)
        return result

    def add_message(self, message: BaseMessage) -> None:
        if isinstance(message, AIMessage):
            self._messages.append({"AI": message.content})
        elif isinstance(message, HumanMessage):
            self._messages.append({"Human": message.content})
        else:
            self._messages.append({"Other": message.content})
        self._trim()

    def clear(self) -> None:
        self._messages.clear()

    def set_window(self, k: Optional[int]) -> None:
        self.max_k = k
        self._trim()

    def delete_at(self, idx: int) -> None:
        if -len(self._messages) <= idx < len(self._messages):
            del self._messages[idx]

    def _trim(self) -> None:
        if self.max_k is not None and len(self._messages) > self.max_k:
            self._messages[:] = self._messages[-self.max_k:]


class ReadOnlyProxyHistory(BaseChatMessageHistory):
    """Exposes the backing history list, but swallows writes."""
    def __init__(self, backing: WindowedInMemoryHistory):
        self.backing = backing

    @property
    def messages(self) -> List[BaseMessage]:
        return self.backing.messages

    def add_message(self, message: BaseMessage) -> None:
        pass

    def clear(self) -> None:
        pass


class ReadOrWriteProxyHistory(BaseChatMessageHistory):
    """Exposes the backing history list, writes AI messages unless they are '####'."""
    def __init__(self, backing: WindowedInMemoryHistory):
        self.backing = backing

    @property
    def messages(self) -> List[BaseMessage]:
        return self.backing.messages

    def add_message(self, message: BaseMessage) -> None:
        # Don't save refusal placeholder "####" to history
        if message.content != "####":
            self.backing.add_message(message)

    def clear(self) -> None:
        pass


class FilteredWriteProxyHistory(BaseChatMessageHistory):
    """Exposes backing history, writes only selected roles."""
    def __init__(self, backing: WindowedInMemoryHistory, save_human: bool = False, save_ai: bool = True):
        self.backing = backing
        self.save_human = save_human
        self.save_ai = save_ai

    @property
    def messages(self) -> List[BaseMessage]:
        return self.backing.messages

    def add_message(self, message: BaseMessage) -> None:
        if isinstance(message, HumanMessage) and self.save_human:
            self.backing.add_message(message)
        elif isinstance(message, AIMessage) and self.save_ai:
            self.backing.add_message(message)

    def clear(self) -> None:
        pass


# --- Session registry and getters ---
_chats: Dict[str, WindowedInMemoryHistory] = {}

def _get_or_create_main(session_id: str, default_max_k: Optional[int] = 4) -> WindowedInMemoryHistory:
    if session_id not in _chats:
        _chats[session_id] = WindowedInMemoryHistory(max_k=default_max_k)
    return _chats[session_id]

def get_chat_history_readonly(session_id: str) -> BaseChatMessageHistory:
    return ReadOnlyProxyHistory(backing=_get_or_create_main(session_id))

def get_chat_history_read_or_write(session_id: str) -> BaseChatMessageHistory:
    return ReadOrWriteProxyHistory(backing=_get_or_create_main(session_id))

def get_chat_history_write_ai_only(session_id: str) -> BaseChatMessageHistory:
    return FilteredWriteProxyHistory(backing=_get_or_create_main(session_id), save_human=False, save_ai=True)

def get_main_history(session_id: str) -> WindowedInMemoryHistory:
    return _get_or_create_main(session_id)

def set_window(session_id: str, k: Optional[int]) -> None:
    _get_or_create_main(session_id).set_window(k)
