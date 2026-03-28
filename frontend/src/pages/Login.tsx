import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'

export default function Login() {
  const { user, isLoading, login } = useAuth()
  const [loading, setLoading] = useState(false)

  // Already logged in — redirect
  if (!isLoading && user) {
    return <Navigate to="/" replace />
  }

  const handleLogin = async () => {
    setLoading(true)
    try {
      await login()
    } catch {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">DevPulse</CardTitle>
          <CardDescription>
            Sign in with your GitHub account to access your engineering metrics.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            className="w-full"
            onClick={handleLogin}
            disabled={loading || isLoading}
          >
            {loading ? 'Redirecting...' : 'Login with GitHub'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
