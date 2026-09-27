import { type RouteObject, createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { AdminAuditPage } from "@/features/admin/pages/AdminAuditPage";
import { AdminCatalogPage } from "@/features/admin/pages/AdminCatalogPage";
import { AdminDashboardPage } from "@/features/admin/pages/AdminDashboardPage";
import { AdminInstitutionsPage } from "@/features/admin/pages/AdminInstitutionsPage";
import { AdminRulesPage } from "@/features/admin/pages/AdminRulesPage";
import { AdminUsersPage } from "@/features/admin/pages/AdminUsersPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { AIAuditPage } from "@/features/researcher/pages/AIAuditPage";
import { ComparePage } from "@/features/researcher/pages/ComparePage";
import { EpisodeDetailPage } from "@/features/researcher/pages/EpisodeDetailPage";
import { EpisodesPage } from "@/features/researcher/pages/EpisodesPage";
import { ExportPage } from "@/features/researcher/pages/ExportPage";
import { InterviewsPage } from "@/features/researcher/pages/InterviewsPage";
import { MemosPage } from "@/features/researcher/pages/MemosPage";
import { ResearcherDashboardPage } from "@/features/researcher/pages/ResearcherDashboardPage";
import { ResearcherSessionsPage } from "@/features/researcher/pages/ResearcherSessionsPage";
import { StatusPage } from "@/features/status/StatusPage";
import { ActivityPage } from "@/features/student/pages/ActivityPage";
import { StudentDashboardPage } from "@/features/student/pages/StudentDashboardPage";
import { StudentProgressPage } from "@/features/student/pages/StudentProgressPage";
import { StudentSessionPage } from "@/features/student/pages/StudentSessionPage";
import { TeacherDashboardPage } from "@/features/teacher/pages/TeacherDashboardPage";
import { TeacherSessionPage } from "@/features/teacher/pages/TeacherSessionPage";
import { AppShell } from "@/layouts/AppShell";
import { AuthLayout } from "@/layouts/AuthLayout";
import { NotFoundPage } from "@/layouts/NotFoundPage";

import { AnonymousOnly, RedirectToHome, RequireAuth, RequireRole } from "./guards";

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
              { path: "/teacher", element: <TeacherDashboardPage /> },
              { path: "/teacher/sessions/:sessionId", element: <TeacherSessionPage /> },
              { path: "/teacher/episodes", element: <EpisodesPage /> },
              { path: "/teacher/episodes/:episodeId", element: <EpisodeDetailPage /> },
              { path: "/teacher/export", element: <ExportPage /> },
              { path: "/teacher/*", element: <TeacherDashboardPage /> },
            ],
          },
          {
            element: <RequireRole roles={["RESEARCHER"]} />,
            children: [
              { path: "/researcher", element: <ResearcherDashboardPage /> },
              { path: "/researcher/sessions", element: <ResearcherSessionsPage /> },
              { path: "/researcher/episodes", element: <EpisodesPage /> },
              { path: "/researcher/episodes/:episodeId", element: <EpisodeDetailPage /> },
              { path: "/researcher/compare", element: <ComparePage /> },
              { path: "/researcher/memos", element: <MemosPage /> },
              { path: "/researcher/interviews", element: <InterviewsPage /> },
              { path: "/researcher/export", element: <ExportPage /> },
              { path: "/researcher/ai", element: <AIAuditPage /> },
              { path: "/researcher/*", element: <ResearcherDashboardPage /> },
            ],
          },
          {
            element: <RequireRole roles={["ADMIN"]} />,
            children: [
              { path: "/admin", element: <AdminDashboardPage /> },
              { path: "/admin/users", element: <AdminUsersPage /> },
              { path: "/admin/institutions", element: <AdminInstitutionsPage /> },
              { path: "/admin/audit", element: <AdminAuditPage /> },
              { path: "/admin/rules", element: <AdminRulesPage /> },
              { path: "/admin/catalog", element: <AdminCatalogPage /> },
              { path: "/admin/ai", element: <AIAuditPage /> },
              { path: "/admin/*", element: <AdminDashboardPage /> },
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
