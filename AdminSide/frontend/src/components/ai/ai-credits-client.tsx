"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

const ChevronLeftIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="15 18 9 12 15 6" /></svg>);
const ZapIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>);
const SettingsIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>);
const PlusIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>);
const RefreshCwIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>);
const DownloadIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>);
const ArrowUpRightIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="7" y1="17" x2="17" y2="7" /><polyline points="7 7 17 7 17 17" /></svg>);
const MessageSquareIcon = (props: React.SVGProps<SVGSVGElement>) => (<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>);

interface PaymentTx {
  id: string;
  razorpay_order_id: string;
  razorpay_payment_id: string | null;
  amount: number;
  currency: string;
  credits_amount: number;
  status: string;
  description: string | null;
  created_at: string;
}

interface UsageTx {
  id: string;
  description: string;
  model: string | null;
  tokens_in: number;
  tokens_out: number;
  credits: number;
  created_at: string;
}

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if ((window as unknown as { Razorpay?: unknown }).Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

const packages = [
  { id: 1, credits: 500, price: 50, replies: 308 },
  { id: 2, credits: 1000, price: 100, replies: 617, popular: true },
  { id: 3, credits: 2500, price: 250, replies: 1543 },
  { id: 4, credits: 5000, price: 500, replies: 3086 },
];

export function AiCreditsClient() {
  const [selectedPack, setSelectedPack] = useState<number>(2);
  const [customAmount, setCustomAmount] = useState<string>("");
  const [balance, setBalance] = useState<number>(500.0);
  const [transactions, setTransactions] = useState<PaymentTx[]>([]);
  const [usage, setUsage] = useState<UsageTx[]>([]);
  const [usageTotal, setUsageTotal] = useState<number>(0);
  const [isPaying, setIsPaying] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const activeCredits = customAmount ? parseInt(customAmount) || 0 : (packages.find(p => p.id === selectedPack)?.credits || 0);
  const activePrice = activeCredits * 0.10;
  const activeGst = activePrice * 0.18;
  const total = activePrice + activeGst;

  // Real figures derived from the tenant's purchase transactions.
  const paidTx = transactions.filter((t) => ["paid", "captured", "success", "completed"].includes((t.status || "").toLowerCase()));
  const purchasedCredits = paidTx.reduce((sum, t) => sum + Number(t.credits_amount || 0), 0);
  const paidPurchases = paidTx.length;

  const fetchBalance = useCallback(async () => {
    try {
      const res = await fetch("/api/payments/balance");
      if (res.ok) {
        const data = await res.json();
        if (typeof data.balance === "number") {
          setBalance(data.balance);
        }
      }
    } catch {
      // keep fallback
    }
  }, []);

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch("/api/payments/transactions");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.items)) {
          setTransactions(data.items);
        }
      }
    } catch {
      // keep fallback
    }
  }, []);

  const fetchUsage = useCallback(async () => {
    try {
      const res = await fetch("/api/payments/usage");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.items)) setUsage(data.items);
        if (typeof data.total_credits === "number") setUsageTotal(data.total_credits);
      }
    } catch {
      // keep fallback
    }
  }, []);

  useEffect(() => {
    fetchBalance();
    fetchTransactions();
    fetchUsage();
  }, [fetchBalance, fetchTransactions, fetchUsage]);

  async function handlePayment() {
    if (activeCredits <= 0) return;
    setIsPaying(true);
    setStatusMessage(null);

    try {
      const loaded = await loadRazorpayScript();
      if (!loaded) {
        setStatusMessage({ type: "error", text: "Razorpay SDK could not be loaded. Please check your internet connection." });
        setIsPaying(false);
        return;
      }

      const orderRes = await fetch("/api/payments/create-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          credits: activeCredits,
          amount: parseFloat(total.toFixed(2)),
          description: `${activeCredits.toLocaleString()} AI Credits`,
        }),
      });

      const orderData = await orderRes.json();
      if (!orderRes.ok) {
        throw new Error(orderData.error || orderData.detail || "Failed to create payment order.");
      }

      type RazorpaySuccessPayload = {
        razorpay_order_id: string;
        razorpay_payment_id: string;
        razorpay_signature: string;
      };

      const options = {
        key: orderData.key_id,
        amount: Math.round(orderData.amount * 100),
        currency: orderData.currency || "INR",
        name: "Omniflow",
        description: `${activeCredits.toLocaleString()} AI Credits`,
        order_id: orderData.order_id,
        handler: async function (response: RazorpaySuccessPayload) {
          try {
            const verifyRes = await fetch("/api/payments/verify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });
            const verifyData = await verifyRes.json();
            if (verifyRes.ok && verifyData.success) {
              setBalance(verifyData.new_balance);
              setStatusMessage({
                type: "success",
                text: `Payment successful! ₹${total.toFixed(2)} paid. ${verifyData.credits_added} credits have been added to your balance.`,
              });
              fetchTransactions();
            } else {
              setStatusMessage({
                type: "error",
                text: verifyData.error || verifyData.detail || "Payment signature verification failed.",
              });
            }
          } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Payment verification failed.";
            setStatusMessage({ type: "error", text: msg });
          } finally {
            setIsPaying(false);
          }
        },
        theme: {
          color: "#00b050",
        },
        modal: {
          ondismiss: function () {
            setIsPaying(false);
          },
        },
      };

      const razorpayInstance = new (window as unknown as { Razorpay: new (opts: typeof options) => { open: () => void; on: (evt: string, fn: (resp: { error?: { description?: string } }) => void) => void } }).Razorpay(options);
      razorpayInstance.on("payment.failed", function (resp) {
        setStatusMessage({ type: "error", text: resp.error?.description || "Payment was cancelled or failed." });
        setIsPaying(false);
      });
      razorpayInstance.open();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An error occurred while initiating payment.";
      setStatusMessage({ type: "error", text: msg });
      setIsPaying(false);
    }
  }

  return (
    <div className="bg-[#f8f9fa] min-h-screen text-slate-800 font-sans pb-10">
      
      {/* Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="px-6 py-4 flex items-center justify-between mx-auto max-w-7xl">
          <div className="flex items-center gap-4">
            <Link href="/ai-configuration" className="p-2 border border-slate-200 rounded-full hover:bg-slate-50 transition-colors">
              <ChevronLeftIcon className="w-5 h-5 text-slate-500" />
            </Link>
            <h1 className="text-xl font-bold text-slate-800">AI Credits</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#e8f5e9] text-[#00b050] px-4 py-2 rounded-full font-bold text-sm border border-[#c8e6c9]">
              <ZapIcon className="w-4 h-4 fill-current" />
              <span>{balance.toFixed(2)} AI Credits</span>
            </div>
            <button className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50 shadow-sm">
              <SettingsIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 mx-auto max-w-7xl">
        
        {/* Top Cards Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
          
          <div className="lg:col-span-2 bg-[#00a144] rounded-2xl p-8 shadow-sm text-white relative overflow-hidden flex flex-col justify-between min-h-[220px]">
            {/* Background decoration */}
            <div className="absolute right-0 bottom-0 opacity-10 transform translate-x-1/4 translate-y-1/4">
              <svg width="200" height="200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
            </div>
            
            <div className="relative z-10 flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 text-white/80 font-bold text-xs tracking-widest uppercase mb-4">
                  <ZapIcon className="w-4 h-4 fill-current" /> AI CREDIT BALANCE
                </div>
                <div className="text-6xl font-black mb-2">{balance.toFixed(2)}</div>
                <div className="text-white/80 font-medium">
                  ≈ {Math.round(balance / 1.62)} AI replies left &middot; live balance
                </div>
              </div>
              <button 
                onClick={() => document.getElementById("buy-credits-section")?.scrollIntoView({ behavior: "smooth" })}
                className="flex items-center gap-2 bg-white text-[#00a144] px-5 py-2.5 rounded-full font-bold text-sm shadow-sm hover:bg-slate-50 transition-colors"
              >
                <PlusIcon className="w-4 h-4" /> Buy credits
              </button>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
            <div className="flex justify-between items-start pb-4 border-b border-slate-100">
              <div className="text-slate-500 text-sm font-semibold">Credits purchased</div>
              <div className="text-right">
                <div className="font-black text-slate-900">{purchasedCredits.toLocaleString()} credits</div>
                <div className="text-xs text-slate-400">{paidPurchases} purchase{paidPurchases === 1 ? "" : "s"}</div>
              </div>
            </div>
            <div className="flex justify-between items-start py-4 border-b border-slate-100">
              <div className="text-slate-500 text-sm font-semibold">Current balance</div>
              <div className="text-right">
                <div className="font-black text-slate-900">{balance.toFixed(2)} credits</div>
                <div className="text-xs text-slate-400">≈ {Math.round(balance / 1.62)} AI replies</div>
              </div>
            </div>
            <div className="flex justify-between items-start pt-4">
              <div className="text-slate-500 text-sm font-semibold">Low-balance alert</div>
              <div className="text-right">
                <div className="font-bold text-slate-900">Below 50 credits</div>
              </div>
            </div>
            <p className="text-[10px] text-slate-400 mt-4 leading-relaxed">
              Unused credits carry over. Credits are added to your balance as soon as a payment is confirmed.
            </p>
          </div>

        </div>

        {/* Status Message Alert */}
        {statusMessage && (
          <div className={`mb-6 p-4 rounded-xl border flex items-center justify-between ${
            statusMessage.type === "success" 
              ? "bg-emerald-50 border-emerald-200 text-emerald-800" 
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span>{statusMessage.type === "success" ? "✓" : "⚠"}</span>
              <span>{statusMessage.text}</span>
            </div>
            <button 
              onClick={() => setStatusMessage(null)}
              className="text-xs font-bold underline ml-4 hover:opacity-80"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Buy Credits Section */}
        <div id="buy-credits-section" className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm mb-10">
          <div className="flex justify-between items-end mb-6">
            <h2 className="text-lg font-bold text-slate-900">Buy credits</h2>
            <div className="text-sm text-slate-500 font-medium">₹0.10 per credit + 18% GST &middot; your replies average 1.62 credits</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {packages.map(p => (
              <button 
                key={p.id}
                onClick={() => { setSelectedPack(p.id); setCustomAmount(""); }}
                className={`relative p-5 rounded-xl border-2 text-left transition-all ${
                  selectedPack === p.id && !customAmount 
                    ? "border-[#00b050] bg-emerald-50/20" 
                    : "border-slate-200 hover:border-slate-300 bg-white"
                }`}
              >
                {p.popular && (
                  <div className="absolute -top-3 right-4 bg-[#00b050] text-white text-[10px] font-black uppercase tracking-wider px-2 py-1 rounded-full">
                    POPULAR
                  </div>
                )}
                <div className="text-lg font-black text-slate-900 leading-none mb-1">{p.credits.toLocaleString()}</div>
                <div className="text-xs text-slate-500 mb-4">credits</div>
                
                <div className="font-bold text-slate-900">₹{p.price.toFixed(2)} <span className="text-slate-400 font-normal text-xs">+ GST</span></div>
                <div className="text-xs text-slate-500 mt-1">≈ {p.replies.toLocaleString()} replies</div>
              </button>
            ))}
          </div>

          <div className="mb-8">
            <label className="block text-sm font-semibold text-slate-500 mb-2">Or enter your own amount</label>
            <input 
              type="number"
              placeholder="Number of credits, e.g. 1500"
              value={customAmount}
              onChange={(e) => { setCustomAmount(e.target.value); setSelectedPack(0); }}
              className="w-full md:w-1/2 px-4 py-3 bg-white border border-slate-200 rounded-lg text-sm outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]"
            />
          </div>

          <div className="bg-slate-50 border border-slate-100 rounded-xl p-6 flex flex-col md:flex-row justify-between items-center">
            <div className="w-full md:w-64 space-y-2 mb-6 md:mb-0">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500 font-medium">{activeCredits.toLocaleString()} credits</span>
                <span className="font-bold text-slate-800">₹{activePrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500 font-medium">GST (18%)</span>
                <span className="font-bold text-slate-800">₹{activeGst.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-base pt-2 border-t border-slate-200 mt-2">
                <span className="font-bold text-slate-900">Total</span>
                <span className="font-black text-slate-900">₹{total.toFixed(2)}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-slate-400 pt-2">
                <ShieldCheckIcon className="w-3 h-3" /> Secure checkout by Razorpay. Credits are added as soon as your payment is confirmed.
              </div>
            </div>
            
            <button 
              onClick={handlePayment}
              disabled={isPaying || activeCredits <= 0}
              className={`w-full md:w-auto px-12 py-3.5 rounded-lg font-bold text-base shadow-sm transition-colors flex items-center justify-center gap-2 ${
                isPaying || activeCredits <= 0
                  ? "bg-slate-300 text-slate-500 cursor-not-allowed"
                  : "bg-[#00b050] hover:bg-[#009040] text-white cursor-pointer"
              }`}
            >
              {isPaying ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Processing...</span>
                </>
              ) : (
                `Pay ₹${total.toFixed(2)}`
              )}
            </button>
          </div>
        </div>

        {/* Where your credits went */}
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm mb-10">
          <div className="flex justify-between items-start mb-8">
            <div>
              <h2 className="text-lg font-bold text-slate-900 mb-1">Where your credits went</h2>
              <p className="text-sm text-slate-500">
                {usageTotal.toFixed(2)} credits across {usage.length} AI {usage.length === 1 ? "reply" : "replies"}
              </p>
            </div>
          </div>

          {usage.length === 0 ? (
            <div className="py-10 text-center text-sm text-slate-400 border border-dashed border-slate-200 rounded-xl">
              No AI usage yet.
            </div>
          ) : (
            <div className="space-y-6">
              {usage.map((u) => {
                const max = Math.max(0.01, ...usage.map((x) => Number(x.credits) || 0));
                const pct = Math.round(((Number(u.credits) || 0) / max) * 100);
                return (
                  <div key={u.id}>
                    <div className="flex justify-between text-sm mb-2">
                      <div>
                        <div className="font-bold text-slate-700 flex items-center gap-1.5 mb-0.5">
                          <MessageSquareIcon className="w-3.5 h-3.5 text-slate-400" /> {u.description}
                        </div>
                        <div className="text-[11px] text-slate-400 font-medium">
                          {u.model || "—"} &middot; {(u.tokens_in + u.tokens_out).toLocaleString()} tokens &middot; {new Date(u.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-slate-800">{(Number(u.credits) || 0).toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div className="bg-[#00b050] h-1.5 rounded-full" style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Transaction history */}
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-slate-900">
              Transaction history 
              <span className="text-slate-400 font-normal text-sm ml-2">
                {transactions.length > 0 ? `${transactions.length} online purchases` : "Recent activity"}
              </span>
            </h2>
            <div className="flex gap-3">
              <button 
                onClick={() => fetchTransactions()}
                className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <RefreshCwIcon className="w-4 h-4" /> Refresh
              </button>
              <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50">
                <DownloadIcon className="w-4 h-4" /> Export
              </button>
            </div>
          </div>

          <div className="flex gap-4 mb-6">
            <div className="relative flex-1">
              <svg className="w-4 h-4 absolute left-3 top-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              <input type="search" placeholder="Search description or type..." className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]" />
            </div>
            <select className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 outline-none w-48">
              <option>All types</option>
              <option>Usage</option>
              <option>Purchase</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Type</th>
                  <th className="pb-3 font-semibold">Description</th>
                  <th className="pb-3 font-semibold">Reference</th>
                  <th className="pb-3 font-semibold">Gateway</th>
                  <th className="pb-3 font-semibold text-center">Amount</th>
                  <th className="pb-3 font-semibold">Date</th>
                  <th className="pb-3 font-semibold text-right">Credits</th>
                  <th className="pb-3 font-semibold text-right">Balance</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                    <td className="py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 font-bold text-xs">
                        <ZapIcon className="w-3 h-3 fill-current" /> Purchase
                      </span>
                    </td>
                    <td className="py-4 font-semibold text-slate-800">{tx.description || "Credit Purchase"}</td>
                    <td className="py-4 text-xs font-mono text-slate-500">{tx.razorpay_payment_id || tx.razorpay_order_id}</td>
                    <td className="py-4 font-semibold text-slate-700">Razorpay</td>
                    <td className="py-4 text-center font-semibold text-slate-600">₹{tx.amount.toFixed(2)}</td>
                    <td className="py-4 text-slate-500 font-medium">{new Date(tx.created_at).toLocaleString()}</td>
                    <td className="py-4 text-right font-black text-emerald-600">+{Number(tx.credits_amount).toLocaleString()}</td>
                    <td className="py-4 text-right font-bold text-slate-700">-</td>
                  </tr>
                ))}
                {transactions.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-10 text-center text-sm text-slate-400">
                      No transactions yet. Purchased credits will appear here.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}

function ShieldCheckIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>
  );
}
