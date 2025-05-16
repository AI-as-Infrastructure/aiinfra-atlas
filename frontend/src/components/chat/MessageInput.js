import React from "react";

const MessageInput = ({ input, setInput, onSend }) => (
  <div className="inputContainer">
    <input
      type="text"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      className="input"
      placeholder="Type your question..."
      onKeyPress={(e) => {
        if (e.key === "Enter") onSend();
      }}
    />
    <button onClick={onSend} className="chatButton">
      Send
    </button>
  </div>
);

export default MessageInput;