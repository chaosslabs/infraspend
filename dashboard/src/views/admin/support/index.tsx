import React from "react";
import { Link } from "react-router-dom";

const Support = () => {
  return (
    <div className="mt-16 mb-16 flex h-full w-full items-center justify-center px-2 md:mx-0 md:px-0 lg:mb-10 lg:items-center lg:justify-start">
      <div className="mt-[10vh] w-full max-w-full flex-col items-center md:pl-4 lg:pl-0 xl:max-w-[420px]">
        <h4 className="mb-2.5 text-4xl font-bold text-navy-700 dark:text-white">
          Support
        </h4>
        
        <div className="mt-8 space-y-6">
          <div>
            <h3 className="text-xl font-semibold text-navy-700 dark:text-white mb-2">
              GitHub Repository
            </h3>
            <p className="text-base text-gray-600 dark:text-gray-400 mb-3">
              This is an open source project. You can find the source code and contribute on GitHub:
            </p>
            <a 
              href="https://github.com/chaosslabs/infraspend"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-500 hover:text-brand-600 flex items-center gap-2"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
              chaosslabs/infraspend
            </a>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-navy-700 dark:text-white mb-2">
              Report Issues
            </h3>
            <p className="text-base text-gray-600 dark:text-gray-400 mb-3">
              Found a bug or have a feature request? Please create an issue on GitHub:
            </p>
            <a 
              href="https://github.com/chaosslabs/infraspend/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-500 hover:text-brand-600 flex items-center gap-2"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
              Issue Tracker
            </a>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-navy-700 dark:text-white mb-2">
              Company Information
            </h3>
            <p className="text-base text-gray-600 dark:text-gray-400 mb-3">
              This project is maintained by Chaoss Labs:
            </p>
            <a 
              href="https://github.com/chaosslabs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-500 hover:text-brand-600"
            >
              github.com/chaosslabs
            </a>
          </div>

          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              © {new Date().getFullYear()} Chaoss Labs. All rights reserved.
              <br />
              Licensed under the Apache License, Version 2.0.
            </p>
          </div>

          <div className="mt-4">
            <Link
              to="/auth/sign-in"
              className="text-sm font-medium text-brand-500 hover:text-brand-600 dark:text-white"
            >
              ← Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Support; 