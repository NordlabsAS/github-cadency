import OneOnOnePrepView from './OneOnOnePrepView'
import TeamHealthView from './TeamHealthView'
import GenericAnalysisView from './GenericAnalysisView'

interface Props {
  analysisType: string | null
  result: Record<string, unknown> | null
}

export default function AnalysisResultRenderer({ analysisType, result }: Props) {
  if (!result) {
    return <p className="text-sm text-muted-foreground">No result data.</p>
  }

  if (result.parse_error) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-destructive">Analysis returned a parse error.</p>
        <pre className="max-h-60 overflow-auto rounded bg-muted p-3 text-xs">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>
    )
  }

  switch (analysisType) {
    case 'one_on_one_prep':
      return <OneOnOnePrepView result={result} />
    case 'team_health':
      return <TeamHealthView result={result} />
    case 'communication':
    case 'conflict':
    case 'sentiment':
      return <GenericAnalysisView result={result} />
    default:
      return (
        <pre className="max-h-60 overflow-auto rounded bg-muted p-3 text-xs">
          {JSON.stringify(result, null, 2)}
        </pre>
      )
  }
}
