import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import { AppShell as AppLayout } from './components/AppShell'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Dashboard from './pages/Dashboard'
import Opportunities from './pages/Opportunities'
import OpportunityDetail from './pages/OpportunityDetail'
import Pipeline from './pages/Pipeline'
import CompanyProfile from './pages/CompanyProfile'
import Scrapers from './pages/Scrapers'
import Settings from './pages/Settings'
import Analytics from './pages/Analytics'
import Chat from './pages/Chat'
import Admin from './pages/Admin'
import KnowledgeBase from './pages/KnowledgeBase'
import Proposals from './pages/Proposals'
import ProposalEditor from './pages/ProposalEditor'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/opportunities" element={<Opportunities />} />
                <Route path="/opportunities/:id" element={<OpportunityDetail />} />
                <Route path="/pipeline" element={<Pipeline />} />
                <Route path="/company" element={<CompanyProfile />} />
                <Route path="/scrapers" element={<Scrapers />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/admin" element={<Admin />} />
                <Route path="/knowledge" element={<KnowledgeBase />} />
                <Route path="/proposals" element={<Proposals />} />
                <Route path="/proposals/:id" element={<ProposalEditor />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
