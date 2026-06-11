/**
 * ChatClient - WebSocket client for real-time chat functionality
 *
 * Handles WebSocket connections, message sending/receiving, and automatic reconnection
 * with exponential backoff for the real-time chat feature.
 */
class ChatClient {
  /**
   * Initialize the ChatClient
   * @param {number} conversationId - The ID of the conversation
   */
  constructor(conversationId) {
    this.conversationId = conversationId;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.baseReconnectDelay = 1000; // 1 second
    this.messageCallbacks = [];
    this.connectionStatusCallbacks = [];
    this.isIntentionalDisconnect = false;
  }

  /**
   * Establish WebSocket connection
   * Validates: Requirements 2.2, 2.3
   */
  connect() {
    // Prevent multiple simultaneous connections
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)
    ) {
      console.warn("WebSocket is already connected or connecting");
      return;
    }

    // Construct WebSocket URL
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;

    try {
      this.socket = new WebSocket(wsUrl);
      this._setupEventHandlers();
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      this._notifyConnectionStatus("error", error.message);
      this._scheduleReconnect();
    }
  }

  /**
   * Set up WebSocket event handlers
   * @private
   */
  _setupEventHandlers() {
    this.socket.onopen = () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0; // Reset reconnect counter on successful connection
      this._notifyConnectionStatus("connected");
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (error) {
        console.error("Failed to parse message:", error);
      }
    };

    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      this._notifyConnectionStatus("error", "Connection error occurred");
    };

    this.socket.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      this._notifyConnectionStatus("disconnected", event.reason);

      // Attempt automatic reconnection if not intentionally disconnected
      // Validates: Requirement 2.5
      if (!this.isIntentionalDisconnect) {
        this._scheduleReconnect();
      }
    };
  }

  /**
   * Handle incoming message from WebSocket
   * @private
   * @param {Object} data - Message data
   */
  _handleMessage(data) {
    // Check if this is a rate limit error
    if (data.type === "rate_limit_error") {
      this._handleRateLimitError(data);
      return;
    }

    // Notify all registered callbacks
    this.messageCallbacks.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error("Error in message callback:", error);
      }
    });
  }

  /**
   * Handle rate limit error
   * @private
   * @param {Object} data - Rate limit error data
   */
  _handleRateLimitError(data) {
    console.warn("Rate limit exceeded:", data.message);
    this._notifyConnectionStatus("rate_limit", data.message, data.cooldown_seconds);
  }

  /**
   * Schedule reconnection with exponential backoff
   * Validates: Requirement 2.5
   * @private
   */
  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached");
      this._notifyConnectionStatus("failed", "Unable to reconnect after multiple attempts");
      return;
    }

    // Calculate delay with exponential backoff: 1s, 2s, 4s, 8s, 16s
    const delay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    console.log(
      `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );
    this._notifyConnectionStatus("reconnecting", `Reconnecting in ${delay / 1000}s...`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Send a message through the WebSocket
   * Validates: Requirement 2.2
   * @param {string} content - Message content to send
   * @returns {boolean} - True if message was sent, false otherwise
   */
  sendMessage(content) {
    // Validate content is not empty
    if (!content || typeof content !== "string") {
      console.error("Message content must be a non-empty string");
      return false;
    }

    const trimmedContent = content.trim();
    if (trimmedContent.length === 0) {
      console.error("Message content cannot be empty or whitespace only");
      return false;
    }

    // Validate message length
    if (trimmedContent.length > 5000) {
      console.error("Message content exceeds maximum length of 5000 characters");
      return false;
    }

    // Check WebSocket connection state
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not connected");
      this._notifyConnectionStatus("error", "Cannot send message: not connected");
      return false;
    }

    try {
      // Send message as JSON
      this.socket.send(
        JSON.stringify({
          message: trimmedContent,
        })
      );
      return true;
    } catch (error) {
      console.error("Failed to send message:", error);
      this._notifyConnectionStatus("error", "Failed to send message");
      return false;
    }
  }

  /**
   * Register a callback for incoming messages
   * Validates: Requirement 2.3
   * @param {Function} callback - Function to call when a message is received
   */
  onMessage(callback) {
    if (typeof callback !== "function") {
      console.error("Callback must be a function");
      return;
    }
    this.messageCallbacks.push(callback);
  }

  /**
   * Register a callback for connection status changes
   * @param {Function} callback - Function to call when connection status changes
   */
  onConnectionStatus(callback) {
    if (typeof callback !== "function") {
      console.error("Callback must be a function");
      return;
    }
    this.connectionStatusCallbacks.push(callback);
  }

  /**
   * Notify all connection status callbacks
   * @private
   * @param {string} status - Connection status (connected, disconnected, reconnecting, error, failed, rate_limit)
   * @param {string} message - Optional status message
   * @param {number} cooldownSeconds - Optional cooldown seconds for rate limiting
   */
  _notifyConnectionStatus(status, message = "", cooldownSeconds = 0) {
    this.connectionStatusCallbacks.forEach((callback) => {
      try {
        callback(status, message, cooldownSeconds);
      } catch (error) {
        console.error("Error in connection status callback:", error);
      }
    });
  }

  /**
   * Disconnect the WebSocket connection
   */
  disconnect() {
    this.isIntentionalDisconnect = true;

    if (this.socket) {
      // Close with normal closure code
      this.socket.close(1000, "Client disconnecting");
      this.socket = null;
    }

    // Reset state
    this.reconnectAttempts = 0;
    this._notifyConnectionStatus("disconnected", "Disconnected by user");
  }

  /**
   * Get current connection state
   * @returns {string} - Connection state (connecting, open, closing, closed, or null)
   */
  getConnectionState() {
    if (!this.socket) {
      return null;
    }

    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return "connecting";
      case WebSocket.OPEN:
        return "open";
      case WebSocket.CLOSING:
        return "closing";
      case WebSocket.CLOSED:
        return "closed";
      default:
        return "unknown";
    }
  }

  /**
   * Check if WebSocket is currently connected
   * @returns {boolean} - True if connected, false otherwise
   */
  isConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN;
  }
}

window.ChatClient = ChatClient;
