"""
Streamlit callback handler for displaying agent progress in real-time.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import streamlit as st
from langchain_core.callbacks.base import BaseCallbackHandler


class StreamlitCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming agent outputs to Streamlit."""
    
    def __init__(self, status_container):
        """
        Initialize the callback handler.
        
        Args:
            status_container: Streamlit container for displaying status updates
        """
        self.status_container = status_container
        self.current_agent = None
        self.agent_start_time = None
        
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts."""
        with self.status_container:
            st.markdown("🤖 **Calling AI Model...**")
            with st.expander("View Prompt", expanded=False):
                st.code(prompts[0][:500] + "..." if len(prompts[0]) > 500 else prompts[0])
    
    def on_llm_end(self, response, **kwargs: Any) -> None:
        """Called when LLM ends."""
        with self.status_container:
            st.markdown("✅ **AI Response Received**")
    
    def on_agent_action(self, action, **kwargs: Any) -> None:
        """Called when agent takes an action."""
        with self.status_container:
            st.markdown(f"🎯 **Agent Action**: {action}")
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Called when a tool starts."""
        tool_name = serialized.get("name", "Unknown Tool")
        with self.status_container:
            st.markdown(f"🔧 **Using Tool**: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool ends."""
        with self.status_container:
            st.markdown("✅ **Tool Complete**")
    
    def on_text(self, text: str, **kwargs: Any) -> None:
        """Called when there's text to display."""
        with self.status_container:
            st.markdown(text)
    
    def on_agent_finish(self, finish, **kwargs: Any) -> None:
        """Called when agent finishes."""
        with self.status_container:
            st.markdown("🎉 **Agent Complete**")


class AgentProgressTracker:
    """Track and display agent progress in Streamlit."""
    
    def __init__(self, container):
        """
        Initialize progress tracker.
        
        Args:
            container: Streamlit container for progress display
        """
        self.container = container
        self.agents = []
        self.current_step = 0
        self.total_steps = 0
        
    def start_agent(self, agent_name: str, description: str):
        """Start tracking a new agent."""
        self.current_step += 1
        self.agents.append({
            "name": agent_name,
            "description": description,
            "status": "running",
            "start_time": datetime.now(),
            "messages": []
        })
        self._update_display()
    
    def add_message(self, message: str, message_type: str = "info"):
        """Add a message to the current agent."""
        if self.agents:
            self.agents[-1]["messages"].append({
                "text": message,
                "type": message_type,
                "timestamp": datetime.now()
            })
        self._update_display()
    
    def complete_agent(self, success: bool = True):
        """Mark current agent as complete."""
        if self.agents:
            self.agents[-1]["status"] = "success" if success else "error"
            self.agents[-1]["end_time"] = datetime.now()
            duration = (self.agents[-1]["end_time"] - self.agents[-1]["start_time"]).total_seconds()
            self.agents[-1]["duration"] = duration
        self._update_display()
    
    def _update_display(self):
        """Update the visual display."""
        with self.container:
            st.empty()  # Clear previous content
            
            # Progress bar
            if self.total_steps > 0:
                progress = self.current_step / self.total_steps
                st.progress(progress, text=f"Step {self.current_step} of {self.total_steps}")
            
            # Display each agent
            for agent in self.agents:
                self._render_agent(agent)
    
    def _render_agent(self, agent: dict):
        """Render an individual agent's progress."""
        # Status icon
        if agent["status"] == "running":
            icon = "🔄"
            color = "blue"
        elif agent["status"] == "success":
            icon = "✅"
            color = "green"
        else:
            icon = "❌"
            color = "red"
        
        # Agent header
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"{icon} **{agent['name']}**")
            st.caption(agent['description'])
        with col2:
            if "duration" in agent:
                st.caption(f"{agent['duration']:.2f}s")
        
        # Messages
        if agent["messages"]:
            with st.expander("Details", expanded=(agent["status"] == "running")):
                for msg in agent["messages"]:
                    if msg["type"] == "info":
                        st.info(msg["text"])
                    elif msg["type"] == "success":
                        st.success(msg["text"])
                    elif msg["type"] == "warning":
                        st.warning(msg["text"])
                    elif msg["type"] == "error":
                        st.error(msg["text"])
                    else:
                        st.markdown(msg["text"])
        
        st.divider()
    
    def set_total_steps(self, total: int):
        """Set total number of steps."""
        self.total_steps = total
