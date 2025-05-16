import React from "react";
import createFullPromptHtml from "./FullPromptTemplate";

const ConfigBox = ({ config, onExport }) => {
  const renderValue = (value) => {
    if (typeof value === "object" && value !== null) {
      return JSON.stringify(value);
    }
    return value;
  };

  // New function to format the search type
  const formatSearchType = (searchType) => {
    if (searchType === "similarity_score_threshold") {
      return "Similarity score threshold";
    }
    return searchType;
  };

  // Function to format search kwargs in a more readable way
  const formatSearchKwargs = (kwargs) => {
    if (!kwargs || typeof kwargs !== "object") {
      return "None";
    }
    const k = kwargs.k || 0;
    const citationLimit = kwargs.citation_limit || 0;
    const scoreThreshold = kwargs.score_threshold || 0;
    return `Fetch-K=${k}; Citation limit=${citationLimit}; Score threshold=${scoreThreshold}`;
  };

  // Function to open the system prompt in a new tab
  const openPromptInNewTab = (e) => {
    e.preventDefault();
    const promptText = config.FULL_SYSTEM_PROMPT || config.SYSTEM_PROMPT || "";
    const htmlContent = createFullPromptHtml(promptText);
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const isPromptTruncated = config.SYSTEM_PROMPT && 
                           config.FULL_SYSTEM_PROMPT && 
                           config.SYSTEM_PROMPT.length < config.FULL_SYSTEM_PROMPT.length;
                           
  const renderSystemPrompt = () => {
    if (!isPromptTruncated) {
      return renderValue(config.SYSTEM_PROMPT);
    }
    return (
      <>
        {config.SYSTEM_PROMPT}{' '}
        <a 
          href="#"
          onClick={openPromptInNewTab}
          className="full-prompt-link"
        >
          View full prompt
        </a>
      </>
    );
  };

  return (
    <div className="configBox">
      <div className="configTitle">
        <strong>Test Target</strong>
      </div>
      <div className="configItem">
        <strong>LLM:</strong> {renderValue(config.LLM)}
      </div>
      <div className="configItem">
        <strong>Index Name:</strong> {renderValue(config.INDEX_NAME)}
      </div>
      <div className="configItem">
        <strong>Embedding Model:</strong> {renderValue(config.EMBEDDING_MODEL)}
      </div>
      <div className="configItem">
        <strong>Search Type:</strong> {renderValue(formatSearchType(config.SEARCH_TYPE))}
      </div>
      <div className="configItem">
        <strong>Search Kwargs:</strong> {formatSearchKwargs(config.SEARCH_KWARGS)}
      </div>
      <div className="configItem">
        <strong>Algorithm:</strong> {renderValue(config.ALGORITHM)}
      </div>
      <div className="configItem">
        <strong>Chunk Size:</strong> {renderValue(config.CHUNK_SIZE)}
      </div>
      <div className="configItem">
        <strong>Chunk Overlap:</strong> {renderValue(config.CHUNK_OVERLAP)}
      </div>
      <div className="configItem">
        <strong>System Prompt:</strong> {renderSystemPrompt()}
      </div>
      <button onClick={onExport} className="exportButton">
        Export Chat Session
      </button>
    </div>
  );
};

export default ConfigBox;