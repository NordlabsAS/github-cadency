import { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { toast } from 'sonner'
import { useDateRange } from '@/hooks/useDateRange'
import { useWorkAllocationItems, useRecategorizeItem } from '@/hooks/useStats'
import ErrorCard from '@/components/ErrorCard'
import TableSkeleton from '@/components/TableSkeleton'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChevronLeft, ExternalLink, GitPullRequest, CircleDot } from 'lucide-react'
import { FALLBACK_CATEGORY_CONFIG, FALLBACK_CATEGORY_ORDER } from '@/utils/categoryConfig'
import { useCategoryConfig } from '@/hooks/useWorkCategories'
import type { WorkCategory, WorkAllocationItem } from '@/utils/types'

const PAGE_SIZE = 25

export default function InvestmentCategory() {
  const { category } = useParams<{ category: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { dateFrom, dateTo } = useDateRange()
  const [page, setPage] = useState(1)
  const catConfig = useCategoryConfig()
  const CATEGORY_CONFIG = catConfig?.config ?? FALLBACK_CATEGORY_CONFIG
  const CATEGORY_ORDER = catConfig?.order ?? FALLBACK_CATEGORY_ORDER

  const typeFilter = (searchParams.get('type') || 'all') as 'pr' | 'issue' | 'all'

  // Reset page when date range changes
  const prevDateRef = useRef({ dateFrom, dateTo })
  useEffect(() => {
    if (prevDateRef.current.dateFrom !== dateFrom || prevDateRef.current.dateTo !== dateTo) {
      setPage(1)
      prevDateRef.current = { dateFrom, dateTo }
    }
  }, [dateFrom, dateTo])

  const { data, isLoading, isError, refetch } = useWorkAllocationItems(
    category || 'unknown',
    typeFilter,
    dateFrom,
    dateTo,
    page,
    PAGE_SIZE,
    !!category,
  )

  const recategorize = useRecategorizeItem()

  const config = CATEGORY_CONFIG[(category || 'unknown') as WorkCategory]
  const categoryLabel = config?.label ?? category

  function handleTypeChange(value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value === 'all') {
        next.delete('type')
      } else {
        next.set('type', value)
      }
      return next
    })
    setPage(1)
  }

  function handleRecategorize(item: WorkAllocationItem, newCategory: string) {
    recategorize.mutate(
      { itemType: item.type, itemId: item.id, category: newCategory },
      {
        onSuccess: () => {
          toast.success(`Recategorized #${item.number} as ${CATEGORY_CONFIG[newCategory as WorkCategory]?.label ?? newCategory}`)
        },
        onError: () => {
          toast.error('Failed to recategorize item')
        },
      },
    )
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  const sourceLabel = (source: string | null) => {
    switch (source) {
      case 'label': return 'Label'
      case 'title': return 'Title'
      case 'ai': return 'AI'
      case 'manual': return 'Manual'
      case 'cross_ref': return 'Linked issue'
      default: return 'Auto'
    }
  }

  const sourceBadgeVariant = (source: string | null) => {
    switch (source) {
      case 'manual': return 'default' as const
      case 'ai': return 'secondary' as const
      default: return 'outline' as const
    }
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb + Header */}
      <div>
        <Link
          to="/insights/investment"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2"
        >
          <ChevronLeft className="h-4 w-4" />
          Investment
        </Link>
        <div className="flex items-center gap-3">
          <div
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: config?.color ?? '#94a3b8' }}
          />
          <h1 className="text-2xl font-bold">{categoryLabel}</h1>
          {data && (
            <span className="text-sm text-muted-foreground">
              {data.total} {data.total === 1 ? 'item' : 'items'}
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={typeFilter} onValueChange={(v) => v && handleTypeChange(v)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All items</SelectItem>
            <SelectItem value="pr">PRs only</SelectItem>
            <SelectItem value="issue">Issues only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Content */}
      {isError && <ErrorCard message="Failed to load items." onRetry={refetch} />}

      {isLoading && <TableSkeleton rows={10} columns={6} />}

      {data && data.items.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No items found in this category for the selected period.
          </CardContent>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card>
          <CardContent className="pt-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">Type</TableHead>
                  <TableHead>Item</TableHead>
                  <TableHead>Repo</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Category</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((item) => (
                  <TableRow key={`${item.type}-${item.id}`}>
                    <TableCell>
                      {item.type === 'pr' ? (
                        <GitPullRequest className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <CircleDot className="h-4 w-4 text-muted-foreground" />
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5 min-w-0">
                        {item.html_url ? (
                          <a
                            href={item.html_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline truncate max-w-[320px] text-sm"
                          >
                            #{item.number} {item.title}
                          </a>
                        ) : (
                          <span className="truncate max-w-[320px] text-sm">
                            #{item.number} {item.title}
                          </span>
                        )}
                        {item.html_url && (
                          <a
                            href={item.html_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 text-muted-foreground hover:text-foreground"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      {item.labels && item.labels.length > 0 && (
                        <div className="flex gap-1 mt-0.5 flex-wrap">
                          {item.labels.slice(0, 3).map((label) => (
                            <Badge key={label} variant="outline" className="text-[10px] px-1 py-0">
                              {label}
                            </Badge>
                          ))}
                          {item.labels.length > 3 && (
                            <span className="text-[10px] text-muted-foreground">
                              +{item.labels.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {item.repo_name ?? '-'}
                    </TableCell>
                    <TableCell className="text-sm">
                      {item.author_id ? (
                        <Link
                          to={`/team/${item.author_id}`}
                          className="hover:underline text-muted-foreground"
                        >
                          {item.author_name}
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">{item.author_name ?? '-'}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={sourceBadgeVariant(item.category_source)}>
                        {sourceLabel(item.category_source)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground tabular-nums whitespace-nowrap">
                      {(item.merged_at || item.created_at)
                        ? new Date(item.merged_at || item.created_at!).toLocaleDateString()
                        : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <Select
                        value={item.category}
                        onValueChange={(v) => v && handleRecategorize(item, v)}
                      >
                        <SelectTrigger className="w-[130px] h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CATEGORY_ORDER.filter((c) => c !== 'unknown').map((cat) => (
                            <SelectItem key={cat} value={cat}>
                              <div className="flex items-center gap-1.5">
                                <div
                                  className="h-2 w-2 rounded-full"
                                  style={{ backgroundColor: CATEGORY_CONFIG[cat].color }}
                                />
                                {CATEGORY_CONFIG[cat].label}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <span className="text-sm text-muted-foreground">
                  Page {page} of {totalPages} ({data.total} items)
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
