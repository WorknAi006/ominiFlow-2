"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { adminApi, getAdminToken, setAdminToken } from "../api/admin-client";
import { AdminUser } from "../types/admin";

interface AdminAuthContextType {
  user: AdminUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    const token = getAdminToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const me = await adminApi.getMe();
      if (me.is_platform_admin) {
        setUser((prev) => {
          if (prev && prev.id === me.id && prev.email === me.email) {
            return prev;
          }
          return me;
        });
      } else {
        setAdminToken(null);
        setUser(null);
      }
    } catch {
      setAdminToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await adminApi.login(email, password);
    if (!res.user.is_platform_admin) {
      setAdminToken(null);
      setUser(null);
      throw new Error("You do not have Super Admin access permissions.");
    }
    setUser(res.user);
  };

  const logout = () => {
    adminApi.logout();
    setUser(null);
  };

  return (
    <AdminAuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error("useAdminAuth must be used within an AdminAuthProvider");
  }
  return context;
}
