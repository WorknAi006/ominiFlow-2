"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChannelsClient } from "@/components/channels/channels-client";

type Tab = "General" | "Channels" | "Security" | "Activity";

interface UserSession {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  last_active_at: string;
  is_current: boolean;
}

export function SettingsClient() {
  const [activeTab, setActiveTab] = useState<Tab>("General");
  const [routingAction, setRoutingAction] = useState("Flow");
  const [masterFlow, setMasterFlow] = useState("user messages");
  const [mmLiteEnabled, setMmLiteEnabled] = useState(false);
  
  const [sessions, setSessions] = useState<UserSession[]>([]);

  useEffect(() => {
    if (activeTab === "Security") {
      fetch("/api/users/me/sessions")
        .then(res => res.json())
        .then(data => setSessions(data))
        .catch(console.error);
    }
  }, [activeTab]);
  
  const [activityTab, setActivityTab] = useState<"Important" | "Everything">("Important");

  const handleSaveRouting = () => {
    alert("Global routing saved successfully.");
  };

  const handleSignOutSession = async (id: string) => {
    try {
      await fetch(`/api/users/me/sessions/${id}`, { method: "DELETE" });
      setSessions(sessions.filter(s => s.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const handleSignOutAllOther = async () => {
    try {
      await fetch(`/api/users/me/sessions`, { method: "DELETE" });
      setSessions(sessions.filter(s => s.is_current));
      alert("Signed out of all other devices.");
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-[1000px] w-full pb-20">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-[#0b1028]">Settings</h1>
          <p className="text-[#6d6e7c] text-[13px] mt-1">Manage your workspace configuration and channels</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#e8f6f0] border border-[#b2e2cd] px-4 py-2 rounded-full text-[#147a4d] font-bold text-[13px]">
            <span>⚡</span> 461.12 AI Credits
          </div>
          <button className="w-10 h-10 flex items-center justify-center bg-white border border-[#d6d6e0] rounded-full text-[#6d6e7c] hover:bg-[#f7f8fc]">
            ⚙
          </button>
        </div>
      </div>

      <div className="border-b border-[#e6ece9]">
        <div className="flex gap-8">
          {(["General", "Channels", "Security", "Activity"] as Tab[]).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-1 text-[14px] font-semibold transition-colors relative ${
                activeTab === tab ? "text-[#1b7a53]" : "text-[#6d6e7c] hover:text-[#0b1028]"
              }`}
            >
              {tab}
              {activeTab === tab && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1b7a53] rounded-t-full" />
              )}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "General" && (
        <div className="flex flex-col gap-6">
          <div className="bg-white border border-[#e6ece9] rounded-2xl p-7 shadow-[0_2px_10px_rgba(34,39,56,0.02)]">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[#1b7a53] text-[18px]">⚙</span>
              <h2 className="text-[16px] font-bold text-[#0b1028]">Global Routing Settings</h2>
            </div>
            <p className="text-[#6d6e7c] text-[13px] mb-6">
              Configure how unhandled messages are globally routed in your chatbot. Choose your automated fallback behavior for when no exact keywords match.
            </p>

            <div className="flex flex-col gap-5">
              <div>
                <label className="block text-[#0b1028] text-[13px] font-bold mb-2">Global Fallback Action</label>
                <select 
                  value={routingAction}
                  onChange={(e) => setRoutingAction(e.target.value)}
                  className="w-full h-11 border border-[#d6d6e0] rounded-xl px-4 text-[#0b1028] text-[13px] bg-white outline-none focus:border-[#4f46ff] focus:ring-2 focus:ring-[#4f46ff]/20 appearance-none"
                >
                  <option>Flow</option>
                  <option>Chatbot</option>
                  <option>Human Agent</option>
                </select>
                <div className="mt-3 bg-[#f7f8fc] border border-[#e6ece9] rounded-xl p-3.5 text-[13px] text-[#6d6e7c]">
                  Route every unmatched message into a specific master Rete.js visual flow.
                </div>
              </div>

              <div className="border border-[#f5dfb8] bg-[#fffcf5] rounded-xl p-5 mt-2">
                <label className="block text-[#9a6a16] text-[13px] font-bold mb-2">Select Master Flow Collection</label>
                <select 
                  value={masterFlow}
                  onChange={(e) => setMasterFlow(e.target.value)}
                  className="w-full h-11 border border-[#f5dfb8] rounded-xl px-4 text-[#0b1028] text-[13px] bg-white outline-none focus:border-[#4f46ff] appearance-none"
                >
                  <option>user messages</option>
                  <option>default fallback</option>
                </select>
                <p className="mt-3 text-[#9a6a16] text-[12px]">
                  This flow will be triggered unconditionally when a user types anything that doesn't match an exact keyword rule.
                </p>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button 
                onClick={handleSaveRouting}
                className="bg-[#158e57] hover:bg-[#117648] text-white px-5 py-2.5 rounded-xl font-bold text-[13px] transition-colors"
              >
                Save Global Routing
              </button>
            </div>
          </div>

          <div className="bg-white border border-[#e6ece9] rounded-2xl p-7 shadow-[0_2px_10px_rgba(34,39,56,0.02)]">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-[#1b7a53] text-[18px]">📢</span>
                <h2 className="text-[16px] font-bold text-[#0b1028]">Marketing Messages Lite</h2>
              </div>
            </div>
            <p className="text-[#6d6e7c] text-[13px] mb-6 leading-[1.6] max-w-[850px]">
              Send marketing template broadcasts through Meta's MM Lite API, which optimises delivery for engagement. Only marketing templates in broadcasts use it; if Meta can't deliver a message through MM Lite, it is sent through the regular Cloud API instead.
            </p>

            <div className="flex items-center justify-between bg-[#f7f8fc] border border-[#e6ece9] rounded-xl p-5 mb-5">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <strong className="text-[#0b1028] text-[13px]">Meta onboarding status</strong>
                  <span className="bg-[#e8f6f0] text-[#147a4d] border border-[#b2e2cd] px-2 py-0.5 rounded-md text-[11px] font-bold tracking-wide">Onboarded</span>
                </div>
                <p className="text-[#6d6e7c] text-[13px] mb-1">Your WhatsApp Business Account can send marketing broadcasts through MM Lite.</p>
                <p className="text-[#a0a0aa] text-[11px]">Last checked 10/10/2026, 14:45:43</p>
              </div>
              <button className="flex items-center gap-2 border border-[#d6d6e0] bg-white hover:bg-[#f7f8fc] px-4 py-2 rounded-xl text-[#0b1028] text-[13px] font-semibold transition-colors">
                <span>↻</span> Refresh status
              </button>
            </div>

            <div className="flex items-center justify-between border border-[#e6ece9] rounded-xl p-5">
              <div>
                <strong className="block text-[#0b1028] text-[13px] mb-1">Send marketing broadcasts via MM Lite</strong>
                <p className="text-[#6d6e7c] text-[13px]">Applies to broadcasts created after you change this. Existing broadcasts keep their route.</p>
              </div>
              <button 
                onClick={() => setMmLiteEnabled(!mmLiteEnabled)}
                className={`relative w-12 h-6 rounded-full transition-colors duration-200 focus:outline-none ${mmLiteEnabled ? 'bg-[#158e57]' : 'bg-[#d6d6e0]'}`}
              >
                <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform duration-200 ${mmLiteEnabled ? 'translate-x-6' : 'translate-x-0'}`} />
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === "Channels" && (
        <div className="mt-[-20px]">
          <ChannelsClient />
        </div>
      )}

      {activeTab === "Security" && (
        <div className="flex flex-col gap-6">
          <div className="bg-white border border-[#e6ece9] rounded-2xl p-7 shadow-[0_2px_10px_rgba(34,39,56,0.02)]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-[#1b7a53] text-[18px]">🛡️</span>
                <h2 className="text-[16px] font-bold text-[#0b1028]">Active sessions</h2>
              </div>
              <button className="text-[#6d6e7c] hover:text-[#0b1028] text-lg font-bold">↻</button>
            </div>
            <p className="text-[#6d6e7c] text-[13px] mb-6">
              Everywhere your account is currently signed in. If you do not recognise a device, sign it out — it loses access immediately.
            </p>

            <div className="flex flex-col gap-4">
              {sessions.map(session => (
                <div key={session.id} className="flex items-center justify-between border border-[#e6ece9] rounded-xl p-5">
                  <div className="flex items-start gap-4">
                    <div className="text-[22px] text-[#a0a0aa]">💻</div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <strong className="text-[#0b1028] text-[13px]">{session.device_info || "Unknown Device"}</strong>
                        {session.is_current && (
                          <span className="bg-[#f7f8fc] border border-[#d6d6e0] text-[#0b1028] px-2 py-0.5 rounded-full text-[11px] font-bold">This device</span>
                        )}
                      </div>
                      <div className="text-[#6d6e7c] text-[13px]">
                        {session.ip_address || "Unknown IP"} • active {new Date(session.last_active_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  {!session.is_current && (
                    <button 
                      onClick={() => handleSignOutSession(session.id)}
                      className="flex items-center gap-2 border border-[#d6d6e0] bg-white hover:bg-[#f7f8fc] px-4 py-2 rounded-xl text-[#0b1028] text-[13px] font-semibold transition-colors"
                    >
                      <span>↪</span> Sign out
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white border border-[#e6ece9] rounded-2xl p-7 shadow-[0_2px_10px_rgba(34,39,56,0.02)]">
            <h2 className="text-[14px] font-bold text-[#0b1028] mb-2">Sign out everywhere else</h2>
            <p className="text-[#6d6e7c] text-[13px] mb-5 max-w-[800px]">
              Ends every session except this one. Use this if you have signed in on a device you no longer have, or you think someone else has access.
            </p>
            <button 
              onClick={handleSignOutAllOther}
              className="bg-[#e74c3c] hover:bg-[#c0392b] text-white px-5 py-2.5 rounded-xl font-bold text-[13px] transition-colors"
            >
              Sign out of all other devices
            </button>
          </div>
        </div>
      )}

      {activeTab === "Activity" && (
        <div className="flex flex-col gap-6">
          <div className="bg-white border border-[#e6ece9] rounded-2xl p-7 shadow-[0_2px_10px_rgba(34,39,56,0.02)]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-[#1b7a53] text-[18px]">🕒</span>
                <h2 className="text-[16px] font-bold text-[#0b1028]">Activity log</h2>
              </div>
              <button className="text-[#6d6e7c] hover:text-[#0b1028] text-lg font-bold">↻</button>
            </div>
            <p className="text-[#6d6e7c] text-[13px] mb-6">
              Who changed what, and when. Actions taken by a support admin on your account are shown under their own name.
            </p>

            <div className="flex items-center justify-between mb-8">
              <div className="flex bg-[#f7f8fc] p-1 rounded-xl border border-[#e6ece9]">
                <button 
                  onClick={() => setActivityTab("Important")}
                  className={`px-4 py-1.5 rounded-lg text-[13px] font-semibold transition-colors ${activityTab === "Important" ? "bg-white shadow-[0_1px_3px_rgba(0,0,0,0.08)] text-[#0b1028]" : "text-[#6d6e7c]"}`}
                >
                  Important
                </button>
                <button 
                  onClick={() => setActivityTab("Everything")}
                  className={`px-4 py-1.5 rounded-lg text-[13px] font-semibold transition-colors ${activityTab === "Everything" ? "bg-white shadow-[0_1px_3px_rgba(0,0,0,0.08)] text-[#0b1028]" : "text-[#6d6e7c]"}`}
                >
                  Everything
                </button>
              </div>
              <select className="h-10 border border-[#d6d6e0] rounded-xl px-4 text-[#0b1028] text-[13px] bg-white outline-none focus:border-[#4f46ff] min-w-[220px]">
                <option>Everyone</option>
                <option>Just Me</option>
              </select>
            </div>

            <div className="flex flex-col">
              <h3 className="text-[#8b8c99] text-[12px] font-bold mb-5 uppercase tracking-wider">Wed Oct 07 2026</h3>
              
              <div className="flex items-start gap-4 mb-6">
                <div className="w-8 h-8 rounded-full bg-[#f7f8fc] border border-[#e6ece9] flex items-center justify-center text-[#6d6e7c] text-sm">👤</div>
                <div>
                  <div className="text-[13px]">
                    <strong className="text-[#0b1028] font-bold">alishambgcard@gmail.com</strong> <span className="text-[#6d6e7c]">signed in as this account</span>
                  </div>
                  <div className="text-[#a0a0aa] text-[11px] mt-0.5 font-medium">18:18 · user</div>
                </div>
              </div>

              <div className="flex items-start gap-4 mb-8">
                <div className="w-8 h-8 rounded-full bg-[#f7f8fc] border border-[#e6ece9] flex items-center justify-center text-[#6d6e7c] text-sm">👤</div>
                <div>
                  <div className="text-[13px]">
                    <strong className="text-[#0b1028] font-bold">sejaldhanwani@gmail.com</strong> <span className="text-[#6d6e7c]">updated account details</span>
                  </div>
                  <div className="text-[#a0a0aa] text-[11px] mt-0.5 font-medium">16:13 · user</div>
                </div>
              </div>

              <h3 className="text-[#8b8c99] text-[12px] font-bold mb-5 uppercase tracking-wider">Sat Oct 03 2026</h3>

              <div className="flex items-start gap-4 mb-4">
                <div className="w-8 h-8 rounded-full bg-[#f7f8fc] border border-[#e6ece9] flex items-center justify-center text-[#6d6e7c] text-sm">👤</div>
                <div>
                  <div className="text-[13px]">
                    <strong className="text-[#0b1028] font-bold">onlinegologistics@gmail.com</strong> <span className="text-[#6d6e7c]">changed a template</span>
                  </div>
                  <div className="text-[#a0a0aa] text-[11px] mt-0.5 font-medium">16:23 · template</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
