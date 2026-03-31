import { useState, useCallback } from 'react'
import {
  useWorkCategories,
  useCreateWorkCategory,
  useUpdateWorkCategory,
  useDeleteWorkCategory,
  useWorkCategoryRules,
  useCreateWorkCategoryRule,
  useUpdateWorkCategoryRule,
  useDeleteWorkCategoryRule,
  useReclassify,
  useScanSuggestions,
  useBulkCreateRules,
} from '@/hooks/useWorkCategories'
import type { WorkCategoryDef, WorkCategoryRuleDef, WorkCategorySuggestion } from '@/hooks/useWorkCategories'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Skeleton } from '@/components/ui/skeleton'
import ErrorCard from '@/components/ErrorCard'
import { Plus, Pencil, Trash2, RefreshCw, ChevronDown, HelpCircle, Search, Check, X } from 'lucide-react'

// --- Helper: info tooltip ---

function InfoTip({ children }: { children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger className="inline-flex text-muted-foreground/60 hover:text-muted-foreground transition-colors ml-1">
        <HelpCircle className="h-3.5 w-3.5" />
      </TooltipTrigger>
      <TooltipContent>{children}</TooltipContent>
    </Tooltip>
  )
}

// --- Category Dialog ---

function CategoryDialog({
  initial,
  categories,
  onSave,
  isPending,
  trigger,
}: {
  initial?: WorkCategoryDef
  categories: WorkCategoryDef[]
  onSave: (data: { category_key: string; display_name: string; description: string | null; color: string; exclude_from_stats: boolean }) => void
  isPending: boolean
  trigger: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [key, setKey] = useState(initial?.category_key ?? '')
  const [displayName, setDisplayName] = useState(initial?.display_name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [color, setColor] = useState(initial?.color ?? '#3b82f6')
  const [exclude, setExclude] = useState(initial?.exclude_from_stats ?? false)

  const isEdit = !!initial
  const canSubmit = key.length >= 2 && displayName.length >= 1 && /^#[0-9a-fA-F]{6}$/.test(color)

  function reset() {
    setKey(initial?.category_key ?? '')
    setDisplayName(initial?.display_name ?? '')
    setDescription(initial?.description ?? '')
    setColor(initial?.color ?? '#3b82f6')
    setExclude(initial?.exclude_from_stats ?? false)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset() }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Category' : 'New Category'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Key</Label>
            <Input
              value={key}
              onChange={(e) => setKey(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
              disabled={isEdit}
              placeholder="e.g. epic, security, design"
            />
            <p className="text-xs text-muted-foreground mt-1">Unique identifier. Lowercase letters, numbers, underscores. Cannot be changed after creation.</p>
          </div>
          <div>
            <Label>Display Name</Label>
            <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="e.g. Epic" />
            <p className="text-xs text-muted-foreground mt-1">Shown in charts, tables, and dropdowns throughout DevPulse.</p>
          </div>
          <div>
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. New functionality or enhancements that add user-facing value."
              rows={2}
            />
            <p className="text-xs text-muted-foreground mt-1">Help your team understand what belongs in this category.</p>
          </div>
          <div className="flex items-center gap-3">
            <Label>Color</Label>
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-8 w-12 rounded border cursor-pointer" />
            <Input value={color} onChange={(e) => setColor(e.target.value)} className="w-28 font-mono text-sm" />
          </div>
          <div className="flex items-center gap-3">
            <Switch
              checked={exclude}
              onCheckedChange={setExclude}
              disabled={isEdit && initial?.category_key === 'unknown'}
            />
            <div>
              <Label>Exclude from stats</Label>
              <p className="text-xs text-muted-foreground">When enabled, items in this category won't count toward cycle time, velocity, benchmarks, or investment metrics.</p>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            disabled={!canSubmit || isPending}
            onClick={() => {
              onSave({ category_key: key, display_name: displayName, description: description || null, color, exclude_from_stats: exclude })
              setOpen(false)
            }}
          >
            {isEdit ? 'Save' : 'Create'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// --- Rule Dialog ---

const MATCH_TYPE_INFO: Record<string, { label: string; description: string; placeholder: string }> = {
  label: {
    label: 'Label',
    description: 'Matches a GitHub label on the PR or issue. Compared exactly (case-insensitive by default).',
    placeholder: 'e.g. bug, enhancement, epic',
  },
  issue_type: {
    label: 'Issue Type',
    description: 'Matches the GitHub issue type (e.g. Bug, Epic, Feature, Task). Only applies to issues — PRs do not have types. Requires your GitHub repo to have issue types enabled.',
    placeholder: 'e.g. Bug, Epic, Feature, Task',
  },
  title_regex: {
    label: 'Title Regex',
    description: 'A regular expression tested against the PR or issue title. Use \\b for word boundaries. Matched anywhere in the title.',
    placeholder: 'e.g. \\bepic\\b|\\bfeature\\b',
  },
  prefix: {
    label: 'Title Prefix',
    description: 'Matches if the PR or issue title starts with this text (case-insensitive by default).',
    placeholder: 'e.g. [EPIC], fix:, feat:',
  },
}

function RuleDialog({
  initial,
  categories,
  onSave,
  isPending,
  trigger,
}: {
  initial?: WorkCategoryRuleDef
  categories: WorkCategoryDef[]
  onSave: (data: Omit<WorkCategoryRuleDef, 'id'>) => void
  isPending: boolean
  trigger: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [matchType, setMatchType] = useState<string>(initial?.match_type ?? 'label')
  const [matchValue, setMatchValue] = useState(initial?.match_value ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [caseSensitive, setCaseSensitive] = useState(initial?.case_sensitive ?? false)
  const [categoryKey, setCategoryKey] = useState(initial?.category_key ?? '')
  const [priority, setPriority] = useState(initial?.priority ?? 50)

  const canSubmit = matchValue.length >= 1 && categoryKey.length >= 1

  const matchInfo = MATCH_TYPE_INFO[matchType] ?? MATCH_TYPE_INFO.label

  function reset() {
    setMatchType(initial?.match_type ?? 'label')
    setMatchValue(initial?.match_value ?? '')
    setDescription(initial?.description ?? '')
    setCaseSensitive(initial?.case_sensitive ?? false)
    setCategoryKey(initial?.category_key ?? '')
    setPriority(initial?.priority ?? 50)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset() }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Rule' : 'New Rule'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Match Type</Label>
            <Select value={matchType} onValueChange={setMatchType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="label">Label</SelectItem>
                <SelectItem value="issue_type">Issue Type</SelectItem>
                <SelectItem value="title_regex">Title Regex</SelectItem>
                <SelectItem value="prefix">Title Prefix</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">{matchInfo.description}</p>
          </div>
          <div>
            <Label>Match Value</Label>
            <Input
              value={matchValue}
              onChange={(e) => setMatchValue(e.target.value)}
              placeholder={matchInfo.placeholder}
              className="font-mono text-sm"
            />
          </div>
          <div>
            <Label>Description <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Catches GitHub 'bug' label from triage workflow"
            />
            <p className="text-xs text-muted-foreground mt-1">A note to help your team understand why this rule exists.</p>
          </div>
          <div>
            <Label>Category</Label>
            <Select value={categoryKey} onValueChange={setCategoryKey}>
              <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
              <SelectContent>
                {categories.map((cat) => (
                  <SelectItem key={cat.category_key} value={cat.category_key}>
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                      {cat.display_name}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">The work category assigned when this rule matches.</p>
          </div>
          <div>
            <Label>
              Priority
              <InfoTip>Lower numbers are evaluated first. When multiple rules could match the same item, the lowest-priority rule wins. Convention: labels 1-50, issue types 51-99, title rules 100+.</InfoTip>
            </Label>
            <Input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
              min={1}
            />
          </div>
          <div className="flex items-center gap-3">
            <Switch checked={caseSensitive} onCheckedChange={setCaseSensitive} />
            <div>
              <Label>Case sensitive</Label>
              <p className="text-xs text-muted-foreground">When off, matching ignores uppercase/lowercase differences.</p>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            disabled={!canSubmit || isPending}
            onClick={() => {
              onSave({
                match_type: matchType as WorkCategoryRuleDef['match_type'],
                match_value: matchValue,
                description: description || null,
                case_sensitive: caseSensitive,
                category_key: categoryKey,
                priority,
              })
              setOpen(false)
            }}
          >
            {initial ? 'Save' : 'Create'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// --- Match type badge ---

const MATCH_TYPE_LABELS: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  label: { label: 'Label', variant: 'default' },
  issue_type: { label: 'Issue Type', variant: 'destructive' },
  title_regex: { label: 'Regex', variant: 'secondary' },
  prefix: { label: 'Prefix', variant: 'outline' },
}

// --- Suggestions Card ---

function SuggestionsCard({ categories }: { categories: WorkCategoryDef[] }) {
  const scanMutation = useScanSuggestions()
  const bulkCreate = useBulkCreateRules()
  const [suggestions, setSuggestions] = useState<(WorkCategorySuggestion & { _category: string })[]>([])
  const [scanned, setScanned] = useState(false)

  const handleScan = useCallback(() => {
    scanMutation.mutate(undefined, {
      onSuccess: (data) => {
        setSuggestions(data.map((s) => ({ ...s, _category: s.suggested_category })))
        setScanned(true)
      },
    })
  }, [scanMutation])

  const dismiss = useCallback((index: number) => {
    setSuggestions((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const updateCategory = useCallback((index: number, categoryKey: string) => {
    setSuggestions((prev) => prev.map((s, i) => i === index ? { ...s, _category: categoryKey } : s))
  }, [])

  const approveOne = useCallback((index: number) => {
    const s = suggestions[index]
    if (!s) return
    const priority = s.match_type === 'label' ? 45 : 55
    bulkCreate.mutate(
      [{
        match_type: s.match_type,
        match_value: s.match_value,
        category_key: s._category,
        priority,
        case_sensitive: false,
        description: null,
      }],
      { onSuccess: () => dismiss(index) },
    )
  }, [suggestions, bulkCreate, dismiss])

  const approveAll = useCallback(() => {
    if (suggestions.length === 0) return
    const rules = suggestions.map((s) => ({
      match_type: s.match_type,
      match_value: s.match_value,
      category_key: s._category,
      priority: s.match_type === 'label' ? 45 : 55,
      case_sensitive: false,
      description: null,
    }))
    bulkCreate.mutate(rules, {
      onSuccess: () => {
        setSuggestions([])
      },
    })
  }, [suggestions, bulkCreate])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>GitHub Suggestions</CardTitle>
          <CardDescription>
            Scan your synced GitHub data to discover labels and issue types that don't have classification rules yet.
          </CardDescription>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={handleScan}
          disabled={scanMutation.isPending}
        >
          <Search className={`h-4 w-4 mr-1 ${scanMutation.isPending ? 'animate-pulse' : ''}`} />
          {scanMutation.isPending ? 'Scanning...' : 'Scan GitHub Data'}
        </Button>
      </CardHeader>
      <CardContent>
        {!scanned && !scanMutation.isPending && (
          <p className="text-sm text-muted-foreground text-center py-6">
            Click "Scan GitHub Data" to discover uncovered labels and issue types from your synced PRs and issues.
          </p>
        )}
        {scanned && suggestions.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-6">
            All labels and issue types are covered by existing rules.
          </p>
        )}
        {suggestions.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-muted-foreground">
                {suggestions.length} uncovered value{suggestions.length === 1 ? '' : 's'} found. Review the suggested categories and approve to create rules.
              </p>
              <Button
                size="sm"
                onClick={approveAll}
                disabled={bulkCreate.isPending}
              >
                <Check className="h-4 w-4 mr-1" />
                Approve All ({suggestions.length})
              </Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead className="text-right">Usage</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {suggestions.map((s, i) => {
                  const matchInfo = MATCH_TYPE_LABELS[s.match_type] ?? { label: s.match_type, variant: 'outline' as const }
                  return (
                    <TableRow key={`${s.match_type}-${s.match_value}`}>
                      <TableCell>
                        <Badge variant={matchInfo.variant}>{matchInfo.label}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{s.match_value}</TableCell>
                      <TableCell className="text-right tabular-nums">{s.usage_count}</TableCell>
                      <TableCell>
                        <Select value={s._category} onValueChange={(v) => updateCategory(i, v)}>
                          <SelectTrigger className="w-[160px] h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {categories.map((cat) => (
                              <SelectItem key={cat.category_key} value={cat.category_key}>
                                <span className="flex items-center gap-2">
                                  <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                                  {cat.display_name}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-green-600 hover:text-green-700 hover:bg-green-50"
                                onClick={() => approveOne(i)}
                                disabled={bulkCreate.isPending}
                              >
                                <Check className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Create rule</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                onClick={() => dismiss(i)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Dismiss</TooltipContent>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// --- Main page ---

export default function WorkCategoriesPage() {
  const { data: categories, isLoading: catsLoading, isError: catsError, refetch: refetchCats } = useWorkCategories()
  const { data: rules, isLoading: rulesLoading, isError: rulesError, refetch: refetchRules } = useWorkCategoryRules()
  const createCat = useCreateWorkCategory()
  const updateCat = useUpdateWorkCategory()
  const deleteCat = useDeleteWorkCategory()
  const createRule = useCreateWorkCategoryRule()
  const updateRule = useUpdateWorkCategoryRule()
  const deleteRule = useDeleteWorkCategoryRule()
  const reclassify = useReclassify()
  const [howItWorksOpen, setHowItWorksOpen] = useState(false)

  if (catsError || rulesError) {
    return <ErrorCard message="Failed to load work categories" onRetry={() => { refetchCats(); refetchRules() }} />
  }

  if (catsLoading || rulesLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const cats = categories ?? []
  const rulesList = rules ?? []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Work Categories</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Define how PRs and issues are classified into work categories. Categories power the Investment breakdown, work allocation drill-down, and activity summaries across DevPulse.
        </p>
      </div>

      {/* How it works */}
      <Card>
        <CardHeader
          className="cursor-pointer select-none flex flex-row items-center justify-between"
          onClick={() => setHowItWorksOpen(!howItWorksOpen)}
        >
          <CardTitle className="text-base">How classification works</CardTitle>
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${howItWorksOpen ? 'rotate-180' : ''}`} />
        </CardHeader>
        {howItWorksOpen && (
          <CardContent className="pt-0">
            <div className="text-sm text-muted-foreground space-y-3">
              <p>
                Every PR and issue is automatically classified into a work category during sync. The classification engine evaluates rules in <strong className="text-foreground">priority order</strong> (lowest number first) and assigns the first matching category:
              </p>
              <ol className="list-decimal list-inside space-y-1.5 ml-1">
                <li><strong className="text-foreground">Label rules</strong> — match against GitHub labels on the item (e.g., a "bug" label maps to Bug Fix)</li>
                <li><strong className="text-foreground">Issue Type rules</strong> — match the GitHub issue type (e.g., Bug, Epic, Feature, Task). Only applies to issues.</li>
                <li><strong className="text-foreground">Title Regex rules</strong> — match a regular expression against the title</li>
                <li><strong className="text-foreground">Title Prefix rules</strong> — match the beginning of the title (e.g., "[EPIC]")</li>
                <li><strong className="text-foreground">Cross-reference</strong> — if a PR is still "Unknown" but links to a classified issue, it inherits that category</li>
                <li><strong className="text-foreground">AI classification</strong> — optional, when enabled in AI Settings</li>
                <li>Items that don't match any rule are classified as <strong className="text-foreground">Unknown</strong></li>
              </ol>
              <p>
                <strong className="text-foreground">Manual overrides</strong> (set via the Investment drill-down) are never overwritten by rules or reclassification.
              </p>
              <p>
                <strong className="text-foreground">When to reclassify:</strong> After adding, editing, or deleting rules, existing items keep their old categories until you click "Reclassify All" below or run a new sync.
              </p>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Categories */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Categories</CardTitle>
            <CardDescription>
              Each category represents a type of work. Items are grouped by category in charts and metrics.
            </CardDescription>
          </div>
          <CategoryDialog
            categories={cats}
            onSave={(data) => createCat.mutate(data)}
            isPending={createCat.isPending}
            trigger={<Button size="sm"><Plus className="h-4 w-4 mr-1" /> Add Category</Button>}
          />
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Color</TableHead>
                <TableHead>
                  Exclude from Stats
                  <InfoTip>When enabled, items in this category are hidden from cycle time, velocity, benchmarks, and investment metrics. Useful for categories like "ops" or "docs" that shouldn't affect engineering velocity.</InfoTip>
                </TableHead>
                <TableHead>
                  Order
                  <InfoTip>Controls the display order in charts, legends, and dropdowns. Lower numbers appear first.</InfoTip>
                </TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cats.map((cat) => (
                <TableRow key={cat.category_key}>
                  <TableCell>
                    <div>
                      <span className="font-medium">{cat.display_name}</span>
                      {cat.is_default && <Badge variant="secondary" className="ml-2 text-xs">Default</Badge>}
                      <div className="text-xs text-muted-foreground font-mono">{cat.category_key}</div>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[300px]">
                    <span className="text-sm text-muted-foreground">{cat.description || '—'}</span>
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-4 h-4 rounded-full border" style={{ backgroundColor: cat.color }} />
                      <span className="font-mono text-xs text-muted-foreground">{cat.color}</span>
                    </span>
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={cat.exclude_from_stats}
                      disabled={cat.category_key === 'unknown'}
                      onCheckedChange={(checked) => updateCat.mutate({ key: cat.category_key, exclude_from_stats: checked })}
                    />
                  </TableCell>
                  <TableCell>{cat.display_order}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <CategoryDialog
                        initial={cat}
                        categories={cats}
                        onSave={(data) => updateCat.mutate({ key: cat.category_key, display_name: data.display_name, description: data.description, color: data.color, exclude_from_stats: data.exclude_from_stats })}
                        isPending={updateCat.isPending}
                        trigger={
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                        }
                      />
                      {!cat.is_default && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive"
                          onClick={() => deleteCat.mutate(cat.category_key)}
                          disabled={deleteCat.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Rules */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Classification Rules</CardTitle>
            <CardDescription>
              Rules determine which category a PR or issue belongs to. They are evaluated in priority order — the first matching rule wins.
            </CardDescription>
          </div>
          <RuleDialog
            categories={cats}
            onSave={(data) => createRule.mutate(data)}
            isPending={createRule.isPending}
            trigger={<Button size="sm"><Plus className="h-4 w-4 mr-1" /> Add Rule</Button>}
          />
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[80px]">
                  Priority
                  <InfoTip>Lower numbers are checked first. The first rule that matches determines the category. Convention: labels 1-50, issue types 51-99, title rules 100+.</InfoTip>
                </TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Match Value</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Case</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rulesList.map((rule) => {
                const matchInfo = MATCH_TYPE_LABELS[rule.match_type] ?? { label: rule.match_type, variant: 'outline' as const }
                const cat = cats.find((c) => c.category_key === rule.category_key)
                return (
                  <TableRow key={rule.id}>
                    <TableCell className="font-mono text-sm">{rule.priority}</TableCell>
                    <TableCell>
                      <Badge variant={matchInfo.variant}>{matchInfo.label}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm max-w-[200px] truncate">{rule.match_value}</TableCell>
                    <TableCell className="max-w-[200px]">
                      <span className="text-sm text-muted-foreground truncate block">{rule.description || '—'}</span>
                    </TableCell>
                    <TableCell>
                      {cat ? (
                        <span className="flex items-center gap-2">
                          <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                          {cat.display_name}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">{rule.category_key}</span>
                      )}
                    </TableCell>
                    <TableCell>{rule.case_sensitive ? 'Yes' : 'No'}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <RuleDialog
                          initial={rule}
                          categories={cats}
                          onSave={(data) => updateRule.mutate({ id: rule.id, ...data })}
                          isPending={updateRule.isPending}
                          trigger={
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                          }
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive"
                          onClick={() => deleteRule.mutate(rule.id)}
                          disabled={deleteRule.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
              {rulesList.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    No rules configured. Items will be classified as "Unknown".
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* GitHub Suggestions */}
      <SuggestionsCard categories={cats} />

      {/* Reclassify */}
      <Card>
        <CardHeader>
          <CardTitle>Reclassify Items</CardTitle>
          <CardDescription>
            Apply the current rules to all existing PRs and issues. Use this after adding, editing, or removing rules to update historical data. Items with manual overrides (set via the Investment drill-down) are preserved.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={() => reclassify.mutate()}
            disabled={reclassify.isPending}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${reclassify.isPending ? 'animate-spin' : ''}`} />
            {reclassify.isPending ? 'Reclassifying...' : 'Reclassify All'}
          </Button>
          {reclassify.data && !reclassify.isPending && (
            <p className="text-sm text-muted-foreground mt-2">
              Updated {reclassify.data.prs_updated} PRs and {reclassify.data.issues_updated} issues in {reclassify.data.duration_s}s.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
