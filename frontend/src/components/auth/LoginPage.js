import React from "react";
import { useAuth } from "react-oidc-context";
import "../../index.scss";

// Define the login-specific header here
const LoginHeader = ({ title }) => {
    return (
        <header className="header">
            <div className="header-left">{title}</div>
            {/* Omit header-right actions */}
        </header>
    );
};

const Footer = () => {
    return (
        <footer className="login-footer">
            <p>
                ATLAS is an output of the{" "}
                <a href="https://aiinfra.anu.edu.au" target="_blank" rel="noreferrer">
                    AI as Infrastructure (AIINFRA)
                </a>
                {" "}project. Hosted by the ANU HASS Digital Research Hub.
            </p>
        </footer>
    );
};

const LoginPage = () => {
    const auth = useAuth();

    // Add debugging for auth state
    console.log('Auth State:', {
        isLoading: auth.isLoading,
        isAuthenticated: auth.isAuthenticated,
        activeNavigator: auth.activeNavigator,
        error: auth.error ? {
            name: auth.error.name,
            message: auth.error.message,
            stack: auth.error.stack
        } : null
    });

    if (auth.isLoading) {
        return <div>Loading...</div>;
    }

    const handleLogin = () => {
        // Debug authentication configuration
        console.log('Auth Configuration:', {
            authority: auth.settings.authority,
            client_id: auth.settings.client_id,
            redirect_uri: auth.settings.redirect_uri,
            response_type: auth.settings.response_type,
            scope: auth.settings.scope
        });
        
        // Add try-catch to catch any errors during signin
        try {
            console.log('Attempting to sign in...');
            auth.signinRedirect();
            console.log('signinRedirect called successfully');
        } catch (error) {
            console.error('Error during signin:', error);
        }
    };

    return (
        <div className="login-container">
            <LoginHeader title="ATLAS: Analysis and Testing of Language Models for Archival Systems" />
            <div className="login-content">
                <button className="login-btn" onClick={handleLogin}>
                    Sign In
                </button>
            </div>
            <Footer />
        </div>
    );
};

export default LoginPage;