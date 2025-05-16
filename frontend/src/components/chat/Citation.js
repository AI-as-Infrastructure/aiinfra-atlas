import React from "react";

const Citation = ({ source, isLast }) => {
  // Safety check to prevent crashes on malformed data
  if (!source || typeof source !== 'object') {
    console.error("Invalid source data for Citation component:", source);
    return null;
  }

  // Always use date for the citation link text, with fallback
  const displayText = source.date || "No date";
  
  // Use the quote field if available, otherwise fall back to content
  const quoteText = source.quote || (source.content ? 
    (source.content.length > 300 ? source.content.substring(0, 300) + "..." : source.content) 
    : "No content available");

  return (
    <span className="sourceItem">
      <span className="tooltip">
        {displayText}
        <span className="tooltiptext">
          {source.title && (
            <p>
              <strong>Title:</strong> {source.title}
            </p>
          )}
          <p>
            <strong>Date:</strong> {source.date || "N/A"}
          </p>
          <p>
            <strong>ID:</strong> {source.id || source.source_id || "N/A"}
          </p>
          <p>
            <strong>Corpus:</strong> {source.corpus || "N/A"}
          </p>
          {source.url && (
            <p>
              <strong>Source:</strong>{" "}
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                Open in new tab
              </a>
            </p>
          )}
          <p>
            <strong>Quote:</strong> {quoteText}
          </p>
          {source.has_more && source.full_content && (
            <p>
              <em>This citation has been truncated. Click "View all citations" to see the full content.</em>
            </p>
          )}
        </span>
      </span>
      {!isLast && "; "}
    </span>
  );
};

export default Citation;