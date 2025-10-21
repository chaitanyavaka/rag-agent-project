import uuid

def create_mcp_message(sender, receiver, msg_type, payload, trace_id=None):
    """Creates a structured message following the Model Context Protocol (MCP)."""
    if trace_id is None:
        trace_id = str(uuid.uuid4())
        
    message = {
        "sender": sender,
        "receiver": receiver,
        "type": msg_type,
        "trace_id": trace_id,
        "payload": payload
    }
    return message