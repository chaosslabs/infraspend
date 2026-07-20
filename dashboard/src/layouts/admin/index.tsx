import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "components/navbar";
import Sidebar from "components/sidebar";
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
  const [open, setOpen] = useState(false);

  return (
    <div className="flex h-full min-h-screen w-full bg-gray-50 dark:bg-navy-900">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      {/* Navbar & Main Content */}
      <div className="h-full w-full">
        <main className={`mx-[12px] h-full flex-none transition-all md:pr-2`}>
          <div>
            <Navbar onOpenSidenav={() => setOpen(true)} />
            <div className="pt-5s mx-auto mb-auto min-h-[84vh] p-2 md:pr-2">
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
