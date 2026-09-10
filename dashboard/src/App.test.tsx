import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import App from "./App";

jest.mock("@auth0/auth0-react");
jest.mock("auth/Provider", () => ({ authConfigured: true }));
jest.mock("layouts/admin", () => () => <div>Private workspace</div>);
jest.mock("layouts/auth", () => () => <div>Sign in page</div>);
jest.mock("views/demo/DemoDashboard", () => () => <div>Public demo</div>);

function visit(path: string, state: object) {
  (useAuth0 as jest.Mock).mockReturnValue(state);
  render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
}

test("blocks private workspace for anonymous visitors", () => {
  visit("/admin/default", { isAuthenticated: false, isLoading: false });
  expect(screen.queryByText("Private workspace")).toBeNull();
  expect(screen.getByText("Sign in page")).toBeTruthy();
});
test("allows authenticated workspace access", () => {
  visit("/admin/default", { isAuthenticated: true, isLoading: false });
  expect(screen.getByText("Private workspace")).toBeTruthy();
});
test.each([{ isLoading: true }, { error: new Error("Failed") }])("keeps demo accessible during auth problems", (state) => {
  visit("/demo", state);
  expect(screen.getByText("Public demo")).toBeTruthy();
});
