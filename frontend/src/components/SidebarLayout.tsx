import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

export interface SidebarItem {
  to: string
  label: string
  icon?: ReactNode
}

interface SidebarLayoutProps {
  items: SidebarItem[]
  title: string
  children: ReactNode
}

export default function SidebarLayout({ items, title, children }: SidebarLayoutProps) {
  const { pathname } = useLocation()

  return (
    <div className="flex gap-6">
      <nav className="sticky top-20 h-fit w-48 shrink-0 space-y-1">
        <h2 className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h2>
        {items.map((item) => {
          const isActive = pathname === item.to || pathname.startsWith(item.to + '/')
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-muted text-foreground'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          )
        })}
      </nav>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}
