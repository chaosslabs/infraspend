import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlanningWorkspace } from ".";
import { CallBackendService } from "utils";
const mockToken = jest.fn();
jest.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({ getAccessTokenSilently: mockToken }),
}));
jest.mock("utils", () => ({ CallBackendService: jest.fn() }));
const backend = CallBackendService as jest.Mock;
beforeEach(() => jest.clearAllMocks());
test("sample scenario is interactive without reading or writing account data", async () => {
  render(<PlanningWorkspace demo />);
  expect(screen.getByText(/Fictional costs/)).toBeInTheDocument();
  expect(screen.getAllByText("$1,325.00")).toHaveLength(2);
  fireEvent.change(screen.getByLabelText("Reduction to test (%)"), {
    target: { value: "50" },
  });
  expect(screen.getAllByText("$950.00")).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: "Save sample revision" }));
  expect(await screen.findByText(/Sample revision saved/)).toBeInTheDocument();
  expect(backend).not.toHaveBeenCalled();
});
test("saves manual plans through the API and retains edits after a conflict", async () => {
  backend.mockResolvedValueOnce({ data: [] });
  render(<PlanningWorkspace />);
  fireEvent.change(await screen.findByLabelText("Plan name"), {
    target: { value: "My AI budget" },
  });
  backend.mockRejectedValueOnce(
    new Error("This plan changed in another session.")
  );
  fireEvent.click(screen.getByRole("button", { name: "Save plan" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "changed in another session"
  );
  expect(screen.getByLabelText("Plan name")).toHaveValue("My AI budget");
  const payload = JSON.parse(backend.mock.calls[1][2].body);
  expect(payload.expected_version).toBe(0);
  backend.mockResolvedValueOnce({
    data: {
      plan_id: payload.plan_id,
      version: 1,
      payload: payload.payload,
      created_at: new Date().toISOString(),
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save plan" }));
  expect(await screen.findByText("Revision 1 saved.")).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getByLabelText("Saved plans")).toHaveValue(payload.plan_id)
  );
});
test("loading failures do not create an empty successful workspace", async () => {
  backend.mockRejectedValueOnce(new Error("Plan service unavailable"));
  render(<PlanningWorkspace />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Plan service unavailable"
  );
  expect(screen.getByRole("button", { name: "Save plan" })).toBeDisabled();
});
