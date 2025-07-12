# Authentication

This application implements AWS Cognito for user authentication. The authentication system is designed to be flexible and can be easily toggled on or off based on deployment requirements.

## Configuration

Authentication can be controlled via the `.env` file using the `VITE_USE_COGNITO_AUTH` setting:

- Set to `false` to disable authentication 
- Set to `true` to enable AWS Cognito authentication

## AWS Cognito Setup

To enable authentication, you need to:

1. **Create a Cognito User Pool** in the AWS Cognito console
2. **Configure the Cognito environment variables** using the template provided in `config/.env.template`

The required Cognito variables include:
- `VITE_USE_COGNITO_AUTH` - Toggle authentication on/off
- `VITE_COGNITO_REGION` - AWS region for your Cognito User Pool
- `VITE_COGNITO_DOMAIN` - Cognito domain URL
- `VITE_COGNITO_USERPOOL_ID` - User Pool ID
- `VITE_COGNITO_CLIENT_ID` - App Client ID
- `VITE_COGNITO_LOGIN_REDIRECT_URI` - Callback URL after login
- `VITE_COGNITO_LOGOUT_REDIRECT_URI` - Redirect URL after logout
- `VITE_COGNITO_LOGOUT_ENDPOINT` - Cognito logout endpoint
- `VITE_COGNITO_OAUTH_SCOPE` - OAuth scopes (typically "openid email profile")

For detailed environment file setup, refer to the [Configuration Guide](configuration.md).