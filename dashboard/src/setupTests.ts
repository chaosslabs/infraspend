// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toBeInTheDocument()
import "@testing-library/jest-dom";
// jsdom does not expose Web Crypto; use Node's UUID implementation in tests.
import { randomUUID } from "crypto";
Object.defineProperty(global, "crypto", {
  value: { randomUUID },
  configurable: true,
});
