import React from "react";
import { Link, useLocation } from "react-router-dom";
import routes from "routes";
import { useAuth0 } from "@auth0/auth0-react";
import { MdLogout, MdMenu } from "react-icons/md";
import InfraSpendLogo from "components/logo/InfraSpendLogo";

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
      },
    });
  };

  const adminRoutes = routes.filter(
    (route) => route.layout === "/admin" && !route.hidden,
  );

  return (
    <nav className="sticky top-4 z-40 mb-5 rounded-lg border border-gray-200 bg-white/90 px-3 py-3 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-navy-800/90">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onOpenSidenav}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-gray-200 text-navy-700 transition-colors hover:bg-gray-50 dark:border-white/10 dark:text-white dark:hover:bg-white/10 xl:hidden"
              aria-label="Open navigation"
            >
              <MdMenu className="h-5 w-5" aria-hidden="true" />
            </button>
            <InfraSpendLogo
              className="h-8 w-auto text-navy-700 dark:text-white xl:hidden"
              showWordmark={false}
            />
            <div>
              <p className="text-xs font-semibold uppercase text-brand-600 dark:text-teal-200">
                InfraSpend
              </p>
              <p className="text-sm font-bold text-navy-700 dark:text-white">
                FinOps workspace
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {adminRoutes.map((route) => (
            <Link
              key={route.path}
              to={route.layout + "/" + route.path}
              className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition-colors ${
                activeRoute(route.path)
                  ? "bg-brand-50 text-brand-700 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-teal-200 dark:ring-brand-400/20"
                  : "text-gray-600 hover:bg-gray-50 hover:text-navy-700 dark:text-gray-300 dark:hover:bg-white/10 dark:hover:text-white"
              }`}
            >
              <span className="text-base">{route.icon}</span>
              <span>{route.name}</span>
            </Link>
          ))}

          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-gray-600 transition-colors hover:bg-gray-50 hover:text-navy-700 dark:text-gray-300 dark:hover:bg-white/10 dark:hover:text-white"
          >
            <MdLogout className="h-5 w-5" aria-hidden="true" />
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
