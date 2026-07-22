const SidebarCard = () => {
  return (
    <div className="mx-5 mt-10 rounded-lg border border-brand-100 bg-brand-50 p-4 text-left dark:border-white/10 dark:bg-white/5">
      <p className="text-xs font-semibold uppercase text-brand-700 dark:text-teal-200">
        Product focus
      </p>
      <p className="mt-2 text-sm font-bold leading-5 text-navy-700 dark:text-white">
        Source freshness before cost decisions.
      </p>
      <p className="mt-2 text-xs leading-5 text-gray-700 dark:text-gray-300">
        Linked accounts, monthly metrics, forecasts, and budget planning stay
        connected.
      </p>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white dark:bg-navy-900">
        <div className="h-full w-3/4 rounded-full bg-teal-500" />
      </div>
    </div>
  );
};

export default SidebarCard;
