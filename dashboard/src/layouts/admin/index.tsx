import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "components/navbar";
import routes from "routes";

// Helper function to generate routes
const getRoutes = (routes: any[]) => {
  return routes.map((route, key) => {
    if (route.layout === "/admin") {
      return (
        <Route
          path={`/${route.path}`}
          element={route.component}
          key={key}
        />
      );
    }
    return null;
  });
};

export default function Admin(props: { [x: string]: any }) {
  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gray-50 dark:bg-navy-900">
      {/* Navbar & Main Content */}
      <div className="h-full w-full">
        <main className="mx-auto h-full max-w-[1680px] px-3 transition-all md:px-4">
          <div>
            <Navbar />
            {process.env.REACT_APP_PREVIEW_SANDBOX === "true" && (
              <div role="status" className="my-3 rounded-lg bg-amber-100 p-3 text-sm text-amber-950">
                Preview sandbox · Sample data · Changes reset on redeployment.
                Real provider connections are disabled.
              </div>
            )}
            <div className="mx-auto mb-auto min-h-[84vh] pb-4">
              <Routes>
                {getRoutes(routes)}
                <Route path="/" element={<Navigate to="/admin/default" replace />} />
              </Routes>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
