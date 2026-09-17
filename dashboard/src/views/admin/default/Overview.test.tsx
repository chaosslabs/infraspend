import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from ".";
import { useAPIConfigurations } from "./components/hooks/useAPIConfigurations";
import { CallBackendService } from "utils";
const mockToken = jest.fn();
jest.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({ getAccessTokenSilently: mockToken }),
}));
jest.mock("./components/hooks/useAPIConfigurations");
jest.mock("utils", () => ({ CallBackendService: jest.fn() }));
const configurations = useAPIConfigurations as jest.Mock,
  backend = CallBackendService as jest.Mock;
beforeEach(() => jest.clearAllMocks());
test("configuration failures are not empty onboarding", () => {
  configurations.mockReturnValue({
    configurations: [],
    loading: false,
    error: "Offline",
    refresh: jest.fn(),
  });
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Offline");
  expect(screen.queryByText("Add a source")).not.toBeInTheDocument();
});
test("shows account-scoped budgets, valid zero, and missing records distinctly", async () => {
  const date = new Date(),
    month = `${String(date.getUTCMonth() + 1).padStart(
      2,
      "0"
    )}-${date.getUTCFullYear()}`;
  configurations.mockReturnValue({
    configurations: [
      { id: 1, type: "openai", identifier: "A" },
      { id: 2, type: "anthropic", identifier: "B" },
    ],
    loading: false,
  });
  backend.mockImplementation(async (path: string) => {
    if (path.includes("vendors-metrics/openai"))
      return { data: [{ month, cost: 0, currency: "USD" }] };
    if (path.includes("vendors-metrics/anthropic"))
      throw new Error("provider failed");
    if (path.includes("vendors-forecast"))
      return {
        forecast: [{ month, cost: 100, best_case: 80, worst_case: 120 }],
      };
    return {
      data: [
        {
          identifier: "Other",
          budgets: { budgets: [{ month, amount: 9000 }] },
        },
        { identifier: "A", budgets: { budgets: [{ month, amount: 150 }] } },
      ],
    };
  });
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  );
  const link = await screen.findByRole("link", { name: "OpenAI API" });
  const row = within(link.closest("tr")!);
  expect(row.getByText("$0.00")).toBeInTheDocument();
  expect(row.getByText("$150.00")).toBeInTheDocument();
  expect(row.getByText("$50.00 under")).toBeInTheDocument();
  expect(screen.getByText("Unknown")).toBeInTheDocument();
  expect(screen.queryByText("$9,000.00")).not.toBeInTheDocument();
});
