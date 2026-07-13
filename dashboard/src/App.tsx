import { Routes, Route } from "react-router-dom";

import DashboardLayout from "./components/layout/DashboardLayout";

import ProtectedRoute from "./components/auth/ProtectedRoute";

import LoginPage from "./pages/LoginPage";

import DashboardPage from "./pages/DashboardPage";

import PatientsPage from "./pages/PatientsPage";

import SamplesPage from "./pages/SamplesPage";

import PipelinePage from "./pages/PipelinePage";

import ReportsPage from "./pages/ReportsPage";

import ReportDetailPage from "./pages/ReportDetailPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";

import VariantsPage from "./pages/VariantsPage";

import SettingsPage from "./pages/SettingsPage";

import AuditPage from "./pages/AuditPage";



export default function App() {

  return (

    <Routes>

      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>

        <Route element={<DashboardLayout />}>

          <Route index element={<DashboardPage />} />

          <Route path="patients" element={<PatientsPage />} />

          <Route path="samples" element={<SamplesPage />} />

          <Route path="pipeline" element={<PipelinePage />} />

          <Route path="reports" element={<ReportsPage />} />

          <Route path="reports/:id" element={<ReportDetailPage />} />

          <Route path="review" element={<ReviewQueuePage />} />

          <Route path="variants" element={<VariantsPage />} />

          <Route path="settings" element={<SettingsPage />} />

          <Route path="audit" element={<AuditPage />} />

        </Route>

      </Route>

    </Routes>

  );

}

