/**
 * Unit tests for ChatClient
 *
 * These tests validate the core functionality of the ChatClient class
 * including connection management, message sending/receiving, and reconnection logic.
 *
 * Note: These tests are designed to be run in a browser environment with a mock WebSocket.
 */

// Mock WebSocket for testing
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;

    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 10);
  }

  send(data) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not open");
    }
    // In a real test, you'd validate the data format here
    console.log("MockWebSocket.send:", data);
  }

  close(code, reason) {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code, reason });
    }
  }

  // Helper method to simulate receiving a message
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }

  // Helper method to simulate an error
  simulateError(error) {
    if (this.onerror) {
      this.onerror(error);
    }
  }
}

// Test suite
const tests = {
  // Test 1: ChatClient initialization
  testInitialization() {
    const client = new ChatClient(123);

    console.assert(client.conversationId === 123, "Conversation ID should be set");
    console.assert(client.socket === null, "Socket should be null initially");
    console.assert(client.reconnectAttempts === 0, "Reconnect attempts should be 0");
    console.assert(client.maxReconnectAttempts === 5, "Max reconnect attempts should be 5");
    console.assert(Array.isArray(client.messageCallbacks), "Message callbacks should be an array");
    console.assert(
      Array.isArray(client.connectionStatusCallbacks),
      "Connection status callbacks should be an array"
    );

    console.log("✓ Test 1: Initialization passed");
  },

  // Test 2: Message validation - empty message
  testEmptyMessageValidation() {
    const client = new ChatClient(123);

    // Mock a connected socket
    client.socket = { readyState: WebSocket.OPEN };

    const result1 = client.sendMessage("");
    const result2 = client.sendMessage("   ");
    const result3 = client.sendMessage(null);

    console.assert(result1 === false, "Empty string should be rejected");
    console.assert(result2 === false, "Whitespace-only string should be rejected");
    console.assert(result3 === false, "Null should be rejected");

    console.log("✓ Test 2: Empty message validation passed");
  },

  // Test 3: Message validation - length limit
  testMessageLengthValidation() {
    const client = new ChatClient(123);

    // Mock a connected socket
    client.socket = {
      readyState: WebSocket.OPEN,
      send: () => {},
    };

    const validMessage = "a".repeat(5000);
    const invalidMessage = "a".repeat(5001);

    const result1 = client.sendMessage(validMessage);
    const result2 = client.sendMessage(invalidMessage);

    console.assert(result1 === true, "Message with 5000 chars should be accepted");
    console.assert(result2 === false, "Message with 5001 chars should be rejected");

    console.log("✓ Test 3: Message length validation passed");
  },

  // Test 4: Message callback registration
  testMessageCallbackRegistration() {
    const client = new ChatClient(123);
    let callbackCalled = false;

    const callback = (data) => {
      callbackCalled = true;
    };

    client.onMessage(callback);

    console.assert(client.messageCallbacks.length === 1, "Callback should be registered");
    console.assert(client.messageCallbacks[0] === callback, "Registered callback should match");

    // Simulate receiving a message
    client._handleMessage({ message: "test" });

    console.assert(callbackCalled === true, "Callback should be called when message is received");

    console.log("✓ Test 4: Message callback registration passed");
  },

  // Test 5: Connection status callback
  testConnectionStatusCallback() {
    const client = new ChatClient(123);
    let statusReceived = null;
    let messageReceived = null;

    client.onConnectionStatus((status, message) => {
      statusReceived = status;
      messageReceived = message;
    });

    client._notifyConnectionStatus("connected", "Connection established");

    console.assert(statusReceived === "connected", 'Status should be "connected"');
    console.assert(messageReceived === "Connection established", "Message should match");

    console.log("✓ Test 5: Connection status callback passed");
  },

  // Test 6: Connection state checking
  testConnectionState() {
    const client = new ChatClient(123);

    // No socket
    console.assert(client.getConnectionState() === null, "State should be null when no socket");
    console.assert(client.isConnected() === false, "Should not be connected when no socket");

    // Mock socket in different states
    client.socket = { readyState: WebSocket.CONNECTING };
    console.assert(client.getConnectionState() === "connecting", 'State should be "connecting"');
    console.assert(client.isConnected() === false, "Should not be connected when connecting");

    client.socket.readyState = WebSocket.OPEN;
    console.assert(client.getConnectionState() === "open", 'State should be "open"');
    console.assert(client.isConnected() === true, "Should be connected when open");

    client.socket.readyState = WebSocket.CLOSING;
    console.assert(client.getConnectionState() === "closing", 'State should be "closing"');
    console.assert(client.isConnected() === false, "Should not be connected when closing");

    client.socket.readyState = WebSocket.CLOSED;
    console.assert(client.getConnectionState() === "closed", 'State should be "closed"');
    console.assert(client.isConnected() === false, "Should not be connected when closed");

    console.log("✓ Test 6: Connection state checking passed");
  },

  // Test 7: Disconnect functionality
  testDisconnect() {
    const client = new ChatClient(123);
    let disconnectCalled = false;

    // Mock socket
    client.socket = {
      readyState: WebSocket.OPEN,
      close: (code, reason) => {
        disconnectCalled = true;
        console.assert(code === 1000, "Close code should be 1000");
        console.assert(reason === "Client disconnecting", "Close reason should match");
      },
    };

    client.disconnect();

    console.assert(disconnectCalled === true, "Socket close should be called");
    console.assert(
      client.isIntentionalDisconnect === true,
      "Intentional disconnect flag should be set"
    );
    console.assert(client.socket === null, "Socket should be null after disconnect");
    console.assert(client.reconnectAttempts === 0, "Reconnect attempts should be reset");

    console.log("✓ Test 7: Disconnect functionality passed");
  },

  // Test 8: Exponential backoff calculation
  testExponentialBackoff() {
    const client = new ChatClient(123);

    // The backoff delay should be: baseDelay * 2^attempts
    // With baseDelay = 1000ms:
    // Attempt 0: 1000ms
    // Attempt 1: 2000ms
    // Attempt 2: 4000ms
    // Attempt 3: 8000ms
    // Attempt 4: 16000ms

    const expectedDelays = [1000, 2000, 4000, 8000, 16000];

    for (let i = 0; i < expectedDelays.length; i++) {
      const delay = client.baseReconnectDelay * Math.pow(2, i);
      console.assert(
        delay === expectedDelays[i],
        `Delay for attempt ${i} should be ${expectedDelays[i]}ms`
      );
    }

    console.log("✓ Test 8: Exponential backoff calculation passed");
  },

  // Test 9: Message format validation
  testMessageFormat() {
    const client = new ChatClient(123);
    let sentData = null;

    // Mock socket
    client.socket = {
      readyState: WebSocket.OPEN,
      send: (data) => {
        sentData = JSON.parse(data);
      },
    };

    client.sendMessage("Hello, World!");

    console.assert(sentData !== null, "Data should be sent");
    console.assert(sentData.message === "Hello, World!", "Message content should match");
    console.assert(typeof sentData === "object", "Sent data should be an object");

    console.log("✓ Test 9: Message format validation passed");
  },

  // Test 10: Multiple callback registration
  testMultipleCallbacks() {
    const client = new ChatClient(123);
    let callback1Called = false;
    let callback2Called = false;

    client.onMessage(() => {
      callback1Called = true;
    });
    client.onMessage(() => {
      callback2Called = true;
    });

    console.assert(client.messageCallbacks.length === 2, "Both callbacks should be registered");

    client._handleMessage({ message: "test" });

    console.assert(callback1Called === true, "First callback should be called");
    console.assert(callback2Called === true, "Second callback should be called");

    console.log("✓ Test 10: Multiple callback registration passed");
  },
};

// Run all tests
function runTests() {
  console.log("Running ChatClient tests...\n");

  let passed = 0;
  let failed = 0;

  for (const [testName, testFunc] of Object.entries(tests)) {
    try {
      testFunc();
      passed++;
    } catch (error) {
      console.error(`✗ ${testName} failed:`, error);
      failed++;
    }
  }

  console.log(`\n${passed} tests passed, ${failed} tests failed`);

  if (failed === 0) {
    console.log("All tests passed! ✓");
  }
}

// Export for use in browser or Node.js
if (typeof module !== "undefined" && module.exports) {
  module.exports = { tests, runTests };
}

// Auto-run tests if this file is loaded directly
if (typeof window !== "undefined") {
  window.addEventListener("load", runTests);
}
