import React from 'react';
import Citation from './Citation';
import createCitationsHtml from './CitationsTemplate';

const Message = ({ chat, sessionId, onComplete }) => {
  // Generate a unique qa_id for this message if it doesn't have one
  React.useEffect(() => {
    if (chat.sender === 'ai' && !chat.qa_id) {
      // Your existing code
    }
  }, [chat]);

  React.useEffect(() => {
    // Your existing code
  }, [chat, onComplete]);

  const handleOpenAllCitations = (e) => {
    e.preventDefault();
    if (!chat.sources || chat.sources.length === 0) return;
    
    // Generate HTML using the template
    const htmlContent = createCitationsHtml(chat.sources);
    
    // Create a Blob with the HTML content
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    // Open the URL in a new tab
    window.open(url, '_blank');
    
    // Clean up the URL object after a delay
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const displayedCitations = chat.sources && chat.sources.length > 0 
    ? chat.sources.slice(0, 9) 
    : [];
  
  const citationsCount = chat.sources ? chat.sources.length : 0;

  return (
    <div className={chat.sender === "user" ? "userMessage" : "aiMessage"}>
      <div className="messageContent">{chat.message}</div>
      {chat.sender === "ai" && (
        <>
          {chat.sources && chat.sources.length > 0 && (
            <div className="citations-container">
              <div className="citations">
                {displayedCitations.map((source, sourceIndex) => (
                  <Citation 
                    key={sourceIndex}
                    source={source}
                    isLast={sourceIndex === displayedCitations.length - 1 && citationsCount <= 9} 
                  />
                ))}
                {citationsCount > 0 && (
                  <span className="sourceItem open-all-citations">
                    <span className="tooltip" onClick={handleOpenAllCitations}>
                      View all {citationsCount > 9 ? citationsCount : ""} citations
                    </span>
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Message;