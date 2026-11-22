# Linters for common file types

Last checked against the super-linter README "Supported linters and formatters" table: **2026-11-22**
(super-linter `main` at `1f01120`, release v9.0.0).

This file and [more-linters.md](more-linters.md) together hold every language super-linter supports,
with local install and run commands. They are the complete source, so a task needs no network lookup.

## File type → language

<!-- prettier-ignore -->
| Files | Language |
| --- | --- |
| `.py` | Python |
| `.js`, `.mjs`, `.cjs` | JavaScript |
| `.ts`, `.mts`, `.cts` | TypeScript |
| `.jsx`, `.tsx` | JSX / TSX (also JavaScript or TypeScript) |
| `.json` | JSON |
| `.css`, `.scss`, `.sass` | CSS |
| `.html`, `.htm` | HTML |
| `.md`, `.markdown` | Markdown |
| `.yml`, `.yaml` | YAML |
| `.sh`, `.bash`, files with a shell shebang | Shell |
| `Dockerfile`, `*.Dockerfile`, `Containerfile` | Dockerfile |
| `.go` | Go |
| `.rs` | Rust |
| `.rb`, `Gemfile`, `Rakefile` | Ruby |
| `.java` | Java |
| `.tf`, `.tfvars` | Terraform |
| `.sql` | SQL |
| Kubernetes manifests (`kind:` + `apiVersion:`) | Kubernetes |
| `Chart.yaml` and its `templates/` | Helm charts |
| `.github/workflows/*.yml`, `action.yml` | GitHub Actions |
| `.editorconfig` | EditorConfig |
| `.env`, `.env.*` | .env |
| any repo (optional) | Secrets, Spelling |
| anything else (`.c`, `.kt`, `.php`, `.ps1`, `.proto`) | read [more-linters.md](more-linters.md) |

## Primary linter per language

`Primary` is the one linter to install and run now. `Also in super-linter` lists the other tools super-linter
runs for that language: offer them as optional extras, and install none by default. Formatters change
style, linters find problems: keep them apart in the agent guide.

<!-- prettier-ignore -->
| Language | Primary | Install | Run | Also in super-linter (extras; format) |
| --- | --- | --- | --- | --- |
| Python | `ruff` | `brew install ruff` / `pipx install ruff` | `ruff check <path>` | pylint, flake8, isort; format: black or `ruff format` |
| JavaScript | `eslint` | `npm i -D eslint` | `npx eslint <path>` | Biome (`npx @biomejs/biome lint`); format: Prettier, Biome |
| TypeScript | `eslint` | `npm i -D eslint typescript-eslint` | `npx eslint <path>` | Biome; format: Prettier, Biome |
| JSX / TSX | `eslint` | `npm i -D eslint-plugin-react eslint-plugin-jsx-a11y` | `npx eslint <path>` | Biome; format: Prettier, Biome |
| JSON | `eslint-plugin-jsonc` | `npm i -D eslint eslint-plugin-jsonc` | `npx eslint <files>` | eslint-plugin-json, Biome; format: Prettier, Biome |
| CSS | `stylelint` | `npm i -D stylelint stylelint-config-standard` | `npx stylelint "**/*.{css,scss}"` | Biome; format: Prettier, Biome |
| HTML | `htmlhint` | `npm i -D htmlhint` | `npx htmlhint <path>` | format: Prettier, Biome |
| Markdown | `markdownlint` | `npm i -g markdownlint-cli` | `markdownlint <path>` | format: Prettier |
| YAML | `yamllint` | `brew install yamllint` / `pipx install yamllint` | `yamllint <path>` | format: Prettier |
| Shell | `shellcheck` | `brew install shellcheck` | `shellcheck <files>` | executable bit check (`git ls-files -s`: mode 100755); format: shfmt (`shfmt -d`) |
| Dockerfile | `hadolint` | `brew install hadolint` | `hadolint <Dockerfile>` | Checkov, Trivy |
| Go | `golangci-lint` | `brew install golangci-lint` | `golangci-lint run` | format: `golangci-lint fmt` or `gofmt -l` |
| Rust | `clippy` | `rustup component add clippy` | `cargo clippy -- -D warnings` | format: `cargo fmt --check` |
| Ruby | `rubocop` | `gem install rubocop` | `rubocop <path>` | — |
| Java | `checkstyle` | `brew install checkstyle` | `checkstyle -c /google_checks.xml <path>` | format: google-java-format (`brew install google-java-format`) |
| Terraform | `tflint` | `brew install tflint` | `tflint --recursive` | Checkov, Trivy; format: `terraform fmt -check -recursive` |
| SQL | `sqlfluff` | `pipx install sqlfluff` | `sqlfluff lint <path> --dialect <d>` | — |
| Kubernetes | `kubeconform` | `brew install kubeconform` | `kubeconform -strict -summary <files>` | Checkov, Trivy |
| Helm charts | `checkov` | `pipx install checkov` | `checkov -d <chart> --framework helm` | `helm lint <chart>` is a fast first check |
| GitHub Actions | `actionlint` | `brew install actionlint` | `actionlint` | zizmor (`brew install zizmor`; `zizmor .`) for security |
| EditorConfig | `editorconfig-checker` | `brew install editorconfig-checker` | `editorconfig-checker` | — |
| .env | `dotenv-linter` | `brew install dotenv-linter` | `dotenv-linter <files>` | — |
| Secrets | `gitleaks` | `brew install gitleaks` | `gitleaks directory .` | Trivy (`trivy fs --scanners secret .`) |
| Spelling | `codespell` | `pipx install codespell` | `codespell <path>` | — |

Checkov (`pipx install checkov`, `checkov -d .`) and Trivy (`brew install trivy`, `trivy config .`) are
security scanners that cover Dockerfile, Terraform, Kubernetes, Helm, CloudFormation, and ARM. Offer them
for infrastructure-heavy repos, not for every repo.

## Notes

- Scoped work: pass the changed paths (`ruff check <changed.py>`) for a fast loop; `make lint` covers the repo.
- One primary per language the project uses. Extras are for teams that ask for stricter coverage.
- A linter that needs a config (eslint, stylelint, checkstyle, sqlfluff dialect) gets the tool's
  recommended starter config, and the agent guide says where it lives.
