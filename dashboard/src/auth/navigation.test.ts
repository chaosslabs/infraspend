import { safeReturnTo } from "./navigation";

test("preserves private deep links including query and fragment", () => {
  expect(safeReturnTo("/admin/vendors?month=2026-09#budget")).toBe("/admin/vendors?month=2026-09#budget");
});

test.each([undefined, "https://example.com/admin/default", "//example.com/admin/default", "/auth/sign-in", "/demo", "/admin/../auth/sign-in"])("rejects unsafe or non-workspace destination %s", (value) => {
  expect(safeReturnTo(value)).toBe("/admin/default");
});
