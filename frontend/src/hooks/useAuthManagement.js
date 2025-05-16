import { useAuth } from "react-oidc-context";
import envConfig from "../utils/envConfig";

export const useAuthManagement = () => {
  const auth = useAuth();
  
  const handleLogout = () => {
    const baseUrl = envConfig.api.frontendUrl || window.location.origin;
    const logoutUrl = `${envConfig.auth.logoutUrl}?client_id=${envConfig.auth.clientId}&logout_uri=${encodeURIComponent(
      baseUrl + "logout.html"
    )}`;
    window.location.href = logoutUrl;
  };
  
  return {
    isAuthenticated: auth.isAuthenticated,
    user: auth.user,
    logout: handleLogout,
    // You can add other auth-related functionality here
  };
};