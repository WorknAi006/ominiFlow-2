import { useState, useEffect } from "react";
import { fetchAiConfig, updateAiConfig, validateAiConfig } from "@/lib/ai/browser";

export function useAiConfigHook(useStateFn = useState, useEffectFn = useEffect) {
  const [provider, setProvider] = useStateFn<"platform" | "openai">("platform");
  const [apiKey, setApiKey] = useStateFn("");
  const [model, setModel] = useStateFn("gpt-4o");
  const [showKey, setShowKey] = useStateFn(false);
  
  const [savedProvider, setSavedProvider] = useStateFn<"platform" | "openai">("platform");
  const [savedApiKey, setSavedApiKey] = useStateFn("");
  const [savedModel, setSavedModel] = useStateFn("gpt-4o");
  
  const [isLoading, setIsLoading] = useStateFn(true);
  const [isSaving, setIsSaving] = useStateFn(false);
  const [error, setError] = useStateFn<string | null>(null);
  const [isSavedLocal, setIsSavedLocal] = useStateFn(false);
  const [isValidating, setIsValidating] = useStateFn(false);
  const [validationStatus, setValidationStatus] = useStateFn<"none" | "valid" | "invalid" | "temporary_failure" | "rate_limited">("none");
  const [validationMessage, setValidationMessage] = useStateFn<string | null>(null);

  useEffectFn(() => {
    let mounted = true;
    fetchAiConfig().then(config => {
      if (!mounted) return;
      setProvider(config.provider);
      setSavedProvider(config.provider);
      setModel(config.model);
      setSavedModel(config.model);
      const keyVal = config.has_api_key ? "••••••••••••••••" : "";
      setApiKey(keyVal);
      setSavedApiKey(keyVal);
      setValidationStatus(config.is_verified ? "valid" : "none");
      setValidationMessage(null);
      setIsLoading(false);
    }).catch(err => {
      if (!mounted) return;
      setError(err.message);
      setIsLoading(false);
    });
    return () => { mounted = false; };
  }, []);

  const hasUnsavedChanges = apiKey !== savedApiKey || model !== savedModel || provider !== savedProvider;
  
  const isFormValid = provider === "platform" || apiKey.trim().length > 0;

  const handleSave = async () => {
    if (!isFormValid || isSaving) return;
    setIsSaving(true);
    setError(null);
    setIsSavedLocal(false);
    
    try {
      const payloadKey = apiKey === "••••••••••••••••" ? undefined : apiKey;
      const config = await updateAiConfig({
        provider,
        model,
        api_key: payloadKey,
      });
      
      setSavedProvider(config.provider);
      setSavedModel(config.model);
      const keyVal = config.has_api_key ? "••••••••••••••••" : "";
      setApiKey(keyVal);
      setSavedApiKey(keyVal);
      setValidationStatus(config.is_verified ? "valid" : "none");
      setValidationMessage(null);
      setIsSavedLocal(true);
      
      setTimeout(() => setIsSavedLocal(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setProvider(savedProvider);
    setApiKey(savedApiKey);
    setModel(savedModel);
    setError(null);
    setIsSavedLocal(false);
  };

  const handleValidate = async () => {
    if (provider !== "openai" || isSaving || isValidating) return;
    setIsValidating(true);
    setValidationMessage(null);
    try {
      const result = await validateAiConfig();
      setValidationStatus(result.status);
      setValidationMessage(result.message);
    } catch (err: any) {
      setValidationStatus("temporary_failure");
      setValidationMessage(err.message);
    } finally {
      setIsValidating(false);
    }
  };

  return {
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
  };
}
