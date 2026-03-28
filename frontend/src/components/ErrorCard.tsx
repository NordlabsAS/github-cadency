import { AlertCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface ErrorCardProps {
  title?: string
  message?: string
  onRetry?: () => void
}

export default function ErrorCard({
  title = 'Something went wrong',
  message,
  onRetry,
}: ErrorCardProps) {
  return (
    <Card className="border-destructive/30">
      <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
        <AlertCircle className="size-10 text-destructive" />
        <div className="space-y-1">
          <h3 className="text-lg font-semibold">{title}</h3>
          {message && (
            <p className="text-sm text-muted-foreground">{message}</p>
          )}
        </div>
        {onRetry && (
          <Button variant="outline" onClick={onRetry}>
            Try Again
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
