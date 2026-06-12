# ChatClient JavaScript Class

## Overview

The `ChatClient` class provides a WebSocket-based client for real-time chat functionality in the RealmKey application. It handles connection management, message sending/receiving, and automatic reconnection with exponential backoff.

## Features

- **WebSocket Connection Management**: Establishes and maintains WebSocket connections
- **Message Validation**: Validates message content (non-empty, max 5000 characters)
- **Automatic Reconnection**: Implements exponential backoff strategy (1s, 2s, 4s, 8s, 16s)
- **Callback System**: Supports multiple callbacks for messages and connection status
- **Connection State Tracking**: Provides methods to check connection state

## Requirements Validated

- **Requirement 2.2**: Message broadcasting through WebSocket
- **Requirement 2.3**: Real-time message display
- **Requirement 2.5**: Automatic reconnection on interruption

## Usage

### Basic Setup

```javascript
// Initialize the client with a conversation ID
const chatClient = new ChatClient(conversationId);

// Register message callback
chatClient.onMessage((data) => {
    console.log('Received message:', data);
    // Handle incoming message
});

// Register connection status callback
chatClient.onConnectionStatus((status, message) => {
    console.log('Connection status:', status, message);
    // Update UI based on connection status
});

// Connect to WebSocket
chatClient.connect();
```

### Sending Messages

```javascript
const success = chatClient.sendMessage('Hello, World!');
if (success) {
    console.log('Message sent successfully');
} else {
    console.error('Failed to send message');
}
```

### Disconnecting

```javascript
// Disconnect when done (e.g., on page unload)
chatClient.disconnect();
```

## API Reference

### Constructor

```javascript
new ChatClient(conversationId)
```

**Parameters:**
- `conversationId` (number): The ID of the conversation

### Methods

#### `connect()`
Establishes a WebSocket connection to the server.

#### `sendMessage(content)`
Sends a message through the WebSocket.

**Parameters:**
- `content` (string): Message content (1-5000 characters)

**Returns:**
- `boolean`: `true` if message was sent, `false` otherwise

**Validation:**
- Content must be a non-empty string
- Content must not exceed 5000 characters
- WebSocket must be connected

#### `onMessage(callback)`
Registers a callback for incoming messages.

**Parameters:**
- `callback` (function): Function to call when a message is received
  - Receives message data object with properties:
    - `type`: "message"
    - `message`: Message content
    - `sender_id`: Sender's user ID
    - `sender_email`: Sender's email
    - `message_id`: Message ID
    - `created_at`: ISO timestamp

#### `onConnectionStatus(callback)`
Registers a callback for connection status changes.

**Parameters:**
- `callback` (function): Function to call when connection status changes
  - Receives two parameters:
    - `status` (string): Connection status (connected, disconnected, reconnecting, error, failed)
    - `message` (string): Optional status message

#### `disconnect()`
Closes the WebSocket connection intentionally.

#### `getConnectionState()`
Returns the current WebSocket connection state.

**Returns:**
- `string`: Connection state (connecting, open, closing, closed, or null)

#### `isConnected()`
Checks if the WebSocket is currently connected.

**Returns:**
- `boolean`: `true` if connected, `false` otherwise

## Message Format

### Outgoing Messages (Client → Server)

```json
{
    "message": "Message content"
}
```

### Incoming Messages (Server → Client)

```json
{
    "type": "message",
    "message": "Message content",
    "sender_id": 123,
    "sender_email": "user@example.com",
    "message_id": 456,
    "created_at": "2024-01-01T12:00:00Z"
}
```

### Error Messages (Server → Client)

```json
{
    "type": "error",
    "message": "Error description"
}
```

## Reconnection Strategy

The client implements exponential backoff for reconnection attempts:

- **Attempt 1**: 1 second delay
- **Attempt 2**: 2 seconds delay
- **Attempt 3**: 4 seconds delay
- **Attempt 4**: 8 seconds delay
- **Attempt 5**: 16 seconds delay
- **After 5 attempts**: Stops reconnecting and notifies user

## Testing

### Unit Tests

Run the unit tests by opening `docs/development/chat-client-test.html` in a browser:

```bash
open docs/development/chat-client-test.html
```

Or run the test suite programmatically:

```javascript
// Include chat-client.test.js
runTests();
```

### Manual Testing

Use the interactive test page for manual testing:

```bash
open docs/development/chat-client-test.html
```

## Integration

The ChatClient is integrated into the conversation detail template:

```html
{% load static %}

<script src="{% static 'js/chat-client.js' %}"></script>

<script>
    const chatClient = new ChatClient({{ conversation.id }});

    chatClient.onMessage((data) => {
        // Handle incoming message
    });

    chatClient.connect();

    window.addEventListener('beforeunload', () => {
        chatClient.disconnect();
    });
</script>
```

## Error Handling

The client handles various error scenarios:

- **Empty messages**: Rejected with validation error
- **Long messages**: Rejected if exceeding 5000 characters
- **Connection failures**: Automatic reconnection with exponential backoff
- **Send failures**: Returns `false` and logs error
- **Invalid JSON**: Logs error and continues

## Browser Compatibility

The ChatClient uses standard WebSocket API and is compatible with:

- Chrome 16+
- Firefox 11+
- Safari 7+
- Edge 12+
- Opera 12.1+

## Security Considerations

- Messages are sent over WebSocket (ws:// or wss://)
- Content is validated on both client and server
- XSS prevention is handled server-side with bleach
- Authentication is enforced at WebSocket connection time
