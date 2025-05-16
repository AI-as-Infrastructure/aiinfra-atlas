import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "react-oidc-context";

const Callback = () => {
  const auth = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!auth.isLoading && !auth.error) {
      if (auth.isAuthenticated) {
        navigate("/", { replace: true });
      }
    }
  }, [auth, navigate]);

  if (auth.isLoading) {
    return <div>Authenticating...</div>;
  }

  if (auth.error) {
    console.error("Auth Error:", auth.error);
    return (
      <div>
        <h3>Authentication Error</h3>
        <p>Error Type: {auth.error.name}</p>
        <p>Message: {auth.error.message}</p>
        <button onClick={() => auth.signinRedirect()}>Try Again</button>
      </div>
    );
  }

  return <div>Completing authentication...</div>;
};

export default Callback;