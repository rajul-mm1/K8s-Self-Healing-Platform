{{- define "todo-app.image" -}}
{{- if .root.Values.image.registry -}}
{{ .root.Values.image.registry }}/{{ .name }}:{{ .root.Values.image.tag }}
{{- else -}}
{{ .name }}:{{ .root.Values.image.tag }}
{{- end -}}
{{- end -}}

{{- define "todo-app.labels" -}}
app.kubernetes.io/part-of: todo-app
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
