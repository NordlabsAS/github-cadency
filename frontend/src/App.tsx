import { useState, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { DateRangeContext, defaultFrom, defaultTo } from '@/hooks/useDateRange'
import { AuthContext, useAuthProvider } from '@/hooks/useAuth'
import ErrorBoundary from '@/components/ErrorBoundary'
import Layout from '@/components/Layout'
import SidebarLayout from '@/components/SidebarLayout'
import Dashboard from '@/pages/Dashboard'
import TeamRegistry from '@/pages/TeamRegistry'
import DeveloperDetail from '@/pages/DeveloperDetail'
import Repos from '@/pages/Repos'
import SyncPage from '@/pages/sync/SyncPage'
import SyncDetailPage from '@/pages/sync/SyncDetailPage'
import AIAnalysis from '@/pages/AIAnalysis'
import Goals from '@/pages/Goals'
import WorkloadOverview from '@/pages/insights/WorkloadOverview'
import CollaborationMatrix from '@/pages/insights/CollaborationMatrix'
import Benchmarks from '@/pages/insights/Benchmarks'
import IssueQuality from '@/pages/insights/IssueQuality'
import CodeChurn from '@/pages/insights/CodeChurn'
import CIInsights from '@/pages/insights/CIInsights'
import DoraMetrics from '@/pages/insights/DoraMetrics'
import Investment from '@/pages/insights/Investment'
import ExecutiveDashboard from '@/pages/ExecutiveDashboard'
import AISettingsPage from '@/pages/settings/AISettings'
import Login from '@/pages/Login'
import AuthCallback from '@/pages/AuthCallback'
import type { SidebarItem } from '@/components/SidebarLayout'

const insightsSidebarItems: SidebarItem[] = [
  { to: '/insights/workload', label: 'Workload' },
  { to: '/insights/collaboration', label: 'Collaboration' },
  { to: '/insights/benchmarks', label: 'Benchmarks' },
  { to: '/insights/issue-quality', label: 'Issue Quality' },
  { to: '/insights/code-churn', label: 'Code Churn' },
  { to: '/insights/cicd', label: 'CI/CD' },
  { to: '/insights/dora', label: 'DORA Metrics' },
  { to: '/insights/investment', label: 'Investment' },
]

const adminSidebarItems: SidebarItem[] = [
  { to: '/admin/repos', label: 'Repos' },
  { to: '/admin/sync', label: 'Sync' },
  { to: '/admin/ai', label: 'AI Analysis' },
  { to: '/admin/ai/settings', label: 'AI Settings' },
]

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('devpulse_token')
  const auth = useContext(AuthContext)
  if (!token) {
    return <Navigate to="/login" replace />
  }
  if (auth?.isLoading) {
    return null
  }
  return <>{children}</>
}

function AppRoutes() {
  const [dateFrom, setDateFrom] = useState(defaultFrom)
  const [dateTo, setDateTo] = useState(defaultTo)
  const auth = useAuthProvider()

  return (
    <AuthContext value={auth}>
      <DateRangeContext value={{ dateFrom, dateTo, setDateFrom, setDateTo }}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <ErrorBoundary>
                    <Routes>
                      <Route path="/" element={auth.isAdmin ? <Dashboard /> : <Navigate to={`/team/${auth.user?.developer_id}`} replace />} />
                      <Route path="/executive" element={auth.isAdmin ? <ExecutiveDashboard /> : <Navigate to="/" replace />} />
                      <Route path="/team" element={auth.isAdmin ? <TeamRegistry /> : <Navigate to="/" replace />} />
                      <Route path="/team/:id" element={<DeveloperDetail />} />
                      <Route path="/goals" element={<Goals />} />

                      {/* Insights — sidebar layout */}
                      <Route path="/insights/*" element={
                        auth.isAdmin ? (
                          <SidebarLayout items={insightsSidebarItems} title="Insights">
                            <Routes>
                              <Route path="/workload" element={<WorkloadOverview />} />
                              <Route path="/collaboration" element={<CollaborationMatrix />} />
                              <Route path="/benchmarks" element={<Benchmarks />} />
                              <Route path="/issue-quality" element={<IssueQuality />} />
                              <Route path="/code-churn" element={<CodeChurn />} />
                              <Route path="/cicd" element={<CIInsights />} />
                              <Route path="/dora" element={<DoraMetrics />} />
                              <Route path="/investment" element={<Investment />} />
                              <Route path="*" element={<Navigate to="/insights/workload" replace />} />
                            </Routes>
                          </SidebarLayout>
                        ) : <Navigate to="/" replace />
                      } />

                      {/* Admin — sidebar layout */}
                      <Route path="/admin/*" element={
                        auth.isAdmin ? (
                          <SidebarLayout items={adminSidebarItems} title="Admin">
                            <Routes>
                              <Route path="/repos" element={<Repos />} />
                              <Route path="/sync" element={<SyncPage />} />
                              <Route path="/sync/:id" element={<SyncDetailPage />} />
                              <Route path="/ai" element={<AIAnalysis />} />
                              <Route path="/ai/settings" element={<AISettingsPage />} />
                              <Route path="*" element={<Navigate to="/admin/repos" replace />} />
                            </Routes>
                          </SidebarLayout>
                        ) : <Navigate to="/" replace />
                      } />
                    </Routes>
                  </ErrorBoundary>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </DateRangeContext>
    </AuthContext>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
      <Toaster position="bottom-right" richColors duration={4000} />
    </QueryClientProvider>
  )
}
