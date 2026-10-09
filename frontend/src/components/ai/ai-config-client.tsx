"use client";

import Link from "next/link";
import { useState } from "react";

const ChevronLeftIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="15 18 9 12 15 6" /></svg>);
const KeyIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" /></svg>);
const BuildingIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="4" y="2" width="16" height="20" rx="2" ry="2" /><path d="M9 22v-4h6v4" /><path d="M8 6h.01" /><path d="M16 6h.01" /><path d="M12 6h.01" /><path d="M12 10h.01" /><path d="M12 14h.01" /><path d="M16 10h.01" /><path d="M16 14h.01" /><path d="M8 10h.01" /><path d="M8 14h.01" /></svg>);
const WrenchIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></svg>);
const CoinsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="8" cy="8" r="7" /><circle cx="16" cy="16" r="7" /></svg>);
const ArrowRightIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>);
const EyeIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>);
const EyeOffIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" /><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" /><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" /><line x1="2" x2="22" y1="2" y2="22" /></svg>);
const InfoIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg>);

import { useAiConfigHook } from "./use-ai-config";

export function AiConfigClient() {
  const [activeTab, setActiveTab] = useState("API Providers");
  
  const {
    provider, setProvider,
    apiKey, setApiKey,
    model, setModel,
    showKey, setShowKey,
    isLoading,
    isSaving,
    error,
    isSavedLocal,
    hasUnsavedChanges,
    isFormValid,
    handleSave,
    handleCancel,
    isValidating,
    validationStatus,
    validationMessage,
    handleValidate
  } = useAiConfigHook();

  if (isLoading) {
    return <div className="p-12 text-center text-slate-500 font-medium">Loading AI configuration...</div>;
  }

  return (
    <div className="bg-[#f8f9fa] min-h-screen text-slate-800 font-sans">
      
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="px-6 py-4 flex items-center gap-4 mx-auto max-w-7xl">
          <Link href="/dashboard" className="flex items-center gap-1 text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors">
            <ChevronLeftIcon className="w-4 h-4" /> Back
          </Link>
          <div className="h-6 w-px bg-slate-200" />
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none mb-1">INTEGRATIONS</div>
            <h1 className="text-[20px] font-bold text-slate-900 leading-none flex items-center gap-2">
              <span className="text-blue-600">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12a10 10 0 0 1 20 0" /><path d="M12 2v20" /><path d="M2 12h20" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
              </span>
              AI Configuration
            </h1>
          </div>
        </div>
      </div>

      <div className="p-6 mx-auto max-w-7xl">
        
        {/* Tabs */}
        <div className="flex gap-2 mb-8 border-b border-slate-200 pb-px">
          {["API Providers", "Business Profile", "Agent Tools"].map(tab => (
            <button 
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === tab 
                  ? "border-blue-600 text-blue-600 bg-blue-50/50 rounded-t-lg" 
                  : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-t-lg"
              }`}
            >
              {tab === "API Providers" && <KeyIcon className="w-4 h-4" />}
              {tab === "Business Profile" && <BuildingIcon className="w-4 h-4" />}
              {tab === "Agent Tools" && <WrenchIcon className="w-4 h-4" />}
              {tab}
            </button>
          ))}
        </div>

        {/* Content Area */}
        {activeTab === "API Providers" && (
          <div className="max-w-4xl mx-auto">
            {/* Provider Selection */}
            <div className="grid grid-cols-2 gap-4 mb-8">
              <button 
                onClick={() => setProvider("platform")}
                className={`p-6 border rounded-xl text-left transition-colors ${provider === "platform" ? "border-blue-600 ring-1 ring-blue-600 bg-blue-50/10" : "border-slate-200 bg-white hover:border-slate-300"}`}
                data-testid="select-platform-provider"
              >
                <div className="font-bold text-slate-900 mb-1">Platform-Managed</div>
                <div className="text-sm text-slate-500">Use built-in AI credits and infrastructure</div>
              </button>
              <button 
                onClick={() => setProvider("openai")}
                className={`p-6 border rounded-xl text-left transition-colors ${provider === "openai" ? "border-blue-600 ring-1 ring-blue-600 bg-blue-50/10" : "border-slate-200 bg-white hover:border-slate-300"}`}
                data-testid="select-openai-provider"
              >
                <div className="font-bold text-slate-900 mb-1">OpenAI</div>
                <div className="text-sm text-slate-500">Bring your own API key for full control</div>
              </button>
            </div>

            {/* Platform-Managed Configuration */}
            {provider === "platform" && (
              <div className="bg-white border border-slate-200 rounded-2xl p-12 shadow-sm flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-6">
                  <CoinsIcon className="w-8 h-8" />
                </div>
                <h2 className="text-xl font-bold text-slate-900 mb-3">Platform AI Credit System</h2>
                <p className="text-[15px] text-slate-500 mb-8 max-w-lg leading-relaxed">
                  You are using the platform-managed AI provider. Your conversations are powered by our infrastructure with automatic fallback protection.
                </p>
                <div className="bg-slate-50 border border-slate-100 rounded-xl p-5 mb-8 w-full max-w-md flex justify-between items-center">
                  <span className="text-slate-600 font-semibold">Current Balance</span>
                  <span className="text-lg font-black text-slate-900">461.12 credits</span>
                </div>
                <Link href="/ai-credits" className="px-6 py-3 bg-white border border-slate-200 rounded-xl font-bold text-slate-700 hover:bg-slate-50 shadow-sm flex items-center gap-2">
                  Purchase Credits <ArrowRightIcon className="w-4 h-4" />
                </Link>
              </div>
            )}

            {/* OpenAI Configuration */}
            {provider === "openai" && (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
                <h2 className="text-xl font-bold text-slate-900 mb-2">OpenAI Configuration</h2>
                <p className="text-sm text-slate-500 mb-6">
                  Connect your OpenAI account. Keys are not verified or saved to a server yet.
                </p>
                
                <div className="bg-slate-50 border border-slate-200 text-slate-800 rounded-lg p-4 text-sm flex gap-3 mb-8">
                  <InfoIcon className="w-5 h-5 shrink-0 text-slate-400" />
                  <div>
                    <p className="font-bold mb-1">Security Notice</p>
                    <p>API keys are encrypted at rest using industry standard AES-128-CBC + HMAC-SHA256. They are never returned in plaintext to the browser.</p>
                  </div>
                </div>

                <div className="space-y-6 max-w-2xl">
                  <div>
                    <label className="block text-sm font-semibold text-slate-900 mb-2">API Key</label>
                    <div className="relative">
                      <input 
                        type={showKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => {
                          setApiKey(e.target.value);
                        }}
                        placeholder="sk-..."
                        className="w-full pl-4 pr-12 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                        data-testid="api-key-input"
                      />
                      <button 
                        type="button"
                        onClick={() => setShowKey(!showKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        data-testid="toggle-key-visibility"
                      >
                        {showKey ? <EyeOffIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-slate-900 mb-2">Primary Model (UI Only)</label>
                    <select 
                      value={model}
                      onChange={(e) => {
                        setModel(e.target.value);
                      }}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white"
                      data-testid="model-select"
                    >
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4-turbo">GPT-4 Turbo</option>
                      <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    </select>
                  </div>
                  
                  {error && (
                    <div className="text-red-600 text-sm font-semibold bg-red-50 p-3 rounded-lg border border-red-200">
                      {error}
                    </div>
                  )}

                  {validationMessage && (
                    <div className={`text-sm font-semibold p-3 rounded-lg border ${
                      validationStatus === "valid" ? "text-emerald-700 bg-emerald-50 border-emerald-200" :
                      validationStatus === "invalid" ? "text-red-700 bg-red-50 border-red-200" :
                      validationStatus === "rate_limited" || validationStatus === "temporary_failure" ? "text-amber-700 bg-amber-50 border-amber-200" :
                      "text-slate-700 bg-slate-50 border-slate-200"
                    }`}>
                      {validationMessage}
                    </div>
                  )}

                  {/* Status and Action Buttons */}
                  <div className="flex items-center gap-4 pt-4 border-t border-slate-100 flex-wrap">
                    <button
                      onClick={handleSave}
                      disabled={!isFormValid || !hasUnsavedChanges || isSaving}
                      className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-bold text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      data-testid="save-config"
                    >
                      {isSaving ? "Saving..." : "Save Configuration"}
                    </button>
                    <button
                      onClick={handleCancel}
                      disabled={!hasUnsavedChanges || isSaving}
                      className="px-6 py-2.5 bg-white border border-slate-300 text-slate-700 rounded-lg font-bold text-sm hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      data-testid="cancel-config"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleValidate}
                      disabled={hasUnsavedChanges || isSaving || isValidating || !apiKey}
                      className="px-6 py-2.5 bg-slate-100 border border-slate-300 text-slate-700 rounded-lg font-bold text-sm hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      data-testid="validate-config"
                      title={hasUnsavedChanges ? "Save configuration first to validate" : ""}
                    >
                      {isValidating ? "Validating..." : "Verify Credentials"}
                    </button>
                    
                    <div className="ml-auto text-sm flex items-center gap-4">
                      {/* Validation Status Indicator */}
                      {!hasUnsavedChanges && validationStatus === "valid" && (
                        <span className="text-emerald-600 font-semibold flex items-center gap-1" data-testid="status-valid">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                          Verified
                        </span>
                      )}
                      {!hasUnsavedChanges && validationStatus === "invalid" && (
                        <span className="text-red-600 font-semibold flex items-center gap-1" data-testid="status-invalid">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                          Not Verified
                        </span>
                      )}
                      {!hasUnsavedChanges && (validationStatus === "rate_limited" || validationStatus === "temporary_failure") && (
                        <span className="text-amber-600 font-semibold flex items-center gap-1" data-testid="status-temporary-failure">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                          Validation Incomplete
                        </span>
                      )}
                      {!hasUnsavedChanges && validationStatus === "none" && apiKey && (
                        <span className="text-slate-500 font-semibold flex items-center gap-1" data-testid="status-unverified">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                          Not Validated
                        </span>
                      )}

                      {isSavedLocal && !hasUnsavedChanges ? (
                        <span className="text-emerald-600 font-semibold flex items-center gap-1" data-testid="status-saved">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
                          Configuration saved
                        </span>
                      ) : hasUnsavedChanges ? (
                        <span className="text-amber-600 font-semibold" data-testid="status-unsaved">Unsaved changes</span>
                      ) : null}
                    </div>
                  </div>

                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
