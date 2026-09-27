import { type ReactNode, Suspense, lazy } from "react";
import { type RouteObject, createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { Skeleton } from "@/design-system/components";

import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { StatusPage } from "@/features/status/StatusPage";
import { ActivityPage } from "@/features/student/pages/ActivityPage";
import { StudentDashboardPage } from "@/features/student/pages/StudentDashboardPage";
import { StudentProgressPage } from "@/features/student/pages/StudentProgressPage";
import { StudentSessionPage } from "@/features/student/pages/StudentSessionPage";
import { AppShell } from "@/layouts/AppShell";
import { AuthLayout } from "@/layouts/AuthLayout";
import { NotFoundPage } from "@/layouts/NotFoundPage";

import { AnonymousOnly, RedirectToHome, RequireAuth, RequireRole } from "./guards";

// Dashboards de personal: se cargan bajo demanda (el estudiante no descarga su código).
const AdminAuditPage = lazy(() => import("@/features/admin/pages/AdminAuditPage").then((m) => ({ default: m.AdminAuditPage })));
const AdminCatalogPage = lazy(() => import("@/features/admin/pages/AdminCatalogPage").then((m) => ({ default: m.AdminCatalogPage })));
const AdminDashboardPage = lazy(() => import("@/features/admin/pages/AdminDashboardPage").then((m) => ({ default: m.AdminDashboardPage })));
const AdminInstitutionsPage = lazy(() => import("@/features/admin/pages/AdminInstitutionsPage").then((m) => ({ default: m.AdminInstitutionsPage })));
const AdminRulesPage = lazy(() => import("@/features/admin/pages/AdminRulesPage").then((m) => ({ default: m.AdminRulesPage })));
const AdminUsersPage = lazy(() => import("@/features/admin/pages/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })));
const AIAuditPage = lazy(() => import("@/features/researcher/pages/AIAuditPage").then((m) => ({ default: m.AIAuditPage })));
const ComparePage = lazy(() => import("@/features/researcher/pages/ComparePage").then((m) => ({ default: m.ComparePage })));
const EpisodeDetailPage = lazy(() => import("@/features/researcher/pages/EpisodeDetailPage").then((m) => ({ default: m.EpisodeDetailPage })));
const EpisodesPage = lazy(() => import("@/features/researcher/pages/EpisodesPage").then((m) => ({ default: m.EpisodesPage })));
const ExportPage = lazy(() => import("@/features/researcher/pages/ExportPage").then((m) => ({ default: m.ExportPage })));
const InterviewsPage = lazy(() => import("@/features/researcher/pages/InterviewsPage").then((m) => ({ default: m.InterviewsPage })));
const MemosPage = lazy(() => import("@/features/researcher/pages/MemosPage").then((m) => ({ default: m.MemosPage })));
const ResearcherDashboardPage = lazy(() => import("@/features/researcher/pages/ResearcherDashboardPage").then((m) => ({ default: m.ResearcherDashboardPage })));
const ResearcherSessionsPage = lazy(() => import("@/features/researcher/pages/ResearcherSessionsPage").then((m) => ({ default: m.ResearcherSessionsPage })));
const TeacherDashboardPage = lazy(() => import("@/features/teacher/pages/TeacherDashboardPage").then((m) => ({ default: m.TeacherDashboardPage })));
const TeacherSessionPage = lazy(() => import("@/features/teacher/pages/TeacherSessionPage").then((m) => ({ default: m.TeacherSessionPage })));

// eslint-disable-next-line react-refresh/only-export-components -- envoltorio local de Suspense
function Page({ children }: { children: ReactNode }) {
  return <Suspense fallback={<Skeleton height="12rem" label="Cargando" />}>{children}</Suspense>;
}

export const routes: RouteObject[] = [
  { path: "/", element: <RedirectToHome /> },
  { path: "/status", element: <StatusPage /> },
  {
    element: <AnonymousOnly />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
          { path: "/forgot-password", element: <ForgotPasswordPage /> },
          { path: "/reset-password", element: <ResetPasswordPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            element: <RequireRole roles={["STUDENT"]} />,
            children: [
              { path: "/student", element: <StudentDashboardPage /> },
              { path: "/student/sessions", element: <StudentDashboardPage /> },
              { path: "/student/sessions/:sessionId", element: <StudentSessionPage /> },
              { path: "/student/sessions/:sessionId/tasks/:taskId", element: <ActivityPage /> },
              { path: "/student/progress", element: <StudentProgressPage /> },
              { path: "/student/*", element: <StudentDashboardPage /> },
            ],
          },
          {
            element: <RequireRole roles={["TEACHER"]} />,
            children: [
              { path: "/teacher", element: <Page><TeacherDashboardPage /></Page> },
              { path: "/teacher/sessions/:sessionId", element: <Page><TeacherSessionPage /></Page> },
              { path: "/teacher/episodes", element: <Page><EpisodesPage /></Page> },
              { path: "/teacher/episodes/:episodeId", element: <Page><EpisodeDetailPage /></Page> },
              { path: "/teacher/export", element: <Page><ExportPage /></Page> },
              { path: "/teacher/*", element: <Page><TeacherDashboardPage /></Page> },
            ],
          },
          {
            element: <RequireRole roles={["RESEARCHER"]} />,
            children: [
              { path: "/researcher", element: <Page><ResearcherDashboardPage /></Page> },
              { path: "/researcher/sessions", element: <Page><ResearcherSessionsPage /></Page> },
              { path: "/researcher/episodes", element: <Page><EpisodesPage /></Page> },
              { path: "/researcher/episodes/:episodeId", element: <Page><EpisodeDetailPage /></Page> },
              { path: "/researcher/compare", element: <Page><ComparePage /></Page> },
              { path: "/researcher/memos", element: <Page><MemosPage /></Page> },
              { path: "/researcher/interviews", element: <Page><InterviewsPage /></Page> },
              { path: "/researcher/export", element: <Page><ExportPage /></Page> },
              { path: "/researcher/ai", element: <Page><AIAuditPage /></Page> },
              { path: "/researcher/*", element: <Page><ResearcherDashboardPage /></Page> },
            ],
          },
          {
            element: <RequireRole roles={["ADMIN"]} />,
            children: [
              { path: "/admin", element: <Page><AdminDashboardPage /></Page> },
              { path: "/admin/users", element: <Page><AdminUsersPage /></Page> },
              { path: "/admin/institutions", element: <Page><AdminInstitutionsPage /></Page> },
              { path: "/admin/audit", element: <Page><AdminAuditPage /></Page> },
              { path: "/admin/rules", element: <Page><AdminRulesPage /></Page> },
              { path: "/admin/catalog", element: <Page><AdminCatalogPage /></Page> },
              { path: "/admin/ai", element: <Page><AIAuditPage /></Page> },
              { path: "/admin/*", element: <Page><AdminDashboardPage /></Page> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const router = createBrowserRouter(routes);

/** Router en memoria para pruebas. */
export function createTestRouter(initialEntries: string[]) {
  return createMemoryRouter(routes, { initialEntries });
}
