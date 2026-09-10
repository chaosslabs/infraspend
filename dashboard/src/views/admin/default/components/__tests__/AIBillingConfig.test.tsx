import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  OpenAIConfig,
  AnthropicConfig,
  ClaudeConfig,
  ChatGPTConfig,
} from "../AIBillingConfig";
import { CallBackendService } from "utils";
import { deriveSourceHealth } from "../SourceHealth";
const mockGetToken = jest.fn();
jest.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({ getAccessTokenSilently: mockGetToken }),
}));
jest.mock("utils", () => ({ CallBackendService: jest.fn() }));
const backend = CallBackendService as jest.Mock;
beforeEach(() => backend.mockReset());
it.each([
  ["openai", OpenAIConfig],
  ["anthropic", AnthropicConfig],
] as const)("saves %s API credentials", async (provider, Component) => {
  backend.mockResolvedValue({});
  const configured = jest.fn();
  render(<Component onConfigured={configured} initialIdentifier="Team" />);
  fireEvent.change(screen.getByLabelText("Organization admin API key"), {
    target: { value: "test-key" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save API credentials" }));
  await waitFor(() => expect(configured).toHaveBeenCalled());
  expect(backend.mock.calls[0][0]).toBe(`/v1/configuration/ai/${provider}`);
  expect(JSON.parse(backend.mock.calls[0][2].body)).toEqual({
    identifier: "Team",
    api_key: "test-key",
  });
  expect(screen.getByLabelText("Organization admin API key")).toHaveValue("");
});
it.each([
  ["claude", ClaudeConfig],
  ["chatgpt", ChatGPTConfig],
] as const)("saves %s monthly charge", async (provider, Component) => {
  backend.mockResolvedValue({});
  const configured = jest.fn();
  render(<Component onConfigured={configured} />);
  expect(
    screen.queryByLabelText("Organization admin API key")
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Billing month"), {
    target: { value: "2026-01" },
  });
  fireEvent.change(screen.getByLabelText("Monthly total (USD)"), {
    target: { value: "22.50" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save monthly total" }));
  await waitFor(() => expect(configured).toHaveBeenCalled());
  expect(backend.mock.calls[0][0]).toBe(
    `/v1/configuration/subscriptions/${provider}`
  );
  expect(JSON.parse(backend.mock.calls[0][2].body)).toEqual({
    identifier: "Default Configuration",
    month: "01-2026",
    cost: "22.50",
    currency: "USD",
  });
});
it("prefills existing months without inventing missing costs", async () => {
  backend.mockResolvedValue({ data: [{ month: "01-2026", cost: 20 }] });
  render(
    <ClaudeConfig existingConfig lockIdentifier initialIdentifier="Team A" />
  );
  await screen.findByText(/Saved months: 01-2026/);
  expect(backend.mock.calls[0][0]).toContain("identifier=Team%20A");
  expect(screen.getByLabelText("Account name")).toHaveAttribute("readonly");
  fireEvent.change(screen.getByLabelText("Billing month"), {
    target: { value: "2026-01" },
  });
  expect(screen.getByLabelText("Monthly total (USD)")).toHaveValue(20);
  fireEvent.change(screen.getByLabelText("Billing month"), {
    target: { value: "2026-02" },
  });
  expect(screen.getByLabelText("Monthly total (USD)")).toHaveValue(null);
});
it("shows save errors without reporting success", async () => {
  backend.mockRejectedValue(new Error("private provider detail"));
  const configured = jest.fn();
  render(<OpenAIConfig onConfigured={configured} />);
  fireEvent.change(screen.getByLabelText("Organization admin API key"), {
    target: { value: "key" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save API credentials" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Unable to save");
  expect(configured).not.toHaveBeenCalled();
});
it("labels manual evidence", () => {
  expect(deriveSourceHealth({ source_kind: "manual_subscription" }).label).toBe(
    "Manual entry"
  );
});
