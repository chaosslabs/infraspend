import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import VendorDetails from "views/admin/vendors/components/VendorDetails";
import APIConfig from "../APIConfig";
import VendorMetrics from "../VendorMetrics";
import DemoDashboard from "views/demo/DemoDashboard";
import { useAPIConfigurations } from "../hooks/useAPIConfigurations";
import { CallBackendService } from "utils";

const mockGetToken = jest.fn();
const mockFetchBudget = jest.fn();
jest.mock("views/admin/vendors/hooks/useBudgetPlans", () => ({
  useBudgetPlans: () => ({
    loading: false,
    budgetPlan: null,
    createBudgetPlan: jest.fn(),
    fetchBudgetPlan: mockFetchBudget,
  }),
}));
jest.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({ getAccessTokenSilently: mockGetToken }),
}));
jest.mock("../hooks/useAPIConfigurations");
jest.mock("utils", () => ({ CallBackendService: jest.fn() }));
jest.mock("components/charts/BarChart", () => () => <div>Cost chart</div>);
const configurations = useAPIConfigurations as jest.Mock;
const backend = CallBackendService as jest.Mock;
const refresh = jest.fn();
beforeEach(() => {
  jest.clearAllMocks();
  configurations.mockReturnValue({
    configurations: [],
    loading: false,
    error: null,
    refresh,
  });
  backend.mockResolvedValue({ data: [] });
});

it.each([
  ["OpenAI API", "openai", false],
  ["Claude API (Anthropic)", "anthropic", false],
  ["Claude subscription", "claude", true],
  ["ChatGPT subscription", "chatgpt", true],
] as const)(
  "connects %s from the source picker",
  async (label, vendor, manual) => {
    render(
      <MemoryRouter>
        <APIConfig />
      </MemoryRouter>
    );
    fireEvent.click(
      screen.getByRole("heading", { name: label }).closest("button")
    );
    const drawer = within(screen.getByRole("dialog"));
    expect(drawer.getByLabelText("Account name")).toHaveValue(
      "Default Configuration"
    );
    fireEvent.change(drawer.getByLabelText("Account name"), {
      target: { value: "  Research team  " },
    });
    if (manual) {
      fireEvent.change(drawer.getByLabelText("Billing month"), {
        target: { value: "2026-01" },
      });
      fireEvent.change(drawer.getByLabelText("Monthly total (USD)"), {
        target: { value: "25" },
      });
    } else {
      fireEvent.change(drawer.getByLabelText("Organization admin API key"), {
        target: { value: "test-key" },
      });
    }
    fireEvent.click(
      drawer.getByRole("button", {
        name: manual ? "Save monthly total" : "Save API credentials",
      })
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(backend.mock.calls[0][0]).toBe(
      `/v1/configuration/${manual ? "subscriptions" : "ai"}/${vendor}`
    );
    expect(JSON.parse(backend.mock.calls[0][2].body).identifier).toBe(
      "Research team"
    );
  }
);

it("edits a saved account without changing its identity and names additional accounts", async () => {
  configurations.mockReturnValue({
    configurations: [{ id: 7, type: "chatgpt", identifier: "Finance" }],
    loading: false,
    error: null,
    refresh,
  });
  render(
    <MemoryRouter>
      <APIConfig />
    </MemoryRouter>
  );
  fireEvent.click(screen.getByRole("button", { name: "Edit" }));
  expect(screen.getByLabelText("Account name")).toHaveValue("Finance");
  expect(screen.getByLabelText("Account name")).toHaveAttribute("readonly");
  await waitFor(() =>
    expect(backend).toHaveBeenCalledWith(
      "/v1/vendors-metrics/chatgpt?identifier=Finance",
      mockGetToken
    )
  );
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(
    screen
      .getByRole("heading", { name: "ChatGPT subscription" })
      .closest("button")
  );
  expect(screen.getByLabelText("Account name")).toHaveValue(
    "ChatGPT subscription account 2"
  );
  expect(screen.getByLabelText("Account name")).not.toHaveAttribute("readonly");
});

it.each([
  ["openai", "OpenAI API", "Fresh"],
  ["anthropic", "Claude API", "Fresh"],
  ["claude", "Claude subscription", "Manual entry"],
  ["chatgpt", "ChatGPT subscription", "Manual entry"],
] as const)(
  "renders %s costs and forecast with the correct provenance",
  (vendor, label, status) => {
    render(
      <MemoryRouter>
        <VendorMetrics vendor={vendor} title={`${label} costs`} demo />
      </MemoryRouter>
    );
    expect(screen.getByText(`${label} source`)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(status);
    expect(screen.getByText("Cost chart")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Forecast" }));
    expect(
      screen.getByRole("columnheader", { name: "Trend forecast" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Connect source" })
    ).toHaveAttribute("href", "/auth/sign-in");
  }
);

it("includes all seven sources in the demo with two manual subscription labels", () => {
  render(
    <MemoryRouter>
      <DemoDashboard />
    </MemoryRouter>
  );
  fireEvent.click(screen.getByText("Explore sample source records"));
  expect(screen.getByText("7 sample sources")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Claude API cost evidence" })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "OpenAI API cost evidence" })
  ).toBeInTheDocument();
  expect(screen.getAllByText("Manual entry")).toHaveLength(2);
});

it.each([
  ["openai", "OpenAI API", false],
  ["anthropic", "Claude API", false],
  ["claude", "Claude subscription", true],
  ["chatgpt", "ChatGPT subscription", true],
] as const)(
  "keeps the named account when loading %s details",
  async (vendor, label, manual) => {
    backend.mockResolvedValue({
      data: [{ month: "01-2026", cost: 25 }],
      forecast: [],
      growth_rates: { trend_based: 0, best_case: 0, worst_case: 0 },
      sums: { total_forecast: 0, total_best_case: 0, total_worst_case: 0 },
    });
    render(
      <MemoryRouter
        initialEntries={[
          `/admin/vendors/${vendor}?identifier=Research%20%26%20Finance`,
        ]}
      >
        <Routes>
          <Route path="/admin/vendors/:vendor" element={<VendorDetails />} />
        </Routes>
      </MemoryRouter>
    );
    expect(
      await screen.findByRole("heading", { name: `${label} Details` })
    ).toBeInTheDocument();
    expect(backend).toHaveBeenCalledWith(
      `/v1/vendors-metrics/${vendor}?identifier=Research%20%26%20Finance`,
      mockGetToken
    );
    expect(backend).toHaveBeenCalledWith(
      `/v1/vendors-forecast/${vendor}?identifier=Research%20%26%20Finance`,
      mockGetToken
    );
    expect(screen.getByText("$25.00")).toBeInTheDocument();
    const provenance = screen.queryByText(
      "Manual subscription entries in USD; no automatic billing sync."
    );
    if (manual) expect(provenance).toBeInTheDocument();
    else expect(provenance).not.toBeInTheDocument();
  }
);
