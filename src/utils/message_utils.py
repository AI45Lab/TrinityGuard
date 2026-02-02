"""Message processing utilities for resolving chat_manager recipients."""

from typing import List, Dict, Optional


def resolve_chat_manager_recipients(messages: List[Dict]) -> List[Dict]:
    """Resolve 'chat_manager' recipients to actual next speakers.

    This function processes a list of messages and replaces 'chat_manager'
    in the 'to_agent' field with the actual recipient by looking ahead to
    see who speaks next.

    Args:
        messages: List of message dicts with 'from_agent', 'to_agent', 'content' fields

    Returns:
        New list with resolved 'to_agent' fields

    Example:
        Input:
        [
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
            {"from_agent": "B", "to_agent": "chat_manager", "content": "Hi"},
            {"from_agent": "C", "to_agent": "chat_manager", "content": "Hey"}
        ]

        Output:
        [
            {"from_agent": "A", "to_agent": "B", "content": "Hello", "to_agent_resolved": True},
            {"from_agent": "B", "to_agent": "C", "content": "Hi", "to_agent_resolved": True},
            {"from_agent": "C", "to_agent": "chat_manager", "content": "Hey"}
        ]
    """
    if not messages:
        return messages

    resolved = []

    for i, msg in enumerate(messages):
        new_msg = msg.copy()

        # Check if recipient is chat_manager
        to_agent = msg.get('to_agent') or msg.get('to')

        if to_agent == 'chat_manager':
            # Look ahead to find the next speaker
            actual_recipient = _find_next_speaker(messages, i)

            if actual_recipient:
                # Update both possible field names for compatibility
                if 'to_agent' in new_msg:
                    new_msg['to_agent'] = actual_recipient
                if 'to' in new_msg:
                    new_msg['to'] = actual_recipient

                # Mark as resolved
                new_msg['to_agent_resolved'] = True
                new_msg['to_agent_original'] = 'chat_manager'

        resolved.append(new_msg)

    return resolved


def _find_next_speaker(messages: List[Dict], current_idx: int) -> Optional[str]:
    """Find the next speaker after current message.

    Args:
        messages: List of all messages
        current_idx: Index of current message

    Returns:
        Name of next speaker, or None if not found
    """
    current_from = messages[current_idx].get('from_agent') or messages[current_idx].get('from')

    # Look ahead in the message list
    for i in range(current_idx + 1, len(messages)):
        next_msg = messages[i]
        next_from = next_msg.get('from_agent') or next_msg.get('from')

        # Skip if it's the same speaker (rare but possible in tool calls)
        if next_from and next_from != current_from:
            return next_from

    return None


def resolve_nested_messages(data: Dict) -> Dict:
    """Recursively resolve chat_manager in nested message structures.

    This handles complex report structures where messages might be nested
    in various fields like 'messages', 'workflow_details', 'details', etc.

    Args:
        data: Dictionary that might contain message lists

    Returns:
        Dictionary with all messages resolved
    """
    if not isinstance(data, dict):
        return data

    result = {}

    for key, value in data.items():
        if key == 'messages' and isinstance(value, list):
            # Found a messages list, resolve it
            result[key] = resolve_chat_manager_recipients(value)
        elif isinstance(value, dict):
            # Recursively process nested dicts
            result[key] = resolve_nested_messages(value)
        elif isinstance(value, list):
            # Process list items
            result[key] = [
                resolve_nested_messages(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            # Keep other values as-is
            result[key] = value

    return result


def get_resolution_stats(messages: List[Dict]) -> Dict:
    """Get statistics about message resolution.

    Args:
        messages: List of messages (can be before or after resolution)

    Returns:
        Dict with resolution statistics
    """
    total = len(messages)
    chat_manager_count = 0
    resolved_count = 0

    for msg in messages:
        to_agent = msg.get('to_agent') or msg.get('to')
        if to_agent == 'chat_manager':
            chat_manager_count += 1
        if msg.get('to_agent_resolved'):
            resolved_count += 1

    return {
        'total_messages': total,
        'chat_manager_count': chat_manager_count,
        'resolved_count': resolved_count,
        'resolution_rate': resolved_count / chat_manager_count if chat_manager_count > 0 else 0.0
    }