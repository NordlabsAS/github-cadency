import { useEffect, useRef, useState } from 'react'
import { useTeams } from '@/hooks/useTeams'
import { cn } from '@/lib/utils'
import { Check, ChevronsUpDown } from 'lucide-react'

interface TeamComboboxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  id?: string
  /** When true, allows "All teams" empty option (for filter use) */
  allowEmpty?: boolean
  emptyLabel?: string
}

export default function TeamCombobox({
  value,
  onChange,
  placeholder = 'Select team...',
  id,
  allowEmpty = false,
  emptyLabel = 'All teams',
}: TeamComboboxProps) {
  const { data: teams = [] } = useTeams()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClick)
      return () => document.removeEventListener('mousedown', handleClick)
    }
  }, [open])

  const filtered = teams.filter(
    (t) => t.name.toLowerCase().includes(search.toLowerCase()),
  )
  const exactMatch = teams.some(
    (t) => t.name.toLowerCase() === search.toLowerCase(),
  )
  const showCreate = search.trim().length >= 2 && !exactMatch

  function handleSelect(name: string) {
    onChange(name)
    setSearch('')
    setOpen(false)
  }

  function handleClear() {
    onChange('')
    setSearch('')
    setOpen(false)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      setOpen(false)
      setSearch('')
    }
    if (e.key === 'Enter' && search.trim()) {
      e.preventDefault()
      // Select exact match, or create new
      const match = teams.find(
        (t) => t.name.toLowerCase() === search.toLowerCase(),
      )
      handleSelect(match ? match.name : search.trim())
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        id={id}
        className={cn(
          'flex h-8 w-full items-center justify-between rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors',
          'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50',
          !value && 'text-muted-foreground',
        )}
        onClick={() => {
          setOpen(!open)
          if (!open) {
            setTimeout(() => inputRef.current?.focus(), 0)
          }
        }}
      >
        <span className="truncate">{value || placeholder}</span>
        <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border bg-popover shadow-md">
          <div className="p-1.5">
            <input
              ref={inputRef}
              type="text"
              className="h-7 w-full rounded border-0 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground"
              placeholder="Search or create..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
          <div className="max-h-48 overflow-y-auto px-1 pb-1">
            {allowEmpty && (
              <button
                type="button"
                className={cn(
                  'flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent',
                  !value && 'font-medium',
                )}
                onClick={handleClear}
              >
                <Check className={cn('h-3.5 w-3.5', value ? 'opacity-0' : 'opacity-100')} />
                <span className="text-muted-foreground">{emptyLabel}</span>
              </button>
            )}
            {filtered.map((t) => (
              <button
                key={t.id}
                type="button"
                className={cn(
                  'flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent',
                  value === t.name && 'font-medium',
                )}
                onClick={() => handleSelect(t.name)}
              >
                <Check className={cn('h-3.5 w-3.5', value === t.name ? 'opacity-100' : 'opacity-0')} />
                {t.name}
              </button>
            ))}
            {showCreate && (
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm text-primary hover:bg-accent"
                onClick={() => handleSelect(search.trim())}
              >
                <span className="h-3.5 w-3.5 text-center text-xs font-bold">+</span>
                Create "{search.trim()}"
              </button>
            )}
            {filtered.length === 0 && !showCreate && (
              <div className="px-2 py-1.5 text-sm text-muted-foreground">
                No teams found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
