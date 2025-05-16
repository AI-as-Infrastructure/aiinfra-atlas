import React from "react";
import 'process/browser';
import { createRoot } from "react-dom/client";
import { AuthProvider } from "react-oidc-context";
import App from "./App";
import envConfig from "./utils/envConfig";

// Log the envConfig values for debugging
console.log('Environment Config:', {
    issuerUrl: envConfig.auth.issuerUrl,
    clientId: envConfig.auth.clientId,
    redirectUri: envConfig.auth.redirectUri,
    oauthScope: envConfig.auth.oauthScope,
});

const oidcConfig = {
    authority: envConfig.auth.issuerUrl,
    client_id: envConfig.auth.clientId,
    redirect_uri: envConfig.auth.redirectUri,
    response_type: "code",
    scope: envConfig.auth.oauthScope,
    loadUserInfo: true,
    onSigninCallback: () => {
        window.history.replaceState(
            {},
            document.title,
            window.location.pathname
        )
    }
};

// Log the final OIDC config
console.log('OIDC Config:', oidcConfig);

// Get the root element
const container = document.getElementById("root");

// Create a root
const root = createRoot(container);

// Render your app
root.render(
    <React.StrictMode>
        <AuthProvider {...oidcConfig}>
            <App />
        </AuthProvider>
    </React.StrictMode>
);