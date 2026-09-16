import { useEffect } from "react";
import APIConfig from "../default/components/APIConfig";
export default function Configuration() {
  useEffect(() => {
    document.title = "Sources · InfraSpend";
  }, []);
  return (
    <div className="is-page">
      <header>
        <h1 className="is-title">Sources</h1>
        <p className="is-muted mt-2">
          Connect a billing account or add a subscription bill.
        </p>
      </header>
      <APIConfig />
    </div>
  );
}
