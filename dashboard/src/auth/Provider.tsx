import { Auth0Provider } from "@auth0/auth0-react";
import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { safeReturnTo } from "./navigation";

export const authConfigured = Boolean(
  process.env.REACT_APP_AUTH0_DOMAIN?.trim() &&
  process.env.REACT_APP_AUTH0_CLIENT_ID?.trim() &&
  process.env.REACT_APP_AUTH0_AUDIENCE?.trim()
);

export default function Provider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  if (!authConfigured) return <>{children}</>;
  return (
    <Auth0Provider
      domain={process.env.REACT_APP_AUTH0_DOMAIN!.trim()}
      clientId={process.env.REACT_APP_AUTH0_CLIENT_ID!.trim()}
      authorizationParams={{
        audience: process.env.REACT_APP_AUTH0_AUDIENCE!.trim(),
        redirect_uri: window.location.origin,
      }}
      onRedirectCallback={(appState) => navigate(safeReturnTo(appState?.returnTo), { replace: true })}
    >
      {children}
    </Auth0Provider>
  );
}
