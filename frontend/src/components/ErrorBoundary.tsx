import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { logger } from '@/utils/logger'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logger.error('ErrorBoundary caught', {
      error: error.message,
      stack: error.stack?.slice(0, 500),
      componentStack: info.componentStack?.slice(0, 500),
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mx-auto max-w-7xl px-4 py-12">
          <Card className="border-destructive/30">
            <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
              <AlertCircle className="size-10 text-destructive" />
              <div className="space-y-1">
                <h3 className="text-lg font-semibold">Something went wrong</h3>
                <p className="text-sm text-muted-foreground">
                  {this.state.error?.message ?? 'An unexpected error occurred.'}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => this.setState({ hasError: false, error: null })}
                >
                  Try Again
                </Button>
                <a href="/">
                  <Button variant="ghost">Go to Dashboard</Button>
                </a>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
