"""Travel Planner MAS Setup for Safety Testing

This package provides a travel planner MAS using standard AG2 GroupChat
for compatibility with MASSafetyGuard framework.

Uses standard AssistantAgent + GroupChat approach (not SwarmAgent)
for better framework compatibility.
"""

# Export main creation function from setup.py
from .setup import create_travel_planner_mas, get_default_task

__all__ = ["create_travel_planner_mas", "get_default_task"]
