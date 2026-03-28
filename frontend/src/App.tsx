import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { DateRangeContext, defaultFrom, defaultTo } from '@/hooks/useDateRange'
import { AuthContext, useAuthProvider } from '@/hooks/useAuth'
import ErrorBoundary from '@/components/ErrorBoundary'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import TeamRegistry from '@/pages/TeamRegistry'
import DeveloperDetail from '@/pages/DeveloperDetail'
import Repos from '@/pages/Repos'
import SyncStatus from '@/pages/SyncStatus'
import AIAnalysis from '@/pages/AIAnalysis'
import Login from '@/pages/Login'
import AuthCallback from '@/pages/AuthCallback'

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
  if (!token) {
    return <Navigate to="/login" replace />
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
                      <Route path="/team" element={auth.isAdmin ? <TeamRegistry /> : <Navigate to="/" replace />} />
                      <Route path="/team/:id" element={<DeveloperDetail />} />
                      <Route path="/repos" element={auth.isAdmin ? <Repos /> : <Navigate to="/" replace />} />
                      <Route path="/sync" element={auth.isAdmin ? <SyncStatus /> : <Navigate to="/" replace />} />
                      <Route path="/ai" element={auth.isAdmin ? <AIAnalysis /> : <Navigate to="/" replace />} />
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
