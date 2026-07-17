import React from "react";
import { Link, useLocation } from "react-router-dom";
import routes from "routes";
import { useAuth0 } from "@auth0/auth0-react";

interface NavbarProps {
  onOpenSidenav: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ onOpenSidenav }) => {
  const { logout } = useAuth0();
  const location = useLocation();

  const activeRoute = (routePath: string) => {
    return location.pathname.includes(routePath);
  };

  const handleLogout = () => {
    logout({
      logoutParams: {
        returnTo: `${window.location.origin}/`,
      }
    });
  };

  return (
    <nav className="sticky top-4 z-40 flex mb-5 flex-row flex-wrap items-center justify-between rounded-xl bg-white/10 p-2 backdrop-blur-xl dark:bg-[#0b14374d]">
      <div className="ml-[6px]">
      </div>

      <div className="relative mt-[3px] flex h-[61px] flex-grow items-center justify-around gap-2 rounded-full bg-white px-2 py-2 shadow-xl shadow-shadow-500 dark:!bg-navy-800 dark:shadow-none md:flex-grow-0 md:gap-1">
        {routes.map((route, index) => {
          if (route.layout === "/admin" && !route.hidden) {
            return (
              <Link
                key={index}
                to={route.layout + "/" + route.path}
                className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                  activeRoute(route.path)
                    ? "bg-brand-500 text-white"
                    : "text-navy-700 dark:text-white hover:bg-gray-100 dark:hover:bg-navy-700"
                }`}
              >
                <span className="mr-2">{route.icon}</span>
                <span>{route.name}</span>
              </Link>
            );
          }
          return null;
        })}
        
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-white dark:hover:text-gray-200"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          Sign Out
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
