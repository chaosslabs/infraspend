import Card from "components/card";
import React, { useState } from "react";
import { useAPIConfigurations } from "./hooks/useAPIConfigurations";
import Modal from "components/modal";
import DatadogConfig from "./DatadogConfig";
import AWSConfig from "./AWSConfig";
import HerokuConfig from "./HerokuConfig";

interface VendorConfig {
  id: string;
  name: string;
  type: string;
  component: React.ComponentType<any>;
}

const VENDOR_CONFIGS: VendorConfig[] = [
  {
    id: "datadog",
    name: "Datadog",
    type: "datadog",
    component: DatadogConfig,
  },
  {
    id: "aws",
    name: "AWS",
    type: "aws",
    component: AWSConfig,
  },
  {
    id: "heroku",
    name: "Heroku",
    type: "heroku",
    component: HerokuConfig,
  },
];

const APIConfig = () => {
  const { configurations, loading, error, refresh } = useAPIConfigurations();
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState<VendorConfig | null>(null);

  const handleConfigureVendor = (vendor: VendorConfig) => {
    setSelectedVendor(vendor);
    setShowConfigModal(true);
  };

  const handleCloseModal = () => {
    setShowConfigModal(false);
    setSelectedVendor(null);
  };

  const getVendorByType = (type: string) => {
    return VENDOR_CONFIGS.find(vendor => vendor.type === type);
  };

  return (
    <>
      <Card extra="pb-6 p-[20px]">
        <div className="flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-navy-700 dark:text-white">
              Linked Accounts
            </h2>
            <div className="relative">
              <button
                onClick={() => setShowConfigModal(true)}
                className="rounded bg-brand-500 px-4 py-2 text-sm text-white hover:bg-brand-600"
              >
                Add Account
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-4 text-gray-500">
              Loading linked accounts...
            </div>
          ) : error ? (
            <div className="text-center py-4 text-red-500">
              {error}
            </div>
          ) : configurations.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No linked accounts found</p>
              <button
                onClick={() => setShowConfigModal(true)}
                className="rounded bg-brand-500 px-4 py-2 text-sm text-white hover:bg-brand-600"
              >
                Add Your First Linked Account
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="p-2 text-left">Vendor</th>
                    <th className="p-2 text-left">Identifier</th>
                    <th className="p-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {configurations.map((config) => {
                    const vendor = getVendorByType(config.type);
                    if (!vendor) return null;
                    
                    return (
                      <tr key={`${config.type}-${config.id}`} className="border-b border-gray-200">
                        <td className="p-2 capitalize">{vendor.name}</td>
                        <td className="p-2">{config.identifier}</td>
                        <td className="p-2 text-right">
                          <button
                            onClick={() => handleConfigureVendor(vendor)}
                            className="rounded bg-brand-500 px-3 py-1 text-sm text-white hover:bg-brand-600"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      {showConfigModal && (
        <Modal
          isOpen={showConfigModal}
          onClose={handleCloseModal}
          title={selectedVendor ? 
            `${configurations.some(c => c.type === selectedVendor.type) ? "Update" : "Add"} ${selectedVendor.name} Account` :
            "Add New Account"
          }
        >
          {selectedVendor ? (
            React.createElement(selectedVendor.component, {
              onConfigured: () => {
                refresh();
                handleCloseModal();
              },
              existingConfig: configurations.some(c => c.type === selectedVendor.type),
            })
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {VENDOR_CONFIGS.map((vendor) => (
                <button
                  key={vendor.id}
                  onClick={() => setSelectedVendor(vendor)}
                  className="p-4 border rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors dark:border-white/10"
                >
                  <h3 className="font-bold mb-2 text-navy-700 dark:text-white">{vendor.name}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Configure {vendor.name} integration
                  </p>
                </button>
              ))}
            </div>
          )}
        </Modal>
      )}
    </>
  );
};

export default APIConfig;
