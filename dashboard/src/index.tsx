import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Auth0Provider } from '@auth0/auth0-react';
import "./index.css";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root"));
const auth0Domain = process.env.REACT_APP_AUTH0_DOMAIN ?? "";
const auth0ClientId = process.env.REACT_APP_AUTH0_CLIENT_ID ?? "";
const auth0Audience = process.env.REACT_APP_AUTH0_AUDIENCE;

root.render(
  <Auth0Provider
      domain={auth0Domain}
      clientId={auth0ClientId}
      authorizationParams={{
        ...(auth0Audience ? { audience: auth0Audience } : {}),
        redirect_uri: window.location.origin,
      }}
    >
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </Auth0Provider>
);
