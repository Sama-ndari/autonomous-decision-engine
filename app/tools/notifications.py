"""
Notification Tools - Push notifications via Pushover.

Provides push notification capabilities for alerting users
about important decisions, human input requirements, and completions.
"""

import os
import requests
from langchain_core.tools import Tool

from app.config import get_config


PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def send_push_notification(message: str) -> str:
    """
    Send a push notification via Pushover.
    
    Args:
        message: The notification message to send
    
    Returns:
        Success or error message
    """
    config = get_config()
    
    if not config.pushover_token or not config.pushover_user:
        return "Push notifications not configured (missing PUSHOVER_TOKEN or PUSHOVER_USER)"
    
    try:
        response = requests.post(
            PUSHOVER_URL,
            data={
                "token": config.pushover_token,
                "user": config.pushover_user,
                "message": message,
                "title": "Autonomous Decision Engine",
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return "Push notification sent successfully"
        else:
            return f"Failed to send notification: {response.status_code}"
    
    except requests.RequestException as e:
        return f"Error sending notification: {str(e)}"


def notify_human_required(task_summary: str) -> str:
    """
    Send notification when human input is required.
    
    Args:
        task_summary: Brief summary of the task requiring attention
    
    Returns:
        Status message
    """
    message = f"🔔 Human Input Required\n\nTask: {task_summary}\n\nPlease review in the ADE terminal."
    return send_push_notification(message)


def notify_task_complete(task_summary: str, decision: str) -> str:
    """
    Send notification when a task is complete.
    
    Args:
        task_summary: Brief summary of the completed task
        decision: The final decision (autonomous, tools, human, stop)
    
    Returns:
        Status message
    """
    emoji = {
        "autonomous": "✅",
        "tools": "🔧",
        "human": "👤",
        "stop": "🛑",
    }.get(decision, "📋")
    
    message = f"{emoji} Task Complete\n\nTask: {task_summary}\nDecision: {decision.upper()}"
    return send_push_notification(message)


def get_notification_tools() -> list[Tool]:
    """
    Get notification-related tools.
    
    Returns:
        List of notification tools
    """
    return [
        Tool(
            name="send_push_notification",
            func=send_push_notification,
            description="Send a push notification to the user's device via Pushover. "
                       "Use this to alert the user about important updates, "
                       "required actions, or task completions. "
                       "Input should be the notification message."
        ),
    ]

