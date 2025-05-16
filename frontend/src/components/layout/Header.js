import React from 'react';
import { Link } from 'react-router-dom';

const Header = ({ title, onLogout, onRefresh, showSessionMessage, showAbout = true, isAboutPage = false }) => {
  return (
    <header className="header">
      <div className="header-left">
        <p>{title}</p>
      </div>
      <div className="header-right">
        {showSessionMessage && !isAboutPage && (
          <span className="session-message-inline">Session refreshed</span>
        )}
        
        {/* Show different buttons based on page */}
        {isAboutPage ? (
          <Link to="/" className="link-button">
            Home
          </Link>
        ) : (
          <>
            <button 
              className="link-button" 
              onClick={onRefresh}
              aria-label="Start new session"
            >
              New Session
            </button>
            <span className="separator">|</span>
            {showAbout && (
              <>
                <Link to="/about" className="link-button">
                  About
                </Link>
                <span className="separator">|</span>
              </>
            )}
            <button 
              className="link-button" 
              onClick={onLogout}
              aria-label="Log out"
            >
              Logout
            </button>
          </>
        )}
      </div>
    </header>
  );
};

export default Header;