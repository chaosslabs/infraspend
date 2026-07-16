import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { MdDashboard, MdBarChart, MdAttachMoney } from "react-icons/md";
import { SiDatadog, SiAmazonaws } from "react-icons/si";
import logoWhite from "assets/img/layout/logoWhite.png";
import { trackPageView, trackEvent } from "../../utils/gtm";

export default function SignIn() {
  const { loginWithRedirect } = useAuth0();

  useEffect(() => {
    trackPageView('/', 'Sign In');
  }, []);

  const handleSignIn = () => {
    trackEvent('auth', 'sign_in_click');
    loginWithRedirect();
  };

  const handleDemoClick = () => {
    trackEvent('demo', 'demo_dashboard_click');
  };

  return (
    <>
      <a
        href="https://github.com/chaosslabs/infraspend"
        className="github-corner"
        aria-label="View source on GitHub"
        target="_blank"
        rel="noopener noreferrer"
        onClick={() => trackEvent('external', 'github_click')}
      >
        <svg
          width="80"
          height="80"
          viewBox="0 0 250 250"
          style={{
            fill: '#151513',
            color: '#fff',
            position: 'absolute',
            top: 0,
            border: 0,
            right: 0,
          }}
          aria-hidden="true"
        >
          <path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z" />
          <path
            d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2"
            fill="currentColor"
            style={{ transformOrigin: '130px 106px' }}
            className="octo-arm"
          />
          <path
            d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z"
            fill="currentColor"
            className="octo-body"
          />
        </svg>
      </a>
      <style>
        {`
          .github-corner:hover .octo-arm {
            animation: octocat-wave 560ms ease-in-out;
          }
          @keyframes octocat-wave {
            0%, 100% { transform: rotate(0) }
            20%, 60% { transform: rotate(-25deg) }
            40%, 80% { transform: rotate(10deg) }
          }
          @media (max-width: 500px) {
            .github-corner:hover .octo-arm {
              animation: none;
            }
            .github-corner .octo-arm {
              animation: octocat-wave 560ms ease-in-out;
            }
          }
        `}
      </style>
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-8">
        {/* Header */}
        <div className="mt-16 text-center">
          <img src={logoWhite} alt="InfraSpend Logo" className="mx-auto mb-6 h-44" />
          <h1 className="mb-2 text-4xl font-bold text-navy-700 dark:text-white">
            InfraSpend - Open Source FinOps Dashboard
          </h1>
          <p className="mb-8 text-xl text-gray-600 dark:text-gray-400">
            Explore, analyze and optimize your cloud spending
          </p>
        </div>

        {/* Features Grid */}
        <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-3">
          <FeatureCard 
            icon={<MdDashboard className="h-6 w-6"/>}
            title="Budget Tracking"
            description="Monitor your cloud spending across multiple vendors"
          />
          <FeatureCard 
            icon={<MdAttachMoney className="h-6 w-6"/>}
            title="Cost Forecasting"
            description="Predict future cloud costs using common forecasting techniques"
          />
          <FeatureCard 
            icon={<MdBarChart className="h-6 w-6"/>}
            title="AI-Powered Insights"
            description="We use AI to provide accurate forecasts and optimization suggestions"
            soon
          />
        </div>

        {/* Supported Integrations */}
        <div className="mb-8 text-center">
          <h2 className="mb-4 text-2xl font-bold text-navy-700 dark:text-white">
            Supported Integrations
          </h2>
          <div className="flex justify-center gap-8">
            <div className="flex items-center gap-2">
              <SiDatadog className="h-8 w-8 text-brand-500" />
              <div className="text-left">
                <p className="font-medium text-navy-700 dark:text-white">Datadog</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Fully Supported</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <SiAmazonaws className="h-8 w-8 text-brand-400" />
              <div className="text-left">
                <p className="font-medium text-navy-700 dark:text-white">AWS</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Fully Supported</p>
              </div>
            </div>
          </div>
        </div>

        {/* Sign In Button and Support Link */}
        <div className="mx-auto w-full max-w-[400px] text-center">
          <div className="flex gap-4">
            <button
              onClick={handleSignIn}
              className="linear flex-1 rounded-xl bg-brand-500 py-3 text-base font-medium text-white transition duration-200 hover:bg-brand-600 active:bg-brand-700 dark:bg-brand-400 dark:text-white dark:hover:bg-brand-300 dark:active:bg-brand-200"
            >
              Sign In to Get Started
            </button>
            <Link
              to="/demo"
              onClick={handleDemoClick}
              className="linear flex-1 rounded-xl bg-indigo-100 py-3 text-base font-medium text-indigo-700 transition duration-200 hover:bg-indigo-200 active:bg-indigo-300 dark:bg-navy-700 dark:text-indigo-400 dark:hover:bg-navy-600"
            >
              Try Demo Dashboard
            </Link>
          </div>
          <div className="mt-4 flex flex-col items-center justify-center gap-2">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Free and open source. Start optimizing your cloud costs today.
            </p>
            <Link
              to="/auth/support"
              className="text-sm font-medium text-brand-500 hover:text-brand-600 dark:text-white"
            >
              Find more about us →
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}

const FeatureCard = ({ 
  icon, 
  title, 
  description, 
  soon 
}: { 
  icon: React.ReactNode; 
  title: string; 
  description: string;
  soon?: boolean;
}) => (
  <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-navy-800">
    <div className="mb-4 flex items-center gap-2">
      <div className="inline-flex rounded-lg bg-brand-500 p-3 text-white dark:bg-brand-400">
        {icon}
      </div>
      {soon && (
        <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-500">
          SOON
        </span>
      )}
    </div>
    <h3 className="mb-2 text-xl font-bold text-navy-700 dark:text-white">
      {title}
    </h3>
    <p className="text-base text-gray-600 dark:text-gray-400">
      {description}
    </p>
  </div>
);
