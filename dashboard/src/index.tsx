import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import Provider from "./auth/Provider";
import "./index.css";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <BrowserRouter>
    <Provider><App /></Provider>
  </BrowserRouter>
);
