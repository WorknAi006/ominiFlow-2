"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createTemplate, submitTemplate, type AiTemplateDraft } from "@/lib/templates/browser";
import { listChannels, type ChannelConnection } from "@/lib/channels/browser";
import { AiTemplateModal, AI_TEMPLATE_DRAFT_KEY } from "@/components/templates/ai-template-modal";

const CATEGORY_MAP: Record<string, string> = { Marketing: "MARKETING", Utility: "UTILITY", Authentication: "AUTHENTICATION" };
const LANGUAGE_MAP: Record<string, string> = { English: "en_US", Spanish: "es", Hindi: "hi" };
const CATEGORY_LABEL: Record<string, string> = { MARKETING: "Marketing", UTILITY: "Utility", AUTHENTICATION: "Authentication" };
const LANGUAGE_LABEL: Record<string, string> = { en_US: "English", es: "Spanish", hi: "Hindi" };
const HEADER_LABEL: Record<string, string> = { none: "None", text: "Text", image: "Image", video: "Video", document: "Document" };

const ChevronLeftIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="15 18 9 12 15 6" /></svg>);
const SparklesIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M9 3v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zm7 5v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zM4 15v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2zm16-4v1m0 4v1m0-1a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2z" /></svg>);
const SaveIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></svg>);
const LockIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>);
const LayoutIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>);
const TimerIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>);
const ShieldCheckIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>);

interface CarouselCardItem {
  id: number;
  body: string;
  mediaName?: string;
  buttons: string[];
}

export function TemplateEditor() {
  const router = useRouter();
  const [templateType, setTemplateType] = useState<"Standard" | "Carousel" | "Offer" | "OTP">("Standard");
  const [category, setCategory] = useState("Marketing");
  const [language, setLanguage] = useState("English");
  const [name, setName] = useState("");
  const [headerType, setHeaderType] = useState("None");
  const [headerText, setHeaderText] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [footerText, setFooterText] = useState("");
  const [buttons, setButtons] = useState<string[]>([]);
  const [headerFile, setHeaderFile] = useState<File | null>(null);
  const [headerPreviewUrl, setHeaderPreviewUrl] = useState<string | null>(null);
  const [bodyExamples, setBodyExamples] = useState<Record<string, string>>({});
  const [currentTime, setCurrentTime] = useState("11:27 AM");

  // Keep live time for phone mockup
  useEffect(() => {
    const updateTime = () => {
      const d = new Date();
      setCurrentTime(d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }));
    };
    updateTime();
  }, []);

  // Generate preview object URL when header media file is selected
  useEffect(() => {
    if (headerFile) {
      const url = URL.createObjectURL(headerFile);
      setHeaderPreviewUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setHeaderPreviewUrl(null);
    }
  }, [headerFile]);

  // Carousel specific state
  const [carouselMediaType, setCarouselMediaType] = useState<"Image" | "Video">("Image");
  const [carouselIncludeBody, setCarouselIncludeBody] = useState(true);
  const [carouselButtonLabel, setCarouselButtonLabel] = useState("Buy now");
  const [carouselCards, setCarouselCards] = useState<CarouselCardItem[]>([
    { id: 1, body: "Exclusive product collection", buttons: ["Buy now"] },
    { id: 2, body: "Limited edition stock", buttons: ["Buy now"] },
  ]);

  // OTP specific state
  const [otpDelivery, setOtpDelivery] = useState<"copy" | "one_tap" | "zero_tap">("copy");
  const [otpButtonText, setOtpButtonText] = useState("Copy code");
  const [otpExpiration, setOtpExpiration] = useState(5);
  const [otpAutofillText, setOtpAutofillText] = useState("Autofill");
  const [otpPackageName, setOtpPackageName] = useState("com.example.app");
  const [otpAppSignatureHash, setOtpAppSignatureHash] = useState("");
  const [otpSecurityRecommendation, setOtpSecurityRecommendation] = useState(true);

  // Limited Time Offer specific state
  const [offerCouponCode, setOfferCouponCode] = useState("SUMMER20");
  const [offerExpirationText, setOfferExpirationText] = useState("Expires in 24 hours");

  const [channels, setChannels] = useState<ChannelConnection[]>([]);
  const [channelId, setChannelId] = useState("");
  const [saving, setSaving] = useState(false);
  const [submittingMeta, setSubmittingMeta] = useState(false);
  const [error, setError] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function applyDraft(d: AiTemplateDraft) {
    setName(d.name);
    setCategory(CATEGORY_LABEL[d.category] ?? "Marketing");
    setLanguage(LANGUAGE_LABEL[d.language] ?? "English");
    setHeaderType(HEADER_LABEL[d.header_type] ?? "None");
    setHeaderText(d.header_text ?? "");
    setBodyText(d.body_text);
    setFooterText(d.footer_text ?? "");
    setButtons(d.buttons ?? []);
  }

  useEffect(() => {
    listChannels({ page: 1, page_size: 100, channel_type: "whatsapp" })
      .then((r) => {
        setChannels(r.items);
        if (r.items.length > 0) {
          setChannelId((prev) => prev || r.items[0].id);
        }
      })
      .catch(() => setChannels([]));
  }, []);

  // Sync category with OTP type
  useEffect(() => {
    if (templateType === "OTP") {
      setCategory("Authentication");
    } else if (category === "Authentication") {
      setCategory("Marketing");
    }
  }, [templateType]);

  // Pre-fill from AI draft if present
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const raw = await Promise.resolve(sessionStorage.getItem(AI_TEMPLATE_DRAFT_KEY));
        if (raw && active) {
          applyDraft(JSON.parse(raw) as AiTemplateDraft);
          sessionStorage.removeItem(AI_TEMPLATE_DRAFT_KEY);
        }
      } catch {
        // ignore
      }
    })();
    return () => { active = false; };
  }, []);

  // Compute detected body variables {{1}}, {{2}}
  const bodyVariables = [...new Set(Array.from(bodyText.matchAll(/\{\{\s*(\d+)\s*\}\}/g), (match) => `{{${match[1]}}}`))];

  // Helper to add variable to body
  const addVariableToBody = () => {
    const existingNums = Array.from(bodyText.matchAll(/\{\{\s*(\d+)\s*\}\}/g), (m) => parseInt(m[1], 10));
    const nextNum = existingNums.length > 0 ? Math.max(...existingNums) + 1 : 1;
    const token = `{{${nextNum}}}`;
    
    const textarea = textareaRef.current;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const nextText = bodyText.substring(0, start) + token + bodyText.substring(end);
      setBodyText(nextText);
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + token.length, start + token.length);
      }, 0);
    } else {
      setBodyText((prev) => `${prev} ${token}`);
    }
    
    setBodyExamples((prev) => ({
      ...prev,
      [token]: prev[token] || `Sample ${nextNum}`,
    }));
  };

  // Rich text formatting wrap
  const wrapFormat = (wrapper: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = bodyText.substring(start, end);
    if (selected) {
      const replaced = `${wrapper}${selected}${wrapper}`;
      setBodyText(bodyText.substring(0, start) + replaced + bodyText.substring(end));
    } else {
      setBodyText(bodyText + wrapper + wrapper);
    }
    textarea.focus();
  };

  const insertEmoji = (emoji: string) => {
    setBodyText((prev) => `${prev} ${emoji}`);
  };

  async function save() {
    setError("");
    if (!channelId) return setError("Select a WhatsApp channel.");
    if (!/^[a-z0-9_]{1,512}$/.test(name)) return setError("Name must be lowercase letters, numbers and underscores only.");
    if (!bodyText.trim() && templateType !== "OTP") return setError("Body is required.");
    setSaving(true);
    try {
      const payloadBody = templateType === "OTP" 
        ? "{{1}} is your verification code. For your security, do not share this code."
        : bodyText;

      const payloadButtons = templateType === "OTP"
        ? [otpButtonText || "Copy code"]
        : templateType === "Carousel"
          ? [carouselButtonLabel || "Buy now"]
          : buttons.filter(Boolean);

      await createTemplate({
        channel_connection_id: channelId,
        name,
        language: LANGUAGE_MAP[language] ?? "en_US",
        category: CATEGORY_MAP[category] ?? null,
        header_format: headerType.toUpperCase() as "NONE" | "TEXT" | "IMAGE" | "VIDEO" | "DOCUMENT",
        header_text: headerType === "Text" ? (headerText.trim().slice(0, 60) || null) : null,
        body_text: payloadBody,
        footer_text: footerText.trim() || null,
        buttons: payloadButtons,
      });
      router.push("/templates");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the template.");
      setSaving(false);
    }
  }

  async function submitToMeta() {
    setError("");
    if (!channelId) return setError("Select a WhatsApp channel.");
    if (!/^[a-z0-9_]{1,512}$/.test(name)) return setError("Name must be lowercase letters, numbers and underscores only.");
    if (!bodyText.trim() && templateType !== "OTP") return setError("Body is required.");
    if (templateType !== "OTP" && bodyVariables.some((variable) => !bodyExamples[variable]?.trim())) {
      return setError("Enter one sample value for every body variable before submitting to Meta.");
    }
    if (["Image", "Video", "Document"].includes(headerType) && !headerFile && templateType === "Standard") {
      return setError(`Choose a sample ${headerType.toLowerCase()} for Meta review.`);
    }

    setSubmittingMeta(true);
    try {
      const payloadBody = templateType === "OTP" 
        ? "{{1}} is your verification code. For your security, do not share this code."
        : bodyText.trim();

      const payloadButtons = templateType === "OTP"
        ? [otpButtonText || "Copy code"]
        : templateType === "Carousel"
          ? [carouselButtonLabel || "Buy now"]
          : buttons.filter(Boolean);

      const payloadExamples = templateType === "OTP"
        ? ["123456"]
        : bodyVariables.map((variable) => bodyExamples[variable]?.trim() || "sample");

      await submitTemplate({
        channel_connection_id: channelId,
        name,
        language: LANGUAGE_MAP[language] ?? "en_US",
        category: CATEGORY_MAP[category] ?? "MARKETING",
        header_format: headerType.toUpperCase() as "NONE" | "TEXT" | "IMAGE" | "VIDEO" | "DOCUMENT",
        header_text: headerType === "Text" ? headerText.trim() : null,
        body_text: payloadBody,
        footer_text: footerText.trim() || null,
        buttons: payloadButtons,
        body_examples: payloadExamples,
        ...(headerFile ? { header_file: headerFile } : {}),
      });
      router.push("/templates");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit the template to Meta.");
      setSubmittingMeta(false);
    }
  }

  // Rich formatted body renderer with variable substitution & WhatsApp markdown
  const renderFormattedBody = () => {
    if (!bodyText.trim()) {
      return <span className="text-slate-400 italic">Your message preview will appear here</span>;
    }

    let text = bodyText;
    bodyVariables.forEach((v) => {
      const sample = bodyExamples[v];
      if (sample && sample.trim()) {
        text = text.replaceAll(v, `__SAMPLE_${v}_${sample.trim()}__`);
      } else {
        text = text.replaceAll(v, `__VAR_${v}__`);
      }
    });

    const lines = text.split("\n");
    return lines.map((line, lIdx) => {
      const tokens = line.split(/(__SAMPLE_[^_]+_[^_]+__|__VAR_[^_]+__|\*[^*]+\*|_[^_]+_|~[^~]+~|`[^`]+`)/g);

      return (
        <span key={lIdx} className="block min-h-[1.25rem]">
          {tokens.map((token, tIdx) => {
            if (!token) return null;
            if (token.startsWith("__SAMPLE_") && token.endsWith("__")) {
              const inner = token.slice(9, -2);
              const idx = inner.indexOf("_");
              const val = inner.slice(idx + 1);
              return (
                <span key={tIdx} className="font-semibold text-emerald-800 bg-emerald-50 px-1 py-0.5 rounded border border-emerald-200/60" title="Variable Sample">
                  {val}
                </span>
              );
            }
            if (token.startsWith("__VAR_") && token.endsWith("__")) {
              const varName = token.slice(6, -2);
              return (
                <span key={tIdx} className="font-mono text-[11px] font-bold text-emerald-700 bg-emerald-100/80 px-1.5 py-0.5 rounded border border-emerald-300/80" title="Placeholder">
                  {varName}
                </span>
              );
            }
            if (token.startsWith("*") && token.endsWith("*") && token.length > 2) {
              return <strong key={tIdx} className="font-bold text-slate-900">{token.slice(1, -1)}</strong>;
            }
            if (token.startsWith("_") && token.endsWith("_") && token.length > 2) {
              return <em key={tIdx} className="italic text-slate-800">{token.slice(1, -1)}</em>;
            }
            if (token.startsWith("~") && token.endsWith("~") && token.length > 2) {
              return <del key={tIdx} className="line-through text-slate-500">{token.slice(1, -1)}</del>;
            }
            if (token.startsWith("`") && token.endsWith("`") && token.length > 2) {
              return <code key={tIdx} className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded font-mono text-xs">{token.slice(1, -1)}</code>;
            }
            return <span key={tIdx}>{token}</span>;
          })}
        </span>
      );
    });
  };

  // Generate rendered preview text with variable sample substitution
  const renderedBody = () => {
    let res = bodyText;
    bodyVariables.forEach((v) => {
      const sample = bodyExamples[v];
      if (sample) {
        res = res.replaceAll(v, sample);
      }
    });
    return res;
  };

  return (
    <div className="bg-[#f8f9fa] min-h-screen text-slate-800 font-sans">
      {/* Top Navigation */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-2xs">
        <div className="px-6 py-4 flex items-center justify-between mx-auto max-w-7xl">
          <div className="flex items-center gap-4">
            <Link href="/templates" className="p-2 border border-slate-200 rounded-full hover:bg-slate-50 transition-colors">
              <ChevronLeftIcon className="w-5 h-5 text-slate-500" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Create Template</h1>
              <p className="text-xs text-slate-400">Design WhatsApp message templates and submit for Meta approval</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving || submittingMeta}
              className="px-5 py-2.5 bg-white hover:bg-slate-50 disabled:opacity-60 text-slate-700 border border-slate-300 rounded-xl font-bold text-xs flex items-center gap-2 shadow-2xs transition"
            >
              <SaveIcon className="w-4 h-4" /> {saving ? "Saving Draft..." : "Save Draft"}
            </button>
            <button
              type="button"
              onClick={() => void submitToMeta()}
              disabled={saving || submittingMeta}
              className="px-6 py-2.5 bg-[#00b050] hover:bg-[#009040] disabled:opacity-60 text-white rounded-xl font-bold text-xs shadow-sm transition"
            >
              {submittingMeta ? "Submitting to Meta..." : "Submit to Meta"}
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 mx-auto max-w-7xl flex flex-col lg:flex-row gap-8">
        
        {/* Left Column (Form Sections) */}
        <div className="flex-1 space-y-6 max-w-3xl">
          
          {/* Template Type Selector Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <button 
              type="button"
              onClick={() => setTemplateType("Standard")}
              className={`p-4 text-left border rounded-2xl bg-white transition-all cursor-pointer ${
                templateType === "Standard" ? "border-[#00b050] shadow-sm ring-2 ring-[#00b050]/20" : "border-slate-200/90 hover:border-slate-300"
              }`}
            >
              <LayoutIcon className={`w-5 h-5 mb-2.5 ${templateType === "Standard" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-sm text-slate-900 mb-1">Standard</div>
              <div className="text-[11px] text-slate-500 leading-tight">Text or media header, body, footer & buttons</div>
            </button>

            <button 
              type="button"
              onClick={() => setTemplateType("Carousel")}
              className={`p-4 text-left border rounded-2xl bg-white transition-all cursor-pointer ${
                templateType === "Carousel" ? "border-[#00b050] shadow-sm ring-2 ring-[#00b050]/20" : "border-slate-200/90 hover:border-slate-300"
              }`}
            >
              <LayoutIcon className={`w-5 h-5 mb-2.5 ${templateType === "Carousel" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-sm text-slate-900 mb-1">Carousel</div>
              <div className="text-[11px] text-slate-500 leading-tight">Up to 10 swipeable media cards</div>
            </button>

            <button 
              type="button"
              onClick={() => setTemplateType("Offer")}
              className={`p-4 text-left border rounded-2xl bg-white transition-all cursor-pointer ${
                templateType === "Offer" ? "border-[#00b050] shadow-sm ring-2 ring-[#00b050]/20" : "border-slate-200/90 hover:border-slate-300"
              }`}
            >
              <TimerIcon className={`w-5 h-5 mb-2.5 ${templateType === "Offer" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-sm text-slate-900 mb-1">Limited-Time Offer</div>
              <div className="text-[11px] text-slate-500 leading-tight">Coupon code with a countdown</div>
            </button>

            <button 
              type="button"
              onClick={() => setTemplateType("OTP")}
              className={`p-4 text-left border rounded-2xl bg-white transition-all cursor-pointer ${
                templateType === "OTP" ? "border-[#00b050] shadow-sm ring-2 ring-[#00b050]/20" : "border-slate-200/90 hover:border-slate-300"
              }`}
            >
              <ShieldCheckIcon className={`w-5 h-5 mb-2.5 ${templateType === "OTP" ? "text-[#00b050]" : "text-slate-400"}`} />
              <div className="font-bold text-sm text-slate-900 mb-1">Authentication (OTP)</div>
              <div className="text-[11px] text-slate-500 leading-tight">Verification code with autofill / copy</div>
            </button>
          </div>

          {/* Section 1: Basic Info */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-base font-bold text-slate-900">Basic Info</h2>
              <button
                type="button"
                onClick={() => setAiOpen(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-purple-50 text-purple-700 rounded-xl font-bold text-xs border border-purple-100 hover:bg-purple-100 transition"
              >
                <SparklesIcon className="w-3.5 h-3.5" /> Generate with AI
              </button>
            </div>
            
            {error && (
              <div className="mb-5 rounded-xl bg-rose-50 border border-rose-200 p-3.5 text-xs font-semibold text-rose-800">
                {error}
              </div>
            )}

            <div className="mb-5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                WhatsApp Channel <span className="text-rose-500">*</span>
              </label>
              <select
                value={channelId}
                onChange={(e) => setChannelId(e.target.value)}
                className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050] shadow-2xs"
              >
                <option value="">{channels.length ? "Select a channel" : "No WhatsApp channels — connect one first"}</option>
                {channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <p className="mt-1.5 text-[11px] text-slate-400">
                Drafts are saved locally first. WhatsApp templates must be reviewed and approved by Meta before broadcasting.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-5">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Category <span className="text-rose-500">*</span>
                </label>
                <select 
                  value={category} 
                  disabled={templateType === "OTP"}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050] shadow-2xs disabled:bg-slate-50"
                >
                  <option>Marketing</option>
                  <option>Utility</option>
                  <option>Authentication</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Language</label>
                <select 
                  value={language} 
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050] shadow-2xs"
                >
                  <option>English</option>
                  <option>Spanish</option>
                  <option>Hindi</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Template Name <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input 
                  type="text" 
                  value={name} 
                  onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))}
                  placeholder="e.g. order_update_v1"
                  maxLength={512}
                  className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050] shadow-2xs"
                />
                <span className="absolute right-4 top-2.5 text-xs font-semibold text-slate-400">
                  {name.length}/512
                </span>
              </div>
              <span className="mt-1 block text-[11px] text-slate-400">
                Lowercase letters, numbers and underscores only (Meta API requirement).
              </span>
            </div>
          </div>

          {/* Section 2: Header Configuration (For Standard & Offer) */}
          {(templateType === "Standard" || templateType === "Offer") && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
              <h2 className="text-base font-bold text-slate-900 mb-4">Header</h2>
              <div className="flex flex-wrap gap-5">
                {["None", "Text", "Image", "Video", "Document"].map((opt) => (
                  <label key={opt} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="headerType"
                      value={opt}
                      checked={headerType === opt}
                      onChange={() => {
                        setHeaderType(opt);
                        if (!["Image", "Video", "Document"].includes(opt)) setHeaderFile(null);
                      }}
                      className="w-4 h-4 text-[#00b050] focus:ring-[#00b050]"
                    />
                    <span className="text-sm font-semibold text-slate-700">{opt}</span>
                  </label>
                ))}
              </div>

              {headerType === "Text" && (
                <div className="relative mt-4">
                  <input
                    value={headerText}
                    onChange={(e) => setHeaderText(e.target.value)}
                    maxLength={60}
                    placeholder="Header text (max 60)"
                    className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]"
                  />
                  <span className="absolute right-3.5 top-3 text-[10px] font-semibold text-slate-400">
                    {headerText.length}/60
                  </span>
                </div>
              )}

              {(headerType === "Image" || headerType === "Video" || headerType === "Document") && (
                <div className="mt-4">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                    Sample {headerType.toLowerCase()} for Meta review
                  </label>
                  <input
                    type="file"
                    accept={headerType === "Image" ? "image/jpeg,image/png,.jpg,.jpeg,.png" : headerType === "Video" ? "video/mp4,.mp4" : "application/pdf,.pdf"}
                    onChange={(event) => setHeaderFile(event.target.files?.[0] ?? null)}
                    className="block w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-emerald-50 file:text-[#00b050] hover:file:bg-emerald-100 cursor-pointer"
                  />
                  <p className="mt-2 text-[11px] text-slate-400">
                    {headerFile ? `${headerFile.name} · ${(headerFile.size / 1024 / 1024).toFixed(1)} MB` : "Required for Meta review. Limits: Image 5 MB, Video 16 MB, PDF 100 MB."}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Section 3: Body & Variables (Standard & Carousel) */}
          {(templateType === "Standard" || templateType === "Carousel" || templateType === "Offer") && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-base font-bold text-slate-900">Body</h2>
                <button
                  type="button"
                  onClick={addVariableToBody}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white text-[#00b050] rounded-xl font-bold text-xs border border-[#00b050] hover:bg-emerald-50 transition shadow-2xs cursor-pointer"
                >
                  + Add Variable
                </button>
              </div>
              
              <p className="text-xs text-slate-500 mb-4 leading-relaxed">
                Make your messages personal using variables like <code className="text-[#00b050] font-bold bg-[#e8f5e9] px-1 py-0.5 rounded">{`{{1}}`}</code>, <code className="text-[#00b050] font-bold bg-[#e8f5e9] px-1 py-0.5 rounded">{`{{2}}`}</code>. Variables will be automatically numbered and sent to Meta API!
              </p>

              <div className="border border-slate-200 rounded-2xl overflow-hidden focus-within:border-[#00b050] focus-within:ring-1 focus-within:ring-[#00b050] transition-all">
                {/* Rich text formatting bar */}
                <div className="flex justify-between items-center px-4 py-2.5 bg-slate-50/70 border-b border-slate-100">
                  <div className="flex items-center gap-3 text-slate-600">
                    <button type="button" onClick={() => insertEmoji("😊")} title="Add Emoji" className="hover:text-slate-900 transition">
                      😊
                    </button>
                    <button type="button" onClick={() => wrapFormat("*")} title="Bold (*)" className="font-bold hover:text-slate-900 transition text-xs">
                      B
                    </button>
                    <button type="button" onClick={() => wrapFormat("_")} title="Italic (_)" className="italic hover:text-slate-900 transition text-xs">
                      I
                    </button>
                    <button type="button" onClick={() => wrapFormat("~")} title="Strikethrough (~)" className="line-through hover:text-slate-900 transition text-xs">
                      S
                    </button>
                  </div>
                  <div className="text-xs font-semibold text-slate-400">
                    {bodyText.length}/1024
                  </div>
                </div>

                <textarea 
                  ref={textareaRef}
                  className="w-full min-h-[140px] p-4 text-sm resize-none outline-none text-slate-800 placeholder:text-slate-400 leading-relaxed font-sans"
                  placeholder="Type your message body (e.g., Hello {{1}}, your order {{2}} has been confirmed!)"
                  value={bodyText}
                  maxLength={1024}
                  onChange={(e) => setBodyText(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Section 3.1: Dedicated Body Variables Card (Matching Reference Video) */}
          {bodyVariables.length > 0 && templateType !== "OTP" && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs animate-in fade-in">
              <h2 className="text-sm font-bold text-slate-900 mb-1">Body Variables</h2>
              <p className="text-xs text-slate-500 mb-4">Provide sample values for each variable so Meta reviewers and live preview can render it.</p>
              <div className="space-y-3">
                {bodyVariables.map((variable) => (
                  <div key={variable} className="flex items-center gap-3">
                    <span className="w-14 text-xs font-bold text-[#00b050] bg-emerald-50 px-2.5 py-2 rounded-xl text-center border border-emerald-100">
                      {variable}
                    </span>
                    <input
                      value={bodyExamples[variable] ?? ""}
                      onChange={(event) => setBodyExamples((current) => ({ ...current, [variable]: event.target.value }))}
                      maxLength={1024}
                      className="flex-1 px-3.5 py-2 border border-slate-200 rounded-xl text-sm font-medium outline-none focus:border-[#00b050]"
                      placeholder={`Sample value for ${variable} (e.g. John or #1234)`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Carousel Card Structure & Items (When Carousel is chosen) */}
          {templateType === "Carousel" && (
            <div className="space-y-6">
              {/* Card Structure Settings */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
                <h2 className="text-base font-bold text-slate-900 mb-4">Card structure (applies to every card)</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                  <div>
                    <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Media Type</span>
                    <div className="flex gap-4">
                      {["Image", "Video"].map((t) => (
                        <label key={t} className="flex items-center gap-2 cursor-pointer text-xs font-bold text-slate-700">
                          <input
                            type="radio"
                            name="carouselMediaType"
                            value={t}
                            checked={carouselMediaType === t}
                            onChange={() => setCarouselMediaType(t as "Image" | "Video")}
                            className="text-[#00b050] focus:ring-[#00b050]"
                          />
                          {t}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Card Body Text</span>
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                      <input
                        type="checkbox"
                        checked={carouselIncludeBody}
                        onChange={(e) => setCarouselIncludeBody(e.target.checked)}
                        className="rounded border-slate-300 text-[#00b050] focus:ring-[#00b050]"
                      />
                      Include body text on every card
                    </label>
                  </div>
                </div>

                <div>
                  <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Button text (applies to every card)</span>
                  <input
                    value={carouselButtonLabel}
                    onChange={(e) => setCarouselButtonLabel(e.target.value)}
                    maxLength={25}
                    placeholder="e.g. Buy now"
                    className="w-full sm:w-64 px-3.5 py-2 border border-slate-200 rounded-xl text-sm font-medium outline-none focus:border-[#00b050]"
                  />
                </div>
              </div>

              {/* Cards List */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-base font-bold text-slate-900">Carousel Cards ({carouselCards.length}/10)</h2>
                  {carouselCards.length < 10 && (
                    <button
                      type="button"
                      onClick={() => setCarouselCards([...carouselCards, { id: carouselCards.length + 1, body: `Card ${carouselCards.length + 1}`, buttons: [carouselButtonLabel] }])}
                      className="px-3 py-1.5 bg-emerald-50 text-[#00b050] rounded-xl font-bold text-xs hover:bg-emerald-100 transition"
                    >
                      + Add Card
                    </button>
                  )}
                </div>

                <div className="space-y-4">
                  {carouselCards.map((card, i) => (
                    <div key={card.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                          Card {i + 1} ({carouselMediaType} · 1 button)
                        </span>
                        {carouselCards.length > 2 && (
                          <button
                            type="button"
                            onClick={() => setCarouselCards(carouselCards.filter((_, idx) => idx !== i))}
                            className="text-xs text-rose-600 hover:underline"
                          >
                            Remove
                          </button>
                        )}
                      </div>

                      {carouselIncludeBody && (
                        <input
                          value={card.body}
                          onChange={(e) => setCarouselCards(carouselCards.map((c, idx) => idx === i ? { ...c, body: e.target.value } : c))}
                          placeholder={`Card ${i + 1} description`}
                          className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Authentication (OTP) Configuration (When OTP is chosen) */}
          {templateType === "OTP" && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-5">
              <h2 className="text-base font-bold text-slate-900">Code Delivery</h2>
              <div className="space-y-3">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="otpDelivery"
                    value="copy"
                    checked={otpDelivery === "copy"}
                    onChange={() => setOtpDelivery("copy")}
                    className="mt-0.5 text-[#00b050] focus:ring-[#00b050]"
                  />
                  <div>
                    <span className="block text-sm font-bold text-slate-800">Copy code</span>
                    <span className="text-xs text-slate-400">User taps a button to copy the code to clipboard</span>
                  </div>
                </label>

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="otpDelivery"
                    value="one_tap"
                    checked={otpDelivery === "one_tap"}
                    onChange={() => setOtpDelivery("one_tap")}
                    className="mt-0.5 text-[#00b050] focus:ring-[#00b050]"
                  />
                  <div>
                    <span className="block text-sm font-bold text-slate-800">One-tap autofill</span>
                    <span className="text-xs text-slate-400">Needs your Android app details for single-tap code handover</span>
                  </div>
                </label>

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="otpDelivery"
                    value="zero_tap"
                    checked={otpDelivery === "zero_tap"}
                    onChange={() => setOtpDelivery("zero_tap")}
                    className="mt-0.5 text-[#00b050] focus:ring-[#00b050]"
                  />
                  <div>
                    <span className="block text-sm font-bold text-slate-800">Zero-tap</span>
                    <span className="text-xs text-slate-400">Auto-fills with no tap (Android app required)</span>
                  </div>
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Button Text</label>
                  <input
                    value={otpButtonText}
                    onChange={(e) => setOtpButtonText(e.target.value)}
                    maxLength={25}
                    placeholder="Copy code"
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-xl text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Code expiration (minutes, 1-90)</label>
                  <input
                    type="number"
                    min={1}
                    max={90}
                    value={otpExpiration}
                    onChange={(e) => setOtpExpiration(Number(e.target.value))}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-xl text-sm"
                  />
                </div>
              </div>

              {(otpDelivery === "one_tap" || otpDelivery === "zero_tap") && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Autofill text</label>
                    <input
                      value={otpAutofillText}
                      onChange={(e) => setOtpAutofillText(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-xl text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Android package name</label>
                    <input
                      value={otpPackageName}
                      onChange={(e) => setOtpPackageName(e.target.value)}
                      placeholder="com.example.app"
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-xl text-sm"
                    />
                  </div>
                </div>
              )}

              <label className="flex items-center gap-2.5 pt-2 cursor-pointer text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={otpSecurityRecommendation}
                  onChange={(e) => setOtpSecurityRecommendation(e.target.checked)}
                  className="rounded border-slate-300 text-[#00b050] focus:ring-[#00b050]"
                />
                <span>Add security recommendation (&ldquo;For your security, do not share this code&rdquo;)</span>
              </label>
            </div>
          )}

          {/* Section 4: Footer Section (Standard & Offer) */}
          {(templateType === "Standard" || templateType === "Offer") && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
              <h2 className="text-base font-bold text-slate-900 mb-1">
                Footer <span className="text-slate-400 font-normal text-xs">(Optional)</span>
              </h2>
              <p className="text-xs text-slate-500 mb-3">Footers are great to add any disclaimers or to add a thoughtful PS</p>
              <div className="relative">
                <textarea 
                  className="w-full min-h-[70px] p-3.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-800 outline-none focus:border-[#00b050] resize-none placeholder:text-slate-400"
                  placeholder="Add footer text (optional)"
                  maxLength={60}
                  value={footerText}
                  onChange={(e) => setFooterText(e.target.value)}
                />
                <div className="absolute bottom-3 right-3 text-[10px] font-semibold text-slate-400">
                  {footerText.length}/60
                </div>
              </div>
            </div>
          )}

          {/* Section 5: Buttons Section (Standard) */}
          {templateType === "Standard" && (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs mb-10">
              <h2 className="text-base font-bold text-slate-900 mb-1">
                Buttons <span className="text-slate-400 font-normal text-xs">(Optional)</span>
              </h2>
              <p className="text-xs text-slate-500 mb-4">Create quick-reply or call-to-action buttons for customers.</p>

              <div className="space-y-2.5 mb-3">
                {buttons.map((b, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      value={b}
                      onChange={(e) => setButtons(buttons.map((x, idx) => (idx === i ? e.target.value : x)))}
                      maxLength={25}
                      placeholder={`Button ${i + 1} text`}
                      className="flex-1 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium outline-none focus:border-[#00b050]"
                    />
                    <button
                      type="button"
                      onClick={() => setButtons(buttons.filter((_, idx) => idx !== i))}
                      className="rounded-lg p-2 text-slate-400 hover:text-rose-600 transition"
                    >
                      🗑
                    </button>
                  </div>
                ))}
              </div>

              {buttons.length < 3 && (
                <button
                  type="button"
                  onClick={() => setButtons([...buttons, ""])}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-2xs"
                >
                  + Add button
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right Column (Realistic WhatsApp Mobile Preview) */}
        <div className="w-full lg:w-[380px] lg:sticky lg:top-24 self-start">
          <div className="border-[7px] border-slate-800 rounded-[3rem] overflow-hidden bg-[#efeae2] h-[700px] flex flex-col relative shadow-2xl">
            {/* Phone Notch/Top bar */}
            <div className="bg-white text-slate-900 px-6 pt-3 pb-2.5 flex justify-between items-center text-xs font-bold border-b border-slate-100 z-10">
              <div>{currentTime}</div>
              <div className="w-24 h-5 bg-black rounded-full" />
              <div className="flex items-center gap-1">
                <span className="text-[10px]">5G</span>
                <div className="w-4 h-2.5 bg-slate-900 rounded-xs" />
              </div>
            </div>
            
            {/* WhatsApp Header Mockup */}
            <div className="bg-[#005c4b] text-white px-4 py-3 flex items-center gap-3 z-10 shadow-xs">
              <ChevronLeftIcon className="w-4 h-4 text-white/80" />
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold text-xs">
                O
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold truncate">Omniflow Official</div>
                <div className="text-[10px] text-white/70">Verified Business Account</div>
              </div>
            </div>
            
            {/* Message Bubble Area */}
            <div className="flex-1 p-3.5 flex flex-col gap-3 relative z-10 overflow-y-auto">
              {/* Meta Security Disclaimer */}
              <div className="bg-[#fcedb3] text-slate-700 text-[10px] p-2.5 rounded-xl mx-auto max-w-[94%] text-center shadow-xs flex items-center gap-2 leading-tight">
                <LockIcon className="w-3.5 h-3.5 shrink-0 text-slate-600" />
                <span>
                  This business uses a secure service from Meta to manage this chat. <span className="text-[#008069] font-medium cursor-pointer">Tap to learn more</span>
                </span>
              </div>
              
              {/* Conditional Preview by Template Type */}
              {templateType === "OTP" ? (
                /* OTP Verification Card Preview */
                <div className="bg-white p-4 rounded-2xl rounded-tl-none shadow-sm max-w-[92%] mt-2 text-xs leading-relaxed text-slate-800 space-y-2.5">
                  <div className="font-bold text-base text-slate-900">
                    123456 <span className="font-normal text-xs text-slate-700">is your verification code.</span>
                  </div>
                  {otpSecurityRecommendation && (
                    <div className="text-xs text-slate-600">
                      For your security, do not share this code.
                    </div>
                  )}
                  <div className="text-[11px] text-slate-400">
                    This code expires in {otpExpiration} minutes.
                  </div>
                  <div className="pt-2 border-t border-slate-100">
                    <button type="button" className="w-full py-2 bg-emerald-50 text-[#00b050] rounded-lg font-bold text-xs text-center border border-emerald-100">
                      📋 {otpButtonText || "Copy code"}
                    </button>
                  </div>
                  <div className="text-[10px] text-slate-400 text-right">{currentTime}</div>
                </div>
              ) : templateType === "Carousel" ? (
                /* Carousel Cards Horizontal Preview */
                <div className="space-y-3">
                  {bodyText && (
                    <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-xs max-w-[90%] text-xs leading-relaxed text-slate-800">
                      {renderFormattedBody()}
                      <div className="text-[10px] text-slate-400 text-right mt-1">{currentTime}</div>
                    </div>
                  )}

                  {/* Horizontal Scrollable Cards */}
                  <div className="flex gap-2.5 overflow-x-auto pb-2 -mx-1 px-1">
                    {carouselCards.map((card, idx) => (
                      <div key={card.id || idx} className="w-48 shrink-0 bg-white rounded-2xl overflow-hidden shadow-xs border border-slate-100 flex flex-col">
                        <div className="h-24 bg-slate-100 flex items-center justify-center text-slate-400 text-xs font-bold border-b border-slate-50">
                          {carouselMediaType}
                        </div>
                        {carouselIncludeBody && (
                          <div className="p-2.5 text-xs text-slate-700 line-clamp-2">
                            {card.body || `Card ${idx + 1}`}
                          </div>
                        )}
                        <div className="mt-auto border-t border-slate-100 p-2 text-center text-xs font-bold text-[#00a5f4] bg-slate-50/50">
                          {carouselButtonLabel || "Buy now"}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-400 text-center">Cards scroll sideways. Sample values stand in for dynamic content.</p>
                </div>
              ) : (
                /* Standard & Offer Bubble Preview */
                <div className="bg-white p-3.5 rounded-2xl rounded-tl-none shadow-xs self-start max-w-[92%] relative mt-2 text-xs leading-relaxed text-slate-800">
                  {/* Header Preview */}
                  {headerType === "Text" && headerText ? (
                    <div className="mb-2 font-bold text-sm text-slate-900 border-b border-slate-100 pb-1.5 leading-snug">
                      {headerText}
                    </div>
                  ) : headerType === "Image" ? (
                    headerPreviewUrl ? (
                      <div className="mb-2.5 w-full h-36 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 shadow-2xs">
                        <img src={headerPreviewUrl} alt="Header Preview" className="w-full h-full object-cover" />
                      </div>
                    ) : (
                      <div className="mb-2.5 w-full h-28 bg-emerald-50/60 rounded-xl flex flex-col items-center justify-center text-slate-500 text-xs font-medium border border-dashed border-emerald-200/80 gap-1.5">
                        <svg className="w-7 h-7 text-[#00b050]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span className="text-[11px] font-bold text-slate-700">Image Header</span>
                        <span className="text-[10px] text-slate-400">Sample image will appear here</span>
                      </div>
                    )
                  ) : headerType === "Video" ? (
                    headerPreviewUrl ? (
                      <div className="mb-2.5 w-full h-36 rounded-xl overflow-hidden border border-slate-200 bg-black shadow-2xs">
                        <video src={headerPreviewUrl} controls className="w-full h-full object-cover" />
                      </div>
                    ) : (
                      <div className="mb-2.5 w-full h-28 bg-emerald-50/60 rounded-xl flex flex-col items-center justify-center text-slate-500 text-xs font-medium border border-dashed border-emerald-200/80 gap-1.5">
                        <svg className="w-7 h-7 text-[#00b050]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <span className="text-[11px] font-bold text-slate-700">Video Header</span>
                        <span className="text-[10px] text-slate-400">Sample video will play here</span>
                      </div>
                    )
                  ) : headerType === "Document" ? (
                    <div className="mb-2.5 w-full p-2.5 bg-slate-50 rounded-xl flex items-center gap-2.5 border border-slate-200 shadow-2xs">
                      <div className="w-9 h-9 rounded-lg bg-rose-100 flex items-center justify-center text-rose-600 font-bold text-xs shrink-0">
                        PDF
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-slate-800 truncate">
                          {headerFile ? headerFile.name : "document.pdf"}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {headerFile ? `${(headerFile.size / 1024).toFixed(0)} KB · PDF` : "Sample document"}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {/* Body with rich formatting & variable chips */}
                  <div className="leading-relaxed text-[13px] text-slate-800">
                    {renderFormattedBody()}
                  </div>

                  {/* Limited Time Offer Coupon Badge */}
                  {templateType === "Offer" && (
                    <div className="mt-3 p-3 bg-amber-50/80 border border-amber-200 rounded-xl text-center space-y-1.5">
                      <div className="text-[10px] font-bold text-amber-800 uppercase tracking-wider flex items-center justify-center gap-1">
                        <span>🏷️ Offer Coupon</span>
                      </div>
                      <div className="font-mono font-bold text-sm text-slate-900 bg-white py-1 px-3 rounded-lg border border-dashed border-amber-400 inline-block shadow-2xs">
                        {offerCouponCode || "SUMMER20"}
                      </div>
                      {offerExpirationText && (
                        <div className="text-[10px] text-amber-700 font-medium">⏳ {offerExpirationText}</div>
                      )}
                    </div>
                  )}

                  {/* Footer */}
                  {footerText && (
                    <div className="text-[11px] text-slate-500 mt-2 italic border-t border-slate-50 pt-1">
                      {footerText}
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 text-right mt-1.5 flex items-center justify-end gap-1">
                    <span>{currentTime}</span>
                    <svg className="w-3.5 h-3.5 text-[#53bdeb]" viewBox="0 0 16 11" fill="currentColor">
                      <path d="M11.07 0.93a0.75 0.75 0 0 0-1.06 0L5.3 5.64 3.73 4.07a0.75 0.75 0 0 0-1.06 1.06l2.1 2.1a0.75 0.75 0 0 0 1.06 0l5.24-5.24a0.75 0.75 0 0 0 0-1.06z" />
                      <path d="M14.07 0.93a0.75 0.75 0 0 0-1.06 0L8.3 5.64l0.53 0.53 4.71-4.71a0.75 0.75 0 0 0 0-1.06z" />
                    </svg>
                  </div>

                  {/* Buttons */}
                  {buttons.filter(Boolean).length > 0 && (
                    <div className="mt-2.5 -mx-3.5 -mb-3.5 border-t border-slate-100 divide-y divide-slate-100">
                      {buttons.filter(Boolean).map((b, i) => (
                        <div key={i} className="py-2.5 text-center text-xs font-bold text-[#00a5f4] hover:bg-slate-50 transition cursor-pointer flex items-center justify-center gap-1.5">
                          <svg className="w-3.5 h-3.5 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                          </svg>
                          <span>{b}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-40 mix-blend-multiply pointer-events-none" style={{ backgroundImage: 'radial-gradient(#cfd8dc 1px, transparent 1px)', backgroundSize: '20px 20px' }} />

            {/* Phone Home Bar */}
            <div className="h-7 bg-[#f0f0f0] w-full mt-auto relative z-10 flex justify-center pb-1">
              <div className="w-28 h-1 bg-slate-400 rounded-full mt-auto" />
            </div>
          </div>
        </div>

      </div>

      <AiTemplateModal open={aiOpen} onClose={() => setAiOpen(false)} onUse={(d) => { applyDraft(d); setAiOpen(false); }} />
    </div>
  );
}

