import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { RiskAssessment, StalePR } from '@/utils/types'
import { riskLevelLabels, riskLevelStyles } from '@/utils/types'

const staleReasonLabels: Record<StalePR['stale_reason'], string> = {
  no_review: 'No Review',
  changes_requested_no_response: 'Changes Requested',
  approved_not_merged: 'Approved, Not Merged',
}

const staleReasonStyles: Record<StalePR['stale_reason'], string> = {
  no_review: 'bg-amber-500/10 text-amber-600',
  changes_requested_no_response: 'bg-red-500/10 text-red-600',
  approved_not_merged: 'bg-blue-500/10 text-blue-600',
}

function ageColor(hours: number): string {
  if (hours > 72) return 'bg-red-500/10 text-red-600'
  if (hours > 48) return 'bg-amber-500/10 text-amber-600'
  return 'bg-yellow-500/10 text-yellow-600'
}

function formatAge(hours: number): string {
  if (hours >= 24) return `${(hours / 24).toFixed(1)}d`
  return `${hours.toFixed(0)}h`
}

export default function StalePRsSection({
  prs,
  riskScores,
}: {
  prs: StalePR[]
  riskScores?: Record<number, RiskAssessment>
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Needs Attention</h2>
        <span className="text-sm text-muted-foreground">{prs.length} stale PR{prs.length !== 1 ? 's' : ''}</span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Pull Request</TableHead>
            <TableHead>Author</TableHead>
            <TableHead>Age</TableHead>
            <TableHead>Reason</TableHead>
            {riskScores && <TableHead>Risk</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {prs.map((pr) => (
            <TableRow key={pr.pr_id}>
              <TableCell>
                <div className="flex flex-col gap-0.5">
                  <a
                    href={pr.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-primary hover:underline"
                  >
                    #{pr.number} {pr.title}
                  </a>
                  <span className="text-xs text-muted-foreground">{pr.repo_name}</span>
                </div>
              </TableCell>
              <TableCell>
                {pr.author_id ? (
                  <Link
                    to={`/team/${pr.author_id}`}
                    className="text-sm hover:underline"
                  >
                    {pr.author_name ?? 'Unknown'}
                  </Link>
                ) : (
                  <span className="text-sm text-muted-foreground">{pr.author_name ?? 'External'}</span>
                )}
              </TableCell>
              <TableCell>
                <Badge variant="secondary" className={ageColor(pr.age_hours)}>
                  {formatAge(pr.age_hours)}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="secondary" className={staleReasonStyles[pr.stale_reason]}>
                  {staleReasonLabels[pr.stale_reason]}
                </Badge>
              </TableCell>
              {riskScores && (
                <TableCell>
                  {riskScores[pr.pr_id] ? (
                    <Badge
                      variant="secondary"
                      className={riskLevelStyles[riskScores[pr.pr_id].risk_level]}
                    >
                      {riskLevelLabels[riskScores[pr.pr_id].risk_level]}
                    </Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
