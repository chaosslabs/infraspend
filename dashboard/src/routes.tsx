import Planning from "views/admin/planning";
import MainDashboard from "views/admin/default";
import Configuration from "views/admin/configuration";
import SignIn from "views/auth/SignIn";
import { MdHome, MdLock, MdSettings, MdHelp, MdPreview } from "react-icons/md";
import Support from "views/admin/support";
import DemoDashboard from "views/demo/DemoDashboard";
import VendorDetails from "views/admin/vendors/components/VendorDetails";

const routes = [
  {
    name: "Overview",
    layout: "/admin",
    path: "default",
    icon: <MdHome className="h-6 w-6" />,
    component: <MainDashboard />,
  },
  {
    name: "Plan",
    layout: "/admin",
    path: "plan",
    icon: <MdPreview className="h-6 w-6" />,
    component: <Planning />,
  },
  {
    name: "Sources",
    layout: "/admin",
    path: "linked-accounts",
    icon: <MdSettings className="h-6 w-6" />,
    component: <Configuration />,
  },
  {
    name: "Sign In",
    layout: "/auth",
    path: "sign-in",
    icon: <MdLock className="h-6 w-6" />,
    component: <SignIn />,
  },
  {
    name: "Support",
    layout: "/auth",
    path: "support",
    icon: <MdHelp className="h-6 w-6" />,
    component: <Support />,
  },
  {
    name: "Demo",
    layout: "",
    path: "demo",
    icon: <MdPreview className="h-6 w-6" />,
    component: <DemoDashboard />,
  },
  {
    name: "Vendor Details",
    layout: "/admin",
    path: "vendors/:vendor",
    icon: <MdSettings className="h-6 w-6" />,
    component: <VendorDetails />,
    hidden: true,
  },
];
export default routes;
