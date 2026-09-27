import { type RouteObject, createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { AdminAuditPage } from "@/features/admin/pages/AdminAuditPage";
import { AdminDashboardPage } from "@/features/admin/pages/AdminDashboardPage";
import { AdminInstitutionsPage } from "@/features/admin/pages/AdminInstitutionsPage";
import { AdminUsersPage } from "@/features/admin/pages/AdminUsersPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { ResearcherDashboardPage } from "@/features/researcher/pages/ResearcherDashboardPage";
import { StatusPage } from "@/features/status/StatusPage";
import { StudentDashboardPage } from "@/features/student/pages/StudentDashboardPage";
import { TeacherDashboardPage } from "@/features/teacher/pages/TeacherDashboardPage";
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
          { element: <RequireRole roles={["STUDENT"]} />, children: [{ path: "/student/*", element: <StudentDashboardPage /> }] },
          { element: <RequireRole roles={["TEACHER"]} />, children: [{ path: "/teacher/*", element: <TeacherDashboardPage /> }] },
          {
            element: <RequireRole roles={["RESEARCHER"]} />,
            children: [{ path: "/researcher/*", element: <ResearcherDashboardPage /> }],
          },
          {
            element: <RequireRole roles={["ADMIN"]} />,
            children: [
              { path: "/admin", element: <AdminDashboardPage /> },
              { path: "/admin/users", element: <AdminUsersPage /> },
              { path: "/admin/institutions", element: <AdminInstitutionsPage /> },
              { path: "/admin/audit", element: <AdminAuditPage /> },
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
