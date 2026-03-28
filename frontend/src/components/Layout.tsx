import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useDateRange } from '@/hooks/useDateRange'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import DateRangePicker from '@/components/DateRangePicker'

const adminNavItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/team', label: 'Team' },
  { to: '/repos', label: 'Repos' },
  { to: '/sync', label: 'Sync' },
  { to: '/ai', label: 'AI Analysis' },
]

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { dateFrom, dateTo, setDateFrom, setDateTo } = useDateRange()
  const { user, isAdmin, logout } = useAuth()

  const navItems = isAdmin
    ? adminNavItems
    : [
        { to: `/team/${user?.developer_id}`, label: 'My Stats' },
      ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            DevPulse
          </Link>
          <nav className="flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  location.pathname === item.to
                    ? 'bg-muted text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <DateRangePicker
              dateFrom={dateFrom}
              dateTo={dateTo}
              onDateFromChange={setDateFrom}
              onDateToChange={setDateTo}
            />
            {user && (
              <>
                <span className="text-muted-foreground">
                  {user.display_name}
                </span>
                <Button variant="ghost" size="sm" onClick={logout}>
                  Logout
                </Button>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  )
}
