import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import SignIn from "views/auth/SignIn";

jest.mock("@auth0/auth0-react");
jest.mock("auth/Provider", () => ({ authConfigured: true }));
jest.mock("utils/gtm", () => ({ trackPageView: jest.fn(), trackEvent: jest.fn() }));

test("passes deep link to Auth0 and allows retry after rejection", async () => {
  const loginWithRedirect = jest.fn().mockRejectedValue(new Error("Network unavailable"));
  (useAuth0 as jest.Mock).mockReturnValue({ loginWithRedirect, isLoading: false });
  render(<MemoryRouter initialEntries={[{ pathname: "/auth/sign-in", state: { returnTo: "/admin/vendors?month=9" } }]}><SignIn /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Please try again"));
  expect(loginWithRedirect).toHaveBeenCalledWith({ appState: { returnTo: "/admin/vendors?month=9" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await waitFor(() => expect(loginWithRedirect).toHaveBeenCalledTimes(2));
});
