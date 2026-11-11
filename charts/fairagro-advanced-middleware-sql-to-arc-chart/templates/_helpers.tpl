{{/*
Expand the name of the chart.
*/}}
{{- define "fairagro-advanced-middleware-sql-to-arc-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "fairagro-advanced-middleware-sql-to-arc-chart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "fairagro-advanced-middleware-sql-to-arc-chart.labels" -}}
helm.sh/chart: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.chart" . }}
{{ include "fairagro-advanced-middleware-sql-to-arc-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "fairagro-advanced-middleware-sql-to-arc-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "fairagro-advanced-middleware-sql-to-arc-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Zalando Postgres cluster name (must match acid.zalan.do/v1 metadata.name).
*/}}
{{- define "fairagro-advanced-middleware-sql-to-arc-chart.postgresClusterName" -}}
{{- .Values.postgres.clusterName | default (printf "%s-pg" (include "fairagro-advanced-middleware-sql-to-arc-chart.fullname" . | trunc 50 | trimSuffix "-")) }}
{{- end }}

{{/*
Operator-managed credentials Secret for the app DB user.
*/}}
{{- define "fairagro-advanced-middleware-sql-to-arc-chart.postgresCredentialsSecret" -}}
{{- printf "%s.%s.credentials.postgresql.acid.zalan.do" .Values.postgres.user (include "fairagro-advanced-middleware-sql-to-arc-chart.postgresClusterName" .) }}
{{- end }}

{{- define "fairagro-advanced-middleware-sql-to-arc-chart.tlsSecretName" -}}
{{- printf "%s-tls" (include "fairagro-advanced-middleware-sql-to-arc-chart.fullname" .) }}
{{- end }}

{{- define "fairagro-advanced-middleware-sql-to-arc-chart.configMapName" -}}
{{- printf "%s-config" (include "fairagro-advanced-middleware-sql-to-arc-chart.fullname" .) }}
{{- end }}
