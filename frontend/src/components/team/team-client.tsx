"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import {
  TeamApiError,
  inviteMember,
  listInvitations,
  listMembers,
  listRoles,
  removeMember,
  revokeInvitation,
  updateMember,
  type Invitation,
  type Role,
  type TeamMember,
} from "@/lib/team/browser";

const PAGE_SIZE = 20;
const MANAGER_ROLES = new Set(["OWNER", "ADMIN", "MANAGER"]);
const REMOVER_ROLES = new Set(["OWNER", "ADMIN"]);
const SENSITIVE_ROLES = new Set(["OWNER", "ADMIN"]);

type Notice = { kind: "success" | "error"; text: string } | null;

interface CurrentUser {
  id: string;
  role: string;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
}

function memberName(member: TeamMember) {
  return [member.first_name, member.last_name].filter(Boolean).join(" ") || member.email;
}

function statusLabel(member: TeamMember): { label: string; tone: string } {
  if (member.membership_status === "suspended") return { label: "Suspended", tone: "channel-pill-warn" };
  if (!member.is_verified) return { label: "Invited", tone: "channel-pill-muted" };
  return { label: "Active", tone: "channel-pill-ok" };
}

export function TeamClient({ currentUser }: { currentUser: CurrentUser }) {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const [roles, setRoles] = useState<Role[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role_id: "" });
  const [inviteError, setInviteError] = useState("");
  const [inviting, setInviting] = useState(false);

  const [manage, setManage] = useState<{ member: TeamMember; roleId: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => Promise<void> } | null>(null);

  const canManage = MANAGER_ROLES.has(currentUser.role);
  const canRemove = REMOVER_ROLES.has(currentUser.role);
  const assignableRoles = useMemo(() => roles.filter((r) => r.assignable), [roles]);
  const manageableRoleNames = useMemo(() => new Set(assignableRoles.map((r) => r.name)), [assignableRoles]);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadMembers = useCallback(async (targetPage: number, term: string) => {
    setLoading(true);
    setLoadError(false);
    try {
      const result = await listMembers({ page: targetPage, page_size: PAGE_SIZE, search: term || undefined });
      setMembers(result.items);
      setTotal(result.total);
    } catch (error) {
      if (!(error instanceof TeamApiError && error.status === 401)) setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAux = useCallback(async () => {
    const [rolesResult, invitesResult] = await Promise.allSettled([listRoles(), listInvitations()]);
    if (rolesResult.status === "fulfilled") setRoles(rolesResult.value);
    if (invitesResult.status === "fulfilled") setInvitations(invitesResult.value);
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => loadMembers(page, search));
  }, [loadMembers, page, search]);

  useEffect(() => {
    void Promise.resolve().then(() => loadAux());
  }, [loadAux]);

  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const handle = setTimeout(() => {
      setPage(1);
      setSearch(searchInput.trim());
    }, 350);
    return () => clearTimeout(handle);
  }, [searchInput]);

  const handleError = (error: unknown, fallback: string) =>
    setNotice({ kind: "error", text: error instanceof TeamApiError ? error.message : fallback });

  async function submitInvite(event: FormEvent) {
    event.preventDefault();
    const email = inviteForm.email.trim();
    if (!email.includes("@")) return setInviteError("Enter a valid email address.");
    if (!inviteForm.role_id) return setInviteError("Choose a role for this member.");
    setInviting(true);
    setInviteError("");
    try {
      await inviteMember({ email, role_id: inviteForm.role_id });
      setInviteOpen(false);
      setInviteForm({ email: "", role_id: "" });
      setNotice({
        kind: "success",
        text: "Invitation created. Email delivery is not configured yet, so share the invite link from your backend until it is.",
      });
      await loadAux();
    } catch (error) {
      setInviteError(error instanceof TeamApiError ? error.message : "Could not create this invitation.");
    } finally {
      setInviting(false);
    }
  }

  async function doRevoke(invitation: Invitation) {
    setBusy(true);
    setNotice(null);
    try {
      await revokeInvitation(invitation.id);
      setNotice({ kind: "success", text: "Invitation revoked." });
      await loadAux();
    } catch (error) {
      handleError(error, "Could not revoke this invitation.");
    } finally {
      setBusy(false);
    }
  }

  async function applyRoleChange(member: TeamMember, roleId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await updateMember(member.id, { role_id: roleId });
      setManage(null);
      setNotice({ kind: "success", text: "Role updated." });
      await Promise.all([loadMembers(page, search), loadAux()]);
    } catch (error) {
      handleError(error, "Could not update this member's role.");
    } finally {
      setBusy(false);
    }
  }

  async function applyStatusChange(member: TeamMember, status: "active" | "suspended") {
    setBusy(true);
    setNotice(null);
    try {
      await updateMember(member.id, { status });
      setManage(null);
      setNotice({ kind: "success", text: status === "suspended" ? "Member suspended." : "Member reactivated." });
      await loadMembers(page, search);
    } catch (error) {
      handleError(error, "Could not update this member's status.");
    } finally {
      setBusy(false);
    }
  }

  async function doRemove(member: TeamMember) {
    setBusy(true);
    setNotice(null);
    try {
      await removeMember(member.id);
      setManage(null);
      setNotice({ kind: "success", text: "Member removed from the workspace. Their conversation history is kept." });
      await loadMembers(page, search);
    } catch (error) {
      handleError(error, "Could not remove this member.");
    } finally {
      setBusy(false);
    }
  }

  const rangeLabel = total === 0 ? "No members" : `${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} of ${total}`;

  return (
    <section className="page-enter max-w-5xl">
      <header className="channel-header">
        <div>
          <p className="eyebrow">OMNIFLOW WORKSPACE</p>
          <h1 className="page-title mt-2">Team</h1>
          <p className="page-subtitle mt-2">The people and roles in your workspace.</p>
        </div>
        {canManage && (
          <button type="button" className="channel-primary-btn" onClick={() => { setInviteError(""); setInviteForm({ email: "", role_id: "" }); setInviteOpen(true); }}>
            <span aria-hidden="true">+</span> Invite member
          </button>
        )}
      </header>

      {notice && (
        <div className={`channel-notice channel-notice-${notice.kind}`} role="status">
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <div className="contact-toolbar">
        <label className="contact-search">
          <span className="sr-only">Search team members</span>
          <span className="contact-search-icon" aria-hidden="true">⌕</span>
          <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Search by name or email" maxLength={100} />
        </label>
        <span className="contact-range" aria-live="polite">{rangeLabel}</span>
      </div>

      {loading ? (
        <div className="channel-state" role="status">Loading team members…</div>
      ) : loadError ? (
        <div className="channel-state channel-state-error" role="alert">
          <strong>The team could not be loaded.</strong>
          <p>The team service did not respond. Please try again.</p>
          <button type="button" className="channel-secondary-btn" onClick={() => void loadMembers(page, search)}>Try again</button>
        </div>
      ) : members.length === 0 ? (
        <div className="channel-state channel-empty">
          <span className="channel-empty-mark" aria-hidden="true">T</span>
          <strong>{search ? "No matching members" : "No members yet"}</strong>
          <p>{search ? "Try a different name or email." : "Invite your teammates to collaborate in this workspace."}</p>
        </div>
      ) : (
        <>
          <div className="contact-table" role="table" aria-label="Team members">
            <div className="contact-row team-row contact-head" role="row">
              <span role="columnheader">Name</span>
              <span role="columnheader">Email</span>
              <span role="columnheader">Role</span>
              <span role="columnheader">Status</span>
              <span role="columnheader">Joined</span>
              <span role="columnheader" className="contact-actions-col">Actions</span>
            </div>
            {members.map((member) => {
              const status = statusLabel(member);
              const isSelf = member.id === currentUser.id;
              const manageable = canManage && manageableRoleNames.has(member.role);
              return (
                <div className="contact-row team-row" role="row" key={member.id}>
                  <span role="cell" data-label="Name" className="contact-name-cell">
                    <span className="contact-avatar" aria-hidden="true">{memberName(member).slice(0, 1).toUpperCase()}</span>
                    <span className="contact-link-static">{memberName(member)}{isSelf && <em className="team-you"> (you)</em>}</span>
                  </span>
                  <span role="cell" data-label="Email">{member.email}</span>
                  <span role="cell" data-label="Role"><span className="team-role-tag">{member.role}</span></span>
                  <span role="cell" data-label="Status"><span className={`channel-pill ${status.tone}`}>{status.label}</span></span>
                  <span role="cell" data-label="Joined">{formatDate(member.created_at)}</span>
                  <span role="cell" data-label="Actions" className="contact-actions-col">
                    {manageable ? (
                      <button type="button" className="channel-action" onClick={() => setManage({ member, roleId: member.role_id })}>Manage</button>
                    ) : (
                      <span className="contact-muted team-no-manage">—</span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>

          <nav className="contact-pagination" aria-label="Pagination">
            <button type="button" className="channel-secondary-btn" disabled={page <= 1 || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>← Previous</button>
            <span>Page {page} of {totalPages}</span>
            <button type="button" className="channel-secondary-btn" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>Next →</button>
          </nav>
        </>
      )}

      {/* Pending invitations */}
      {canManage && invitations.length > 0 && (
        <section className="team-invites" aria-label="Pending invitations">
          <h2>Pending invitations</h2>
          <p className="contact-muted team-invite-note">Email delivery is not configured yet — these invitations exist but are not emailed automatically.</p>
          <ul>
            {invitations.map((invite) => (
              <li key={invite.id}>
                <span className="team-invite-main">
                  <strong>{invite.email}</strong>
                  <small>{invite.role} · expires {formatDate(invite.expires_at)}</small>
                </span>
                <button type="button" className="channel-action channel-action-danger" disabled={busy} onClick={() => void doRevoke(invite)}>Revoke</button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Invite modal */}
      {inviteOpen && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="invite-title">
          <div className="channel-modal">
            <h2 id="invite-title">Invite a team member</h2>
            <p className="channel-modal-sub">They will receive access with the role you choose once they accept.</p>
            <form onSubmit={submitInvite} className="channel-form">
              <label className="channel-field">
                <span>Email</span>
                <input type="email" value={inviteForm.email} onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })} placeholder="teammate@example.com" autoComplete="off" required autoFocus />
              </label>
              <label className="channel-field">
                <span>Role</span>
                <select value={inviteForm.role_id} onChange={(e) => setInviteForm({ ...inviteForm, role_id: e.target.value })} required>
                  <option value="" disabled>Select a role…</option>
                  {assignableRoles.map((role) => (
                    <option key={role.id} value={role.id}>{role.name}{role.description ? ` — ${role.description}` : ""}</option>
                  ))}
                </select>
              </label>
              {inviteError && <p className="channel-form-error" role="alert">{inviteError}</p>}
              <div className="channel-modal-actions">
                <button type="button" className="channel-secondary-btn" onClick={() => setInviteOpen(false)} disabled={inviting}>Cancel</button>
                <button type="submit" className="channel-primary-btn" disabled={inviting || assignableRoles.length === 0}>{inviting ? "Inviting…" : "Send invite"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manage member modal */}
      {manage && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="manage-title">
          <div className="channel-modal">
            <h2 id="manage-title">Manage {memberName(manage.member)}</h2>
            <p className="channel-modal-sub">{manage.member.email}</p>

            <label className="channel-field team-manage-field">
              <span>Role</span>
              <select value={manage.roleId} onChange={(e) => setManage({ ...manage, roleId: e.target.value })}>
                {assignableRoles.map((role) => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="channel-secondary-btn team-full-btn"
              disabled={busy || manage.roleId === manage.member.role_id}
              onClick={() => {
                const target = roles.find((r) => r.id === manage.roleId);
                const member = manage.member;
                if (target && SENSITIVE_ROLES.has(target.name)) {
                  setConfirm({
                    title: `Grant the ${target.name} role?`,
                    message: `${memberName(member)} will gain the elevated ${target.name} role and its permissions.`,
                    action: () => applyRoleChange(member, manage.roleId),
                  });
                } else {
                  void applyRoleChange(member, manage.roleId);
                }
              }}
            >
              Save role change
            </button>

            <div className="team-manage-divider" />

            <div className="team-manage-row">
              {manage.member.membership_status === "suspended" ? (
                <button type="button" className="channel-secondary-btn" disabled={busy} onClick={() => void applyStatusChange(manage.member, "active")}>Reactivate member</button>
              ) : (
                <button
                  type="button"
                  className="channel-secondary-btn channel-btn-danger-outline"
                  disabled={busy}
                  onClick={() => setConfirm({
                    title: `Suspend ${memberName(manage.member)}?`,
                    message: "They will lose access to this workspace until reactivated. Conversations, messages and contacts are kept.",
                    action: () => applyStatusChange(manage.member, "suspended"),
                  })}
                >
                  Suspend member
                </button>
              )}
              {canRemove && (
                <button
                  type="button"
                  className="channel-secondary-btn channel-btn-danger-outline"
                  disabled={busy}
                  onClick={() => setConfirm({
                    title: `Remove ${memberName(manage.member)}?`,
                    message: "They will be removed from this workspace. Their account and historical data are preserved, and they can be re-invited later.",
                    action: () => doRemove(manage.member),
                  })}
                >
                  Remove from workspace
                </button>
              )}
            </div>

            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => setManage(null)} disabled={busy}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation dialog */}
      {confirm && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="confirm-title">{confirm.title}</h2>
            <p className="channel-modal-sub">{confirm.message}</p>
            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => setConfirm(null)} disabled={busy}>Cancel</button>
              <button type="button" className="channel-primary-btn channel-btn-danger" disabled={busy} onClick={async () => { const action = confirm.action; setConfirm(null); await action(); }}>
                {busy ? "Working…" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
