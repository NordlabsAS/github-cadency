import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-5 w-10" />
        </div>
        <Skeleton className="mt-1 h-3 w-20" />
      </CardContent>
    </Card>
  )
}
