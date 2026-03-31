import { TableHead } from '@/components/ui/table'

export default function SortableHead<T extends string>({
  field,
  current,
  asc,
  onToggle,
  children,
  className,
}: {
  field: T
  current: T
  asc: boolean
  onToggle: (f: T) => void
  children: React.ReactNode
  className?: string
}) {
  const active = field === current
  return (
    <TableHead className={className}>
      <button
        type="button"
        className="inline-flex items-center gap-1 hover:text-foreground"
        onClick={() => onToggle(field)}
      >
        {children}
        {active && (
          <span className="text-xs">{asc ? '\u2191' : '\u2193'}</span>
        )}
      </button>
    </TableHead>
  )
}
