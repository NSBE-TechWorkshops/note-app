import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN;
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
const redirectUri = import.meta.env.VITE_COGNITO_REDIRECT_URI ?? "http://localhost:5173/callback";
const logoutUri = import.meta.env.VITE_COGNITO_LOGOUT_URI ?? "http://localhost:5173/";
const region = cognitoDomain.split(".auth.")[1]?.split(".amazoncognito.com")[0] ?? "us-east-1";
const issuer = `https://cognito-idp.${region}.amazonaws.com/${userPoolId}`;
const hostedUi = `https://${cognitoDomain}`;

export const userManager = new UserManager({
  authority: issuer,
  metadata: {
    issuer,
    authorization_endpoint: `${hostedUi}/oauth2/authorize`,
    token_endpoint: `${hostedUi}/oauth2/token`,
    userinfo_endpoint: `${hostedUi}/oauth2/userInfo`,
    jwks_uri: `${issuer}/.well-known/jwks.json`,
    end_session_endpoint: `${hostedUi}/logout`,
  },
  client_id: clientId,
  redirect_uri: redirectUri,
  response_type: "code",
  scope: "openid email profile",
  post_logout_redirect_uri: logoutUri,
  userStore: new WebStorageStateStore({ store: window.localStorage }),
});

export async function getAccessToken() {
  return (await userManager.getUser())?.access_token;
}
