import React from "react";
import Message from "./Message";

const ChatBox = ({ chatHistory, isStreaming, onMessageComplete, sessionId }) => {
  return (
    <div className="chatBox">
      {chatHistory.map((chat, index) => {
        // For AI messages with processing flag, show the inline spinner
        if (chat.sender === "ai" && chat.processing === true) {
          return (
            <div key={index} className="aiMessage">
              <div className="messageContent">
                <div className="processing-doc-context">
                <div className="spinner-inline"></div>
                  Processing document context...                  
                </div>
              </div>
            </div>
          );
        }
        
        // Otherwise render a normal message
        return (
          <Message 
            key={index} 
            chat={chat}
            sessionId={sessionId}
            onComplete={() => onMessageComplete && onMessageComplete(chat)}
          />
        );
      })}
    </div>
  );
};

export default ChatBox;