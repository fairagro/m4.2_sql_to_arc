{{- define "fairagro-advanced-middleware-sql-to-arc-chart.converterPodSpec" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
restartPolicy: Never
initContainers:
  - name: load-edaphobase-dump
    image: {{ .Values.bootstrap.image | quote }}
    imagePullPolicy: IfNotPresent
    env:
      - name: PGHOST
        value: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.postgresClusterName" . | quote }}
      - name: PGPORT
        value: "5432"
      - name: PGDATABASE
        value: {{ .Values.postgres.database | quote }}
      - name: DUMP_URL
        value: {{ .Values.bootstrap.dumpUrl | quote }}
      - name: PGUSER
        valueFrom:
          secretKeyRef:
            name: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.postgresCredentialsSecret" . }}
            key: username
      - name: PGPASSWORD
        valueFrom:
          secretKeyRef:
            name: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.postgresCredentialsSecret" . }}
            key: password
    resources:
      {{- toYaml .Values.bootstrap.resources | nindent 6 }}
    command:
      - /bin/sh
      - -ec
      - |
        set -eu
        echo "Waiting for Postgres at ${PGHOST}:${PGPORT} ..."
        for i in $(seq 1 90); do
          if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; then
            echo "Postgres is ready."
            break
          fi
          if [ "$i" -eq 90 ]; then
            echo "ERROR: Postgres at ${PGHOST} did not become ready in time." >&2
            exit 1
          fi
          sleep 5
        done

        DUMP_FILE=/tmp/edaphobase.sql
        echo "Downloading Edaphobase dump from ${DUMP_URL} (no local fallback) ..."
        if ! wget -O "$DUMP_FILE" "$DUMP_URL"; then
          echo "ERROR: Failed to download Edaphobase dump from ${DUMP_URL}." >&2
          echo "ERROR: No local dump fallback is configured; fix network egress or dumpUrl and retry." >&2
          exit 1
        fi
        if [ ! -s "$DUMP_FILE" ]; then
          echo "ERROR: Downloaded dump from ${DUMP_URL} is empty." >&2
          echo "ERROR: No local dump fallback is configured." >&2
          exit 1
        fi

        echo "Resetting database ${PGDATABASE} for a clean dump import ..."
        # Dump uses plain CREATE (no IF NOT EXISTS); wipe public so re-runs on a
        # persistent Zalando volume do not fail with "relation already exists".
        # Use -c (not a heredoc): heredoc terminators break Helm/YAML indentation.
        psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO CURRENT_USER; GRANT ALL ON SCHEMA public TO public;"

        echo "Importing dump into database ${PGDATABASE} ..."
        # Session-only: skip WAL flush waits on every COPY row. Source of truth
        # is the dump; a crash mid-import is retried from scratch anyway.
        PGOPTIONS="-c synchronous_commit=off -c statement_timeout=0" \
          psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -f "$DUMP_FILE"
        echo "Dump reload complete."
containers:
  - name: sql-to-arc
    image: "{{ .Values.image.repository }}:{{ default .Chart.AppVersion .Values.image.tag }}"
    imagePullPolicy: {{ .Values.image.pullPolicy }}
    env:
      - name: PGHOST
        value: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.postgresClusterName" . | quote }}
      - name: PGDATABASE
        value: {{ .Values.postgres.database | quote }}
      - name: PGUSER
        valueFrom:
          secretKeyRef:
            name: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.postgresCredentialsSecret" . }}
            key: username
      - name: PGPASSWORD
        valueFrom:
          secretKeyRef:
            name: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.postgresCredentialsSecret" . }}
            key: password
      # Kubernetes expands $(VAR) from previously defined env (incl. secretKeyRef).
      - name: SQL_TO_ARC_CONNECTION_STRING
        value: "postgresql+psycopg://$(PGUSER):$(PGPASSWORD)@$(PGHOST):5432/$(PGDATABASE)"
    resources:
      {{- toYaml .Values.converter.resources | nindent 6 }}
    # Explicit -c: do not rely solely on image CMD (matches chart/spec contract).
    command:
      - /middleware/sql_to_arc/sql_to_arc
    args:
      - -c
      - /etc/sql_to_arc/config.yaml
    volumeMounts:
      - name: config
        mountPath: /etc/sql_to_arc
        readOnly: true
      {{- if .Values.tls.enabled }}
      - name: tls
        mountPath: {{ .Values.tls.mountPath | quote }}
        readOnly: true
      {{- end }}
volumes:
  - name: config
    configMap:
      name: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.configMapName" . }}
  {{- if .Values.tls.enabled }}
  - name: tls
    secret:
      secretName: {{ include "fairagro-advanced-middleware-sql-to-arc-chart.tlsSecretName" . }}
  {{- end }}
{{- end }}
