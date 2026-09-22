{{- define "platform-app.image" -}}
{{- $repository := required (printf "%s.image.repository is required" .name) .image.repository -}}
{{- if .image.digest -}}
{{- if not (regexMatch "^sha256:[a-f0-9]{64}$" .image.digest) -}}
{{- fail (printf "%s.image.digest must be a sha256 digest" .name) -}}
{{- end -}}
{{- printf "%s@%s" $repository .image.digest -}}
{{- else -}}
{{- $tag := required (printf "%s.image.tag is required when image.digest is empty" .name) .image.tag -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}
