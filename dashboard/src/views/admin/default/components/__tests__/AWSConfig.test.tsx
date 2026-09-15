import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";
import AWSConfig from "../AWSConfig";

jest.mock("@auth0/auth0-react");
jest.mock("utils", () => ({
  CallBackendService: jest.fn(),
}));

const backend = CallBackendService as jest.Mock;
const getAccessTokenSilently = jest.fn();

beforeEach(() => {
  backend.mockReset();
  (useAuth0 as jest.Mock).mockReturnValue({ getAccessTokenSilently });
});

it("generates and displays tenant-scoped AWS policies", async () => {
  backend.mockResolvedValue({
    trust_policy: {
      Statement: [{ Condition: { StringEquals: { tenant: "one" } } }],
    },
    permissions_policy: { Statement: [{ Action: "ce:GetCostAndUsage" }] },
  });
  render(<AWSConfig />);

  fireEvent.click(
    screen.getByRole("button", { name: "Generate AWS role policies" })
  );

  expect(await screen.findByText(/ce:GetCostAndUsage/)).toBeInTheDocument();
  expect(screen.getByText(/"tenant": "one"/)).toBeInTheDocument();
  expect(backend).toHaveBeenCalledWith(
    "/v1/configuration/aws/setup",
    getAccessTokenSilently,
    { method: "POST" }
  );
});

it("submits the role ARN without long-lived credentials", async () => {
  backend.mockResolvedValue({});
  const configured = jest.fn();
  render(
    <AWSConfig
      existingConfig
      initialIdentifier="Billing"
      lockIdentifier
      onConfigured={configured}
    />
  );

  fireEvent.change(screen.getByLabelText("AWS Role ARN"), {
    target: { value: "arn:aws:iam::123456789012:role/InfraspendCosts" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Update AWS" }));

  await waitFor(() => expect(configured).toHaveBeenCalled());
  expect(JSON.parse(backend.mock.calls[0][2].body)).toEqual({
    role_arn: "arn:aws:iam::123456789012:role/InfraspendCosts",
    identifier: "Billing",
  });
  expect(
    screen.getByText("AWS role updated successfully!")
  ).toBeInTheDocument();
  expect(screen.getByLabelText("AWS Role ARN")).toHaveValue("");
  expect(screen.getByLabelText("Configuration Name")).toHaveAttribute(
    "readonly"
  );
});

it("reports policy generation and role validation failures", async () => {
  backend.mockRejectedValueOnce(new Error("setup failed"));
  render(<AWSConfig />);
  fireEvent.click(
    screen.getByRole("button", { name: "Generate AWS role policies" })
  );
  expect(await screen.findByText("setup failed")).toBeInTheDocument();

  backend.mockRejectedValueOnce(new Error("role denied"));
  fireEvent.change(screen.getByLabelText("AWS Role ARN"), {
    target: { value: "arn:aws:iam::123456789012:role/Denied" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Configure AWS" }));
  expect(await screen.findByText("role denied")).toBeInTheDocument();
});
