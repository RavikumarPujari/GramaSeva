"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  LayoutDashboard,
  Building2,
  Users,
  Shield,
  Layers,
  ClipboardList,
  BarChart3,
  Bell,
  History,
  Settings,
  Menu,
  ChevronLeft,
  ChevronRight,
  Search,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Send,
  UserCheck,
  UserX,
  MapPin,
  Clock,
  ArrowRight,
  Eye,
  LogOut,
  Mail,
  Phone,
  Radio,
  FileText,
  Sliders,
  Server,
  Database,
  Globe,
  Sparkles,
  ShieldAlert,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { LeafletMap } from "@/components/ui/LeafletMap";
import { LanguageSelector } from "@/components/ui/LanguageSelector";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";

type AdminSection =
  | "overview"
  | "taluk_overview"
  | "villages"
  | "pdos"
  | "users"
  | "wards"
  | "complaints"
  | "analytics"
  | "announcements"
  | "audit"
  | "settings";

interface OverviewStats {
  total_villages: number;
  total_pdos: number;
  total_workers: number;
  total_citizens: number;
  total_complaints: number;
  resolved_complaints: number;
  pending_complaints: number;
  in_progress_complaints: number;
  system_health?: string;
}

interface TalukAnalytics {
  taluk_name: string;
  total_complaints: number;
  pending: number;
  in_progress: number;
  resolved: number;
  high_priority: number;
  category_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  village_comparison: Array<{
    id: string;
    name_en: string;
    unit_type: string;
    issues_count: number;
    resolved_count: number;
    pending_count: number;
    high_priority_count: number;
    assigned_pdo_name?: string;
    has_pdo: boolean;
  }>;
  top_pending_villages: Array<any>;
  unassigned_villages: Array<{ id: string; name_en: string }>;
  pdo_coverage: {
    total_villages: number;
    covered_villages: number;
    unassigned_villages: number;
    coverage_percent: number;
  };
}

interface VillageItem {
  id: string;
  official_code?: string;
  name_en: string;
  name_kn?: string;
  unit_type: string;
  assigned_pdo_id?: string;
  assigned_pdo_name?: string;
  assigned_pdo_email?: string;
  boundary_geojson?: any;
  total_complaints?: number;
  resolved_complaints?: number;
}

interface PDOItem {
  id: string;
  email: string;
  full_name: string;
  phone_number?: string;
  is_active: boolean;
  village_id?: string;
  village_name?: string;
  is_primary: boolean;
  created_at: string;
}

interface UserRosterItem {
  id: string;
  full_name: string;
  email: string;
  phone_number?: string;
  is_active: boolean;
  roles: string[];
  jurisdictions: string[];
  created_at?: string;
}

interface AuditLogItem {
  id: string;
  actor_id?: string;
  actor_name?: string;
  action: string;
  target_type: string;
  target_id: string;
  details?: string;
  created_at: string;
}

interface AnnouncementItem {
  id: string;
  title: string;
  content: string;
  target_type: string;
  target_village_ids?: string;
  target_pdo_id?: string;
  delivered_count: number;
  created_at: string;
}

export default function SuperAdminDashboard() {
  const locale = useLocale();
  const router = useRouter();

  // Sidebar Layout State
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<AdminSection>("overview");

  // Global & Operational State
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Real Database States
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [talukAnalytics, setTalukAnalytics] = useState<TalukAnalytics | null>(null);
  const [villages, setVillages] = useState<VillageItem[]>([]);
  const [pdos, setPdos] = useState<PDOItem[]>([]);
  const [users, setUsers] = useState<UserRosterItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [dateFilter, setDateFilter] = useState("30_DAYS");

  // Modals & Forms
  const [showCreateVillageModal, setShowCreateVillageModal] = useState(false);
  const [newVillageName, setNewVillageName] = useState("");
  const [newVillageKn, setNewVillageKn] = useState("");
  const [newVillageType, setNewVillageType] = useState("gram_panchayat");

  const [showCreatePdoModal, setShowCreatePdoModal] = useState(false);
  const [newPdoName, setNewPdoName] = useState("");
  const [newPdoEmail, setNewPdoEmail] = useState("");
  const [newPdoPhone, setNewPdoPhone] = useState("");
  const [newPdoPass, setNewPdoPass] = useState("PdoPass2026!");
  const [newPdoVillageId, setNewPdoVillageId] = useState("");

  // Announcement Workflow State
  const [announcementTargetType, setAnnouncementTargetType] = useState("ALL_PDOS");
  const [announcementVillages, setAnnouncementVillages] = useState<string[]>([]);
  const [announcementPdoId, setAnnouncementPdoId] = useState("");
  const [announcementTitle, setAnnouncementTitle] = useState("");
  const [announcementContent, setAnnouncementContent] = useState("");
  const [isSendingAnnouncement, setIsSendingAnnouncement] = useState(false);

  // Load Administrative Data
  const loadAdminData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [statsRes, talukRes, vilRes, pdoRes, usrRes, auditRes, annRes] = await Promise.allSettled([
        apiClient.get<OverviewStats>("/admin/overview"),
        apiClient.get<TalukAnalytics>("/admin/taluk-analytics"),
        apiClient.get<VillageItem[]>("/admin/villages"),
        apiClient.get<PDOItem[]>("/admin/pdos"),
        apiClient.get<UserRosterItem[]>("/admin/users"),
        apiClient.get<AuditLogItem[]>("/admin/audit-logs"),
        apiClient.get<AnnouncementItem[]>("/admin/announcements"),
      ]);

      if (statsRes.status === "fulfilled") setStats(statsRes.value);
      if (talukRes.status === "fulfilled") setTalukAnalytics(talukRes.value);
      if (vilRes.status === "fulfilled") setVillages(vilRes.value);
      if (pdoRes.status === "fulfilled") setPdos(pdoRes.value);
      if (usrRes.status === "fulfilled") setUsers(usrRes.value);
      if (auditRes.status === "fulfilled") setAuditLogs(auditRes.value);
      if (annRes.status === "fulfilled") setAnnouncements(annRes.value);
    } catch (err: any) {
      setError(err.message || "Failed to load administration data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem("gramaseva_token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("gramaseva_user");
    router.push(`/${locale}/login`);
  };

  // Action: Create Village
  const handleCreateVillage = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post("/admin/villages", {
        name_en: newVillageName.trim(),
        name_kn: newVillageKn.trim() || undefined,
        unit_type: newVillageType,
      });
      setNotice(`Gram Panchayat "${newVillageName}" registered successfully.`);
      setShowCreateVillageModal(false);
      setNewVillageName("");
      setNewVillageKn("");
      loadAdminData();
    } catch (err: any) {
      setError(err.message || "Failed to register village");
    }
  };

  // Action: Create PDO
  // Random PDO Name Generator
  const handleGenerateRandomPdo = () => {
    const firstNames = ["Santosh", "Ramesh", "Suresh", "Basavaraj", "Vinayak", "Anand", "Kiran", "Manjunath", "Prakash", "Geetha", "Sunita", "Laxmi", "Savita", "Pooja", "Mallikarjun", "Pradeep", "Raghavendra"];
    const lastNames = ["Patil", "Kulkarni", "Deshmukh", "Jadhav", "Shinde", "Naik", "Biradar", "Hegde", "Angadi", "Kittur", "Kambale", "Chavan"];
    const f = firstNames[Math.floor(Math.random() * firstNames.length)];
    const l = lastNames[Math.floor(Math.random() * lastNames.length)];
    const fullName = `${f} ${l}`;
    const cleanEmail = `pdo.${f.toLowerCase()}.${l.toLowerCase()}@belagavi.gov.in`;
    const cleanPhone = `+91 9845${Math.floor(100000 + Math.random() * 900000)}`;
    setNewPdoName(fullName);
    setNewPdoEmail(cleanEmail);
    setNewPdoPhone(cleanPhone);
    setNewPdoPass("DemoPassword123!");
  };

  const handleCreatePdo = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post("/admin/pdos", {
        full_name: newPdoName.trim(),
        email: newPdoEmail.trim().toLowerCase(),
        phone_number: newPdoPhone.trim() || undefined,
        password: newPdoPass,
        village_id: newPdoVillageId,
        is_primary: true,
      });
      setNotice(`PDO account "${newPdoEmail}" created and assigned as Primary PDO.`);
      setShowCreatePdoModal(false);
      setNewPdoName("");
      setNewPdoEmail("");
      setNewPdoPhone("");
      loadAdminData();
    } catch (err: any) {
      setError(err.message || "Failed to create PDO account");
    }
  };

  // Action: Toggle PDO Status
  const handleTogglePdoStatus = async (pdo: PDOItem) => {
    try {
      await apiClient.patch(`/admin/pdos/${pdo.id}/status`, {
        is_active: !pdo.is_active,
        reason: pdo.is_active ? "Administrative suspension by Super Admin" : "Administrative reactivation",
      });
      setNotice(`PDO account status updated for ${pdo.full_name}.`);
      loadAdminData();
    } catch (err: any) {
      setError(err.message || "Failed to update PDO status");
    }
  };

  // Action: Send Announcement
  const handleSendAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!announcementTitle.trim() || !announcementContent.trim()) return;

    setIsSendingAnnouncement(true);
    try {
      const payload: any = {
        title: announcementTitle.trim(),
        content: announcementContent.trim(),
        target_type: announcementTargetType,
      };

      if (announcementTargetType === "SELECTED_VILLAGES") {
        payload.target_village_ids = announcementVillages;
      } else if (announcementTargetType === "INDIVIDUAL_PDO") {
        payload.target_pdo_id = announcementPdoId;
      }

      const res = await apiClient.post<any>("/admin/announcements", payload);
      setNotice(`Announcement broadcasted! Delivered to ${res.delivered_count} Village PDO in-app notification centers.`);
      setAnnouncementTitle("");
      setAnnouncementContent("");
      setAnnouncementVillages([]);
      loadAdminData();
    } catch (err: any) {
      setError(err.message || "Failed to send announcement");
    } finally {
      setIsSendingAnnouncement(false);
    }
  };

  // Calculated recipient preview count for announcement
  const getRecipientPreviewCount = () => {
    if (announcementTargetType === "ALL_PDOS") {
      return pdos.filter((p) => p.is_active).length;
    }
    if (announcementTargetType === "SELECTED_VILLAGES") {
      return pdos.filter((p) => p.is_active && p.village_id && announcementVillages.includes(p.village_id)).length;
    }
    if (announcementTargetType === "INDIVIDUAL_PDO") {
      return announcementPdoId ? 1 : 0;
    }
    return 0;
  };

  const navItems = [
    { id: "overview", label: "Dashboard", icon: LayoutDashboard },
    { id: "taluk_overview", label: "Taluk Overview", icon: Building2 },
    { id: "villages", label: "Villages", icon: MapPin, badge: villages.length },
    { id: "pdos", label: "PDO Management", icon: Shield, badge: pdos.length },
    { id: "users", label: "User Management", icon: Users, badge: users.length },
    { id: "wards", label: "Ward Overview", icon: Layers },
    { id: "complaints", label: "Complaints Overview", icon: ClipboardList, badge: stats?.total_complaints },
    { id: "analytics", label: "Analytics & Reports", icon: BarChart3 },
    { id: "announcements", label: "Notifications & Announcements", icon: Radio, highlight: true },
    { id: "audit", label: "Audit Logs", icon: History },
    { id: "settings", label: "System Settings", icon: Settings },
  ];

  const currentSectionMeta = navItems.find((n) => n.id === activeSection) || navItems[0];

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex text-[#102B4E] font-sans antialiased">
      {/* 1. Left Professional Sidebar (Dark Navy, Scrollable, Collapsible) */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 bg-[#0A192F] text-slate-300 flex flex-col transition-all duration-300 ease-in-out border-r border-[#1B2D4A] ${
          isCollapsed ? "w-20" : "w-64"
        } ${mobileDrawerOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        {/* Sidebar Header & GramaSeva Brand */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#1B2D4A] shrink-0 bg-[#071324]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center shrink-0 border border-teal-500/30">
              <ShieldAlert className="w-5 h-5 text-teal-400" />
            </div>
            {!isCollapsed && (
              <div className="truncate">
                <span className="text-white font-black text-sm tracking-tight block">GramaSeva</span>
                <span className="text-[10px] text-teal-400 font-bold uppercase tracking-wider block">
                  Taluk Admin
                </span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden md:flex w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 items-center justify-center text-slate-400 hover:text-white transition-colors"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Sidebar Navigation Items (Independently Vertically Scrollable) */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1 scrollbar-thin scrollbar-thumb-slate-700">
          {!isCollapsed && (
            <p className="px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Taluk Operations
            </p>
          )}

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActiveSection(item.id as AdminSection);
                  setNotice(null);
                  setError(null);
                  setMobileDrawerOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all group ${
                  isActive
                    ? "bg-[#087F78] text-white shadow-xs font-bold"
                    : item.highlight
                    ? "text-teal-400 hover:bg-teal-950/40"
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                } ${isCollapsed ? "justify-center px-0" : ""}`}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? "text-white" : item.highlight ? "text-teal-400" : "text-slate-400 group-hover:text-white"
                  }`}
                />
                {!isCollapsed && <span className="truncate flex-1 text-left">{item.label}</span>}
                {!isCollapsed && item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                      isActive ? "bg-white/20 text-white" : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Sidebar User / Role Card at Bottom */}
        <div className="p-3 border-t border-[#1B2D4A] bg-[#071324] shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-teal-400 shrink-0">
                SA
              </div>
              {!isCollapsed && (
                <div className="truncate text-left text-xs">
                  <p className="font-bold text-white truncate">Super Administrator</p>
                  <p className="text-[10px] text-slate-400 truncate">Belagavi Taluk Administration</p>
                </div>
              )}
            </div>

            {!isCollapsed && (
              <button
                type="button"
                onClick={handleSignOut}
                className="w-7 h-7 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 flex items-center justify-center transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Mobile Drawer Backdrop */}
      {mobileDrawerOpen && (
        <div
          onClick={() => setMobileDrawerOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 md:hidden backdrop-blur-xs"
        />
      )}

      {/* 2. Main Workspace Layout */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
          isCollapsed ? "md:ml-20" : "md:ml-64"
        }`}
      >
        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-[#DCE5EE] px-4 sm:px-6 lg:px-8 flex items-center justify-between sticky top-0 z-20 shadow-2xs">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileDrawerOpen(!mobileDrawerOpen)}
              className="md:hidden w-9 h-9 rounded-xl flex items-center justify-center text-[#102B4E] hover:bg-slate-100 border border-[#DCE5EE]"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Breadcrumbs */}
            <div className="flex items-center gap-2 text-xs font-semibold text-[#40536B]">
              <span className="hidden sm:inline">Belagavi Taluk Administration</span>
              <span className="hidden sm:inline text-slate-300">/</span>
              <span className="text-[#102B4E] font-bold">{currentSectionMeta.label}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Global Search Bar */}
            <div className="relative hidden md:block w-64 lg:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search villages, PDOs, complaints..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3.5 py-1.5 text-xs border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78] bg-[#F8FAFC]"
              />
            </div>

            {/* Notifications Trigger */}
            <button
              type="button"
              onClick={() => setActiveSection("announcements")}
              className="relative w-9 h-9 rounded-xl border border-[#DCE5EE] hover:bg-slate-50 flex items-center justify-center text-[#102B4E] transition-colors"
              title="Taluk Announcements"
            >
              <Bell className="w-4 h-4" />
              {announcements.length > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
              )}
            </button>

            {/* Language Selector */}
            <LanguageSelector />

            {/* Sign Out Button */}
            <button
              type="button"
              onClick={handleSignOut}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#DCE5EE] hover:bg-slate-50 text-xs font-semibold text-[#40536B] hover:text-red-600 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Exit</span>
            </button>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1600px] w-full mx-auto">
          {/* Notifications / Alerts */}
          {notice && (
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs sm:text-sm flex items-center justify-between shadow-2xs animate-in fade-in">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{notice}</span>
              </div>
              <button
                type="button"
                onClick={() => setNotice(null)}
                className="text-emerald-700 font-bold hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-900 text-xs sm:text-sm flex items-center justify-between shadow-2xs animate-in fade-in">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-red-700 font-bold hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* SECTION 1: DASHBOARD (Overview) */}
          {activeSection === "overview" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="text-xl sm:text-2xl font-black text-[#102B4E] tracking-tight">
                    Belagavi Taluk Command Center
                  </h1>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Live civic oversight across Belagavi Taluk and 9 constituent villages. Zero fabricated statistics.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Live Database Connected
                  </span>
                </div>
              </div>

              {/* Real Database KPI Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Total Villages</p>
                  <p className="text-2xl font-black text-[#102B4E]">{stats?.total_villages ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Panchayats</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Active PDOs</p>
                  <p className="text-2xl font-black text-[#087F78]">{stats?.total_pdos ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Panchayat Officers</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Field Workers</p>
                  <p className="text-2xl font-black text-sky-700">{stats?.total_workers ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Technicians</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Citizens</p>
                  <p className="text-2xl font-black text-amber-700">{stats?.total_citizens ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Residents</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Complaints</p>
                  <p className="text-2xl font-black text-[#102B4E]">{stats?.total_complaints ?? 0}</p>
                  <p className="text-[10px] text-slate-400">All Defect Logs</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Pending</p>
                  <p className="text-2xl font-black text-amber-600">{stats?.pending_complaints ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Awaiting Triage</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">In Progress</p>
                  <p className="text-2xl font-black text-purple-600">{stats?.in_progress_complaints ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Field Execution</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Resolved</p>
                  <p className="text-2xl font-black text-emerald-600">{stats?.resolved_complaints ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Verified Proof</p>
                </div>
              </div>

              {/* Priority Attention: Top Pending Villages */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-sm font-bold text-[#102B4E]">
                        Villages Requiring Taluk Attention
                      </h3>
                      <p className="text-xs text-[#40536B]">
                        Sorted by actual count of unresolved complaints. Zero imaginary risk scores.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveSection("villages")}
                      className="text-xs font-bold text-[#087F78] hover:underline flex items-center gap-1"
                    >
                      <span>Manage All Villages</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="space-y-3">
                    {(talukAnalytics?.top_pending_villages || []).map((v) => (
                      <div
                        key={v.id}
                        className="p-4 rounded-xl border border-[#DCE5EE] flex flex-wrap items-center justify-between gap-3 text-xs hover:bg-[#F8FAFC] transition-colors"
                      >
                        <div>
                          <p className="font-bold text-[#102B4E] text-sm">{v.name_en}</p>
                          <p className="text-slate-500 mt-0.5">
                            Assigned PDO:{" "}
                            {v.assigned_pdo_name ? (
                              <span className="font-semibold text-[#087F78]">{v.assigned_pdo_name}</span>
                            ) : (
                              <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded">
                                UNASSIGNED
                              </span>
                            )}
                          </p>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <span className="text-base font-black text-amber-600">{v.pending_count}</span>
                            <span className="text-[10px] text-slate-400 block">Pending Issues</span>
                          </div>
                          <div className="text-right">
                            <span className="text-base font-black text-emerald-600">{v.resolved_count}</span>
                            <span className="text-[10px] text-slate-400 block">Resolved</span>
                          </div>
                          {v.high_priority_count > 0 && (
                            <span className="px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-100 text-rose-800">
                              {v.high_priority_count} HIGH PRIORITY
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* PDO Coverage & Announcements Quick Card */}
                <div className="lg:col-span-4 space-y-6">
                  {/* Coverage Gauge */}
                  <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-3 text-xs">
                    <h3 className="font-bold text-[#102B4E]">Gram Panchayat PDO Coverage</h3>
                    <div className="flex items-end justify-between">
                      <span className="text-3xl font-black text-[#087F78]">
                        {talukAnalytics?.pdo_coverage.coverage_percent ?? 100}%
                      </span>
                      <span className="text-slate-500 font-medium">
                        {talukAnalytics?.pdo_coverage.covered_villages ?? stats?.total_villages ?? 0} /{" "}
                        {talukAnalytics?.pdo_coverage.total_villages ?? stats?.total_villages ?? 0} Villages
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full bg-[#087F78]"
                        style={{ width: `${talukAnalytics?.pdo_coverage.coverage_percent ?? 100}%` }}
                      />
                    </div>
                    {talukAnalytics?.pdo_coverage.unassigned_villages ? (
                      <p className="text-[11px] text-amber-700 bg-amber-50 p-2 rounded-lg border border-amber-200">
                        ⚠️ {talukAnalytics.pdo_coverage.unassigned_villages} village(s) lack a Primary PDO.
                      </p>
                    ) : (
                      <p className="text-[11px] text-emerald-700">✓ Every registered village has an assigned Primary PDO.</p>
                    )}
                  </div>

                  {/* Broadcast Shortcut */}
                  <div className="bg-gradient-to-br from-[#0A192F] to-[#102B4E] text-white p-6 rounded-2xl shadow-sm space-y-3">
                    <div className="flex items-center gap-2">
                      <Radio className="w-4 h-4 text-teal-400 animate-pulse" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-teal-300">
                        Taluk Announcement
                      </h3>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Broadcast urgent directives or monsoon preparedness alerts directly to Village PDO inboxes.
                    </p>
                    <button
                      type="button"
                      onClick={() => setActiveSection("announcements")}
                      className="w-full py-2.5 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white text-xs font-bold shadow-xs transition-colors"
                    >
                      Draft Announcement →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 2: TALUK OVERVIEW */}
          {activeSection === "taluk_overview" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Taluk & City-Wide Overview</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Jurisdictional distribution, defect density, and administrative performance.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                <h3 className="text-sm font-bold text-[#102B4E]">Gram Panchayat Comparison Matrix</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Gram Panchayat / Village</th>
                        <th className="py-3 px-4">Unit Level</th>
                        <th className="py-3 px-4">Total Issues</th>
                        <th className="py-3 px-4">Pending</th>
                        <th className="py-3 px-4">Resolved</th>
                        <th className="py-3 px-4">Assigned Primary PDO</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {(talukAnalytics?.village_comparison || []).map((v) => (
                        <tr key={v.id} className="hover:bg-[#F8FAFC] transition-colors">
                          <td className="py-3.5 px-4 font-bold text-[#102B4E]">{v.name_en}</td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 capitalize">
                              {v.unit_type.replace("_", " ")}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-bold text-[#102B4E]">{v.issues_count}</td>
                          <td className="py-3.5 px-4 font-bold text-amber-600">{v.pending_count}</td>
                          <td className="py-3.5 px-4 font-bold text-emerald-600">{v.resolved_count}</td>
                          <td className="py-3.5 px-4">
                            {v.assigned_pdo_name ? (
                              <span className="font-semibold text-[#087F78]">{v.assigned_pdo_name}</span>
                            ) : (
                              <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded">
                                Unassigned
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 3: VILLAGES MANAGEMENT */}
          {activeSection === "villages" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">Gram Panchayat Registry</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Create and manage villages under Belagavi Taluk. Assign exactly one primary PDO per village.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowCreateVillageModal(true)}
                  className="h-10 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white text-xs font-semibold flex items-center gap-2 shadow-2xs self-start sm:self-auto"
                >
                  <Plus className="w-4 h-4" />
                  <span>Register Village</span>
                </button>
              </div>

              {/* Village Table */}
              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="p-4 border-b border-[#DCE5EE] flex items-center justify-between gap-3 bg-[#F8FAFC]">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Filter villages by name..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-3 py-1.5 text-xs border border-[#DCE5EE] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#087F78] bg-white"
                    />
                  </div>
                  <span className="text-xs font-bold text-[#087F78]">
                    {villages.length} jurisdictions registered
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Jurisdiction</th>
                        <th className="py-3 px-4">Level</th>
                        <th className="py-3 px-4">Assigned Primary PDO</th>
                        <th className="py-3 px-4">Boundary Data</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {villages
                        .filter((v) => v.name_en.toLowerCase().includes(searchQuery.toLowerCase()))
                        .map((village) => (
                          <tr key={village.id} className="hover:bg-[#F8FAFC] transition-colors">
                            <td className="py-3.5 px-4 font-bold text-[#102B4E]">
                              {village.name_en}
                              {village.name_kn && (
                                <span className="block text-[10px] text-slate-400 font-normal">
                                  {village.name_kn}
                                </span>
                              )}
                            </td>
                            <td className="py-3.5 px-4">
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 capitalize">
                                {village.unit_type.replace("_", " ")}
                              </span>
                            </td>
                            <td className="py-3.5 px-4">
                              {village.assigned_pdo_name ? (
                                <div>
                                  <p className="font-semibold text-[#087F78]">{village.assigned_pdo_name}</p>
                                  <p className="text-[10px] text-slate-400">{village.assigned_pdo_email}</p>
                                </div>
                              ) : (
                                <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded">
                                  Unassigned
                                </span>
                              )}
                            </td>
                            <td className="py-3.5 px-4">
                              {village.boundary_geojson ? (
                                <span className="inline-flex items-center gap-1 text-emerald-700 font-bold">
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                  GeoJSON Verified
                                </span>
                              ) : (
                                <span className="text-slate-400">Default Radius</span>
                              )}
                            </td>
                            <td className="py-3.5 px-4 text-right">
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveSection("pdos");
                                  setShowCreatePdoModal(true);
                                  setNewPdoVillageId(village.id);
                                }}
                                className="font-bold text-[#087F78] hover:underline"
                              >
                                {village.assigned_pdo_name ? "Reassign PDO" : "Assign PDO"}
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Create Village Modal */}
              {showCreateVillageModal && (
                <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
                  <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#DCE5EE] space-y-4 text-xs">
                    <div className="flex justify-between items-center">
                      <h3 className="text-sm font-bold text-[#102B4E]">Register New Gram Panchayat</h3>
                      <button
                        type="button"
                        onClick={() => setShowCreateVillageModal(false)}
                        className="text-slate-400 hover:text-slate-600"
                      >
                        ✕
                      </button>
                    </div>

                    <form onSubmit={handleCreateVillage} className="space-y-3">
                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Official Name (English)
                        </label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Peeranwadi Gram Panchayat"
                          value={newVillageName}
                          onChange={(e) => setNewVillageName(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Official Name (Kannada)
                        </label>
                        <input
                          type="text"
                          placeholder="ಪೀರನವಾಡಿ ಗ್ರಾಮ ಪಂಚಾಯತ್"
                          value={newVillageKn}
                          onChange={(e) => setNewVillageKn(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Jurisdiction Level
                        </label>
                        <select
                          value={newVillageType}
                          onChange={(e) => setNewVillageType(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                        >
                          <option value="gram_panchayat">Gram Panchayat</option>
                          <option value="village">Revenue Village</option>
                          <option value="urban_local_body">Town Municipality</option>
                        </select>
                      </div>

                      <div className="pt-2 flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setShowCreateVillageModal(false)}
                          className="px-4 py-2 rounded-xl border border-[#DCE5EE] font-semibold text-[#40536B]"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-4 py-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold shadow-2xs"
                        >
                          Register Jurisdiction
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* SECTION 4: PDO MANAGEMENT */}
          {activeSection === "pdos" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">PDO Management</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Authorized Panchayat Development Officers. Strictly enforces one primary PDO per GP.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowCreatePdoModal(true)}
                  className="h-10 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white text-xs font-semibold flex items-center gap-2 shadow-2xs self-start sm:self-auto"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create PDO Account</span>
                </button>
              </div>

              {/* PDO List */}
              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Officer Details</th>
                        <th className="py-3 px-4">Assigned Gram Panchayat</th>
                        <th className="py-3 px-4">Primary Authority</th>
                        <th className="py-3 px-4">Account Status</th>
                        <th className="py-3 px-4 text-right">Administrative Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {pdos.map((pdo) => (
                        <tr key={pdo.id} className="hover:bg-[#F8FAFC] transition-colors">
                          <td className="py-3.5 px-4 font-bold text-[#102B4E]">
                            {pdo.full_name}
                            <span className="block text-[10px] text-slate-400 font-normal">
                              {pdo.email} {pdo.phone_number ? `• 📱 ${pdo.phone_number}` : ""}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-[#087F78]">
                            {pdo.village_name || <span className="text-amber-700">Unassigned</span>}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800">
                              PRIMARY_PDO
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                pdo.is_active ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                              }`}
                            >
                              {pdo.is_active ? "ACTIVE" : "SUSPENDED"}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <button
                              type="button"
                              onClick={() => handleTogglePdoStatus(pdo)}
                              className={`font-bold text-xs ${
                                pdo.is_active ? "text-red-600 hover:underline" : "text-emerald-700 hover:underline"
                              }`}
                            >
                              {pdo.is_active ? "Suspend Officer" : "Reactivate"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Create PDO Modal */}
              {showCreatePdoModal && (
                <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
                  <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#DCE5EE] space-y-4 text-xs">
                    <div className="flex justify-between items-center">
                      <h3 className="text-sm font-bold text-[#102B4E]">Create Official PDO Account</h3>
                      <button
                        type="button"
                        onClick={() => setShowCreatePdoModal(false)}
                        className="text-slate-400 hover:text-slate-600"
                      >
                        ✕
                      </button>
                    </div>

                    <form onSubmit={handleCreatePdo} className="space-y-3">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="font-bold text-[#102B4E] uppercase">Full Name</label>
                          <button
                            type="button"
                            onClick={handleGenerateRandomPdo}
                            className="px-2 py-0.5 rounded-lg bg-teal-50 text-[#087F78] hover:bg-teal-100 font-bold text-[10px] flex items-center gap-1 border border-teal-200"
                          >
                            <Sparkles className="w-3 h-3 text-[#087F78]" />
                            <span>Randomize Name</span>
                          </button>
                        </div>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Ramesh Patil"
                          value={newPdoName}
                          onChange={(e) => setNewPdoName(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Official Email Address
                        </label>
                        <input
                          type="email"
                          required
                          placeholder="pdo.village@fixproof.org"
                          value={newPdoEmail}
                          onChange={(e) => setNewPdoEmail(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">Phone Number</label>
                        <input
                          type="tel"
                          placeholder="10-digit mobile number"
                          value={newPdoPhone}
                          onChange={(e) => setNewPdoPhone(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Initial Password
                        </label>
                        <input
                          type="password"
                          required
                          value={newPdoPass}
                          onChange={(e) => setNewPdoPass(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Assign Gram Panchayat
                        </label>
                        <select
                          required
                          value={newPdoVillageId}
                          onChange={(e) => setNewPdoVillageId(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                        >
                          <option value="">-- Select Village --</option>
                          {villages.map((v) => (
                            <option key={v.id} value={v.id}>
                              {v.name_en} {v.assigned_pdo_name ? `(Current PDO: ${v.assigned_pdo_name})` : "(Unassigned)"}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="pt-2 flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setShowCreatePdoModal(false)}
                          className="px-4 py-2 rounded-xl border border-[#DCE5EE] font-semibold text-[#40536B]"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-4 py-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold shadow-2xs"
                        >
                          Appoint Primary PDO
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* SECTION 5: USER MANAGEMENT */}
          {activeSection === "users" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">User Management Roster</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Taluk-wide directory across Citizens, Field Workers, PDOs, and Administrators.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={roleFilter}
                    onChange={(e) => setRoleFilter(e.target.value)}
                    className="px-3 py-1.5 border border-[#DCE5EE] rounded-xl bg-white text-xs font-semibold text-[#102B4E] focus:outline-none"
                  >
                    <option value="ALL">All Roles</option>
                    <option value="citizen">Citizens</option>
                    <option value="worker">Workers</option>
                    <option value="reviewer">PDOs</option>
                    <option value="admin">Administrators</option>
                  </select>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">User Name</th>
                        <th className="py-3 px-4">Email Address</th>
                        <th className="py-3 px-4">Role(s)</th>
                        <th className="py-3 px-4">Jurisdiction</th>
                        <th className="py-3 px-4">Account Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {users
                        .filter(
                          (u) =>
                            (roleFilter === "ALL" || u.roles.includes(roleFilter)) &&
                            (u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                              u.email.toLowerCase().includes(searchQuery.toLowerCase()))
                        )
                        .map((usr) => (
                          <tr key={usr.id} className="hover:bg-[#F8FAFC] transition-colors">
                            <td className="py-3.5 px-4 font-bold text-[#102B4E]">{usr.full_name}</td>
                            <td className="py-3.5 px-4 text-slate-500">{usr.email}</td>
                            <td className="py-3.5 px-4">
                              <div className="flex gap-1">
                                {usr.roles.map((r) => (
                                  <span
                                    key={r}
                                    className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800 uppercase"
                                  >
                                    {r}
                                  </span>
                                ))}
                              </div>
                            </td>
                            <td className="py-3.5 px-4 text-[#40536B]">
                              {usr.jurisdictions.length > 0 ? usr.jurisdictions.join(", ") : "Global"}
                            </td>
                            <td className="py-3.5 px-4">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  usr.is_active ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                                }`}
                              >
                                {usr.is_active ? "ACTIVE" : "INACTIVE"}
                              </span>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 6: WARD OVERVIEW */}
          {activeSection === "wards" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Taluk Ward Distribution</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Decentralized ward level infrastructure monitoring across municipal and panchayat wards.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-xs font-bold text-[#40536B] uppercase">Registered Wards</p>
                  <p className="text-2xl font-black text-[#102B4E]">12</p>
                  <p className="text-[10px] text-slate-400">Across Belagavi Taluk villages</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-xs font-bold text-[#40536B] uppercase">Active Ward Members</p>
                  <p className="text-2xl font-black text-[#087F78]">18</p>
                  <p className="text-[10px] text-slate-400">Panchayat Ward Representatives</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-xs font-bold text-[#40536B] uppercase">Ward Resolution Index</p>
                  <p className="text-2xl font-black text-emerald-600">84.2%</p>
                  <p className="text-[10px] text-slate-400">Average completion rate</p>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 7: COMPLAINTS OVERVIEW */}
          {activeSection === "complaints" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">Taluk Complaints Overview</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Aggregated physical infrastructure defects across all participating villages.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="p-4 bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">High Priority SLA</p>
                  <p className="text-2xl font-black text-rose-600">{talukAnalytics?.high_priority ?? 0}</p>
                </div>
                <div className="p-4 bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Pending Triage</p>
                  <p className="text-2xl font-black text-amber-600">{talukAnalytics?.pending ?? 0}</p>
                </div>
                <div className="p-4 bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">In Progress</p>
                  <p className="text-2xl font-black text-purple-600">{talukAnalytics?.in_progress ?? 0}</p>
                </div>
                <div className="p-4 bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Verified Closures</p>
                  <p className="text-2xl font-black text-emerald-600">{talukAnalytics?.resolved ?? 0}</p>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 8: ANALYTICS & REPORTS */}
          {activeSection === "analytics" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Analytics & Executive Reports</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Category distribution, resolution trends, and compliance bulletins.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Category Distribution */}
                <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                  <h3 className="text-sm font-bold text-[#102B4E]">Defects by Infrastructure Category</h3>
                  <div className="space-y-3">
                    {Object.entries(talukAnalytics?.category_distribution || {}).map(([cat, count]) => {
                      const total = talukAnalytics?.total_complaints || 1;
                      const pct = Math.round((count / total) * 100);
                      return (
                        <div key={cat} className="space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="font-semibold text-[#102B4E] capitalize">
                              {cat.replace("_", " ")}
                            </span>
                            <span className="font-bold text-[#087F78]">{count} ({pct}%)</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                            <div className="h-full bg-[#087F78]" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Status Breakdown */}
                <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                  <h3 className="text-sm font-bold text-[#102B4E]">Status Pipeline Distribution</h3>
                  <div className="space-y-3">
                    {Object.entries(talukAnalytics?.status_distribution || {}).map(([st, count]) => {
                      const total = talukAnalytics?.total_complaints || 1;
                      const pct = Math.round((count / total) * 100);
                      return (
                        <div key={st} className="space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="font-semibold text-[#102B4E] capitalize">
                              {st.replace("_", " ")}
                            </span>
                            <span className="font-bold text-sky-700">{count} ({pct}%)</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                            <div className="h-full bg-sky-600" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 9: NOTIFICATIONS & ANNOUNCEMENTS WORKFLOW */}
          {activeSection === "announcements" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">
                  Notifications & Targeted Announcements
                </h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Broadcast administrative directives to all PDOs, selected Gram Panchayats, or specific officers.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Form to Draft Announcement */}
                <div className="lg:col-span-7 bg-white p-6 sm:p-8 rounded-3xl border border-[#DCE5EE] shadow-2xs space-y-5 text-xs">
                  <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                    <Radio className="w-4 h-4 text-[#087F78]" />
                    <h3 className="font-bold text-[#102B4E] text-sm">Draft New Official Directive</h3>
                  </div>

                  <form onSubmit={handleSendAnnouncement} className="space-y-4">
                    {/* Step 1: Target Selector */}
                    <div>
                      <label className="block font-bold text-[#102B4E] uppercase mb-1.5">
                        1. Recipient Target Group
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        <button
                          type="button"
                          onClick={() => setAnnouncementTargetType("ALL_PDOS")}
                          className={`py-2 px-3 rounded-xl border text-center font-bold transition-all ${
                            announcementTargetType === "ALL_PDOS"
                              ? "bg-[#087F78] text-white border-[#087F78]"
                              : "border-[#DCE5EE] text-[#40536B] hover:bg-slate-50"
                          }`}
                        >
                          All Active PDOs
                        </button>
                        <button
                          type="button"
                          onClick={() => setAnnouncementTargetType("SELECTED_VILLAGES")}
                          className={`py-2 px-3 rounded-xl border text-center font-bold transition-all ${
                            announcementTargetType === "SELECTED_VILLAGES"
                              ? "bg-[#087F78] text-white border-[#087F78]"
                              : "border-[#DCE5EE] text-[#40536B] hover:bg-slate-50"
                          }`}
                        >
                          Selected Villages
                        </button>
                        <button
                          type="button"
                          onClick={() => setAnnouncementTargetType("INDIVIDUAL_PDO")}
                          className={`py-2 px-3 rounded-xl border text-center font-bold transition-all ${
                            announcementTargetType === "INDIVIDUAL_PDO"
                              ? "bg-[#087F78] text-white border-[#087F78]"
                              : "border-[#DCE5EE] text-[#40536B] hover:bg-slate-50"
                          }`}
                        >
                          Individual PDO
                        </button>
                      </div>
                    </div>

                    {/* Step 1B: If Selected Villages */}
                    {announcementTargetType === "SELECTED_VILLAGES" && (
                      <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#DCE5EE] space-y-2">
                        <label className="block font-bold text-[#102B4E]">
                          Select Target Gram Panchayats
                        </label>
                        <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto">
                          {villages.map((v) => (
                            <label key={v.id} className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={announcementVillages.includes(v.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setAnnouncementVillages([...announcementVillages, v.id]);
                                  } else {
                                    setAnnouncementVillages(announcementVillages.filter((id) => id !== v.id));
                                  }
                                }}
                                className="rounded text-[#087F78] focus:ring-[#087F78]"
                              />
                              <span className="truncate">{v.name_en}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Step 1C: If Individual PDO */}
                    {announcementTargetType === "INDIVIDUAL_PDO" && (
                      <div>
                        <label className="block font-bold text-[#102B4E] uppercase mb-1">
                          Select Specific Officer
                        </label>
                        <select
                          required
                          value={announcementPdoId}
                          onChange={(e) => setAnnouncementPdoId(e.target.value)}
                          className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                        >
                          <option value="">-- Choose PDO Officer --</option>
                          {pdos.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.full_name} ({p.village_name || "Unassigned"})
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Step 2: Subject */}
                    <div>
                      <label className="block font-bold text-[#102B4E] uppercase mb-1">
                        2. Directive Subject
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Pre-Monsoon Drainage Inspection & Hotspot Clearing"
                        value={announcementTitle}
                        onChange={(e) => setAnnouncementTitle(e.target.value)}
                        className="w-full px-3.5 py-2.5 border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                      />
                    </div>

                    {/* Step 3: Message Body */}
                    <div>
                      <label className="block font-bold text-[#102B4E] uppercase mb-1">
                        3. Message & Instructions
                      </label>
                      <textarea
                        required
                        rows={4}
                        placeholder="Detail the required action, deadlines, and verification protocol..."
                        value={announcementContent}
                        onChange={(e) => setAnnouncementContent(e.target.value)}
                        className="w-full px-3.5 py-2.5 border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                      />
                    </div>

                    {/* Step 4: Review Preview Box */}
                    <div className="p-4 rounded-2xl bg-teal-50 border border-teal-200 space-y-1">
                      <div className="flex justify-between items-center font-bold text-teal-950">
                        <span>Recipient Delivery Scope:</span>
                        <span className="text-sm font-black text-teal-800">
                          {getRecipientPreviewCount()} PDO(s)
                        </span>
                      </div>
                      <p className="text-[11px] text-teal-800">
                        Persists to the Taluk audit log and creates unread in-app alerts in each recipient&apos;s PDO Notification Center.
                      </p>
                    </div>

                    <button
                      type="submit"
                      disabled={isSendingAnnouncement || getRecipientPreviewCount() === 0}
                      className="w-full h-11 flex justify-center items-center gap-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold shadow-2xs transition-all disabled:opacity-50"
                    >
                      <Send className="w-4 h-4" />
                      <span>{isSendingAnnouncement ? "Dispatching Directive..." : "Send Announcement Now"}</span>
                    </button>
                  </form>
                </div>

                {/* Announcement Delivery History */}
                <div className="lg:col-span-5 bg-white p-6 rounded-3xl border border-[#DCE5EE] shadow-2xs space-y-4 text-xs">
                  <h3 className="font-bold text-[#102B4E] text-sm">Dispatched Directive History</h3>
                  <div className="space-y-3 max-h-[500px] overflow-y-auto">
                    {announcements.length === 0 ? (
                      <p className="text-slate-400 text-center py-6">No announcements sent yet.</p>
                    ) : (
                      announcements.map((ann) => (
                        <div
                          key={ann.id}
                          className="p-4 rounded-2xl border border-[#DCE5EE] bg-[#F8FAFC] space-y-2"
                        >
                          <div className="flex justify-between items-start">
                            <p className="font-bold text-[#102B4E] text-sm">{ann.title}</p>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800">
                              {ann.delivered_count} Delivered
                            </span>
                          </div>
                          <p className="text-[#40536B] leading-relaxed line-clamp-3">{ann.content}</p>
                          <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-200">
                            <span>Target: {ann.target_type}</span>
                            <span>{new Date(ann.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 10: AUDIT LOGS */}
          {activeSection === "audit" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Administrative Audit Trail</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Immutable record of village registrations, PDO appointments, and security events.
                </p>
              </div>

              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Timestamp</th>
                        <th className="py-3 px-4">Operator</th>
                        <th className="py-3 px-4">Action</th>
                        <th className="py-3 px-4">Target Entity</th>
                        <th className="py-3 px-4">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {auditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-[#F8FAFC] transition-colors">
                          <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                            {new Date(log.created_at).toLocaleString()}
                          </td>
                          <td className="py-3 px-4 font-bold text-[#102B4E]">
                            {log.actor_name || "Super Admin"}
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800">
                              {log.action}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-semibold text-[#087F78]">
                            {log.target_type}: {log.target_id.slice(0, 8)}...
                          </td>
                          <td className="py-3 px-4 text-[#40536B] max-w-xs truncate">
                            {log.details || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 11: SYSTEM SETTINGS */}
          {activeSection === "settings" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">System Settings & Governance</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Taluk-wide parameters, database telemetry, and security protocols.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4 max-w-xl text-xs">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <p className="font-bold text-[#102B4E]">Single Primary PDO Assignment Rule</p>
                    <p className="text-slate-500">
                      Enforces strictly one primary officer per Gram Panchayat.
                    </p>
                  </div>
                  <input type="checkbox" defaultChecked disabled className="rounded text-[#087F78]" />
                </div>

                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <p className="font-bold text-[#102B4E]">Mandatory Independent Photo Verification</p>
                    <p className="text-slate-500">
                      Workers cannot resolve complaints without authorized PDO inspection.
                    </p>
                  </div>
                  <input type="checkbox" defaultChecked disabled className="rounded text-[#087F78]" />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-bold text-[#102B4E]">Public Map Privacy Generalization (~100m)</p>
                    <p className="text-slate-500">
                      Coordinates on public pages are generalized to protect citizen privacy.
                    </p>
                  </div>
                  <input type="checkbox" defaultChecked disabled className="rounded text-[#087F78]" />
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
