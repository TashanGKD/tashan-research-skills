# Security

Do not publish secrets in this repository.

## Never commit

- API keys or bearer tokens
- cookies or bind keys
- SSH private keys
- cloud credentials
- private papers, private review reports, or private datasets
- raw model logs that may contain user data

## Expected secret handling

Skills that call external services must read secrets from environment variables or local user configuration. They should not print secret values and should not write them to run manifests, reports, prompts, examples, tests, or final messages.

Common environment variables include:

- `GIIISP_AUTH_TOKEN`
- `DASHSCOPE_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_AUTH_TOKEN`
- `MINERU_API_TOKEN`

## Reporting issues

Open a private security advisory or contact the repository owner if you find a leaked credential, unsafe default, or reproducible vulnerability in a script.
