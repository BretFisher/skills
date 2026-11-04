# Linter commands reference

The practical layer super-linter's README doesn't provide: how to map a file to a language, and how to install and run each linter **locally**. super-linter lists linters by language but not their local install/invoke commands — this fills that gap.

Always prefer the **live** super-linter list (`https://raw.githubusercontent.com/super-linter/super-linter/main/README.md`, the `## Supported linters and formatters` table) to confirm the current linter for a language. The snapshot below is a fallback and a source of install/run commands; treat the live list as authoritative for _which_ linter, and this file as authoritative for _how_ to install and run it.

## Extension → language map

super-linter organizes by language, not extension. Use this to go from the files in a project to a super-linter language row.

| Extension / filename          | Language                            |
| ----------------------------- | ----------------------------------- |
| `.py`                         | Python                              |
| `.js`, `.jsx`, `.mjs`, `.cjs` | JavaScript                          |
| `.ts`, `.tsx`                 | TypeScript                          |
| `.go`                         | Go                                  |
| `.rs`                         | Rust                                |
| `.rb`                         | Ruby                                |
| `.java`                       | Java                                |
| `.sh`, `.bash`                | Shell                               |
| `Dockerfile`, `*.dockerfile`  | Dockerfile                          |
| `.yml`, `.yaml`               | YAML                                |
| `.json`                       | JSON                                |
| `.md`, `.markdown`            | Markdown                            |
| `.tf`, `.tfvars`              | Terraform                           |
| `.css`, `.scss`, `.sass`      | CSS                                 |
| `.html`, `.htm`               | HTML                                |
| `.sql`                        | SQL                                 |
| `.xml`                        | XML                                 |
| `.toml`                       | TOML                                |
| `.env`                        | dotenv                              |
| `.editorconfig`               | EditorConfig                        |
| `*.k8s.yaml`, k8s manifests   | Kubernetes (Checkov/kubeconform)    |
| `.github/workflows/*.yml`     | GitHub Actions (actionlint, zizmor) |

## Primary linter per language

`Primary` = the canonical, lowest-friction local choice to install and run now. `Optional extras` = other linters super-linter also runs for that language; offer them but don't install by default. `Formatter` is a separate concern (style, not lint) — mention but keep distinct.

Install commands list a common cross-platform option first; on macOS, Homebrew (`brew install ...`) is a good default where available. Always confirm the live super-linter list before finalizing.

| Language       | Primary linter                 | Install                                           | Local run                       | Optional extras / formatter                              |
| -------------- | ------------------------------ | ------------------------------------------------- | ------------------------------- | -------------------------------------------------------- |
| Python         | `ruff`                         | `pipx install ruff` / `brew install ruff`         | `ruff check <path>`             | extras: pylint, flake8; format: `ruff format` or black   |
| JavaScript     | `eslint`                       | `npm i -D eslint`                                 | `npx eslint <path>`             | alt: Biome (`npx @biomejs/biome lint`); format: prettier |
| TypeScript     | `eslint` (+ typescript-eslint) | `npm i -D eslint typescript-eslint`               | `npx eslint <path>`             | alt: Biome; format: prettier                             |
| Go             | `golangci-lint`                | `brew install golangci-lint`                      | `golangci-lint run`             | format: `gofmt` / `golangci-lint fmt`                    |
| Rust           | `clippy`                       | `rustup component add clippy`                     | `cargo clippy`                  | format: `cargo fmt`                                      |
| Ruby           | `rubocop`                      | `gem install rubocop`                             | `rubocop <path>`                | —                                                        |
| Java           | `checkstyle`                   | `brew install checkstyle`                         | `checkstyle -c <config> <path>` | format: google-java-format                               |
| Shell          | `shellcheck`                   | `brew install shellcheck`                         | `shellcheck <files>`            | format: shfmt (`brew install shfmt`)                     |
| Dockerfile     | `hadolint`                     | `brew install hadolint`                           | `hadolint <Dockerfile>`         | extras: checkov, trivy                                   |
| YAML           | `yamllint`                     | `pipx install yamllint` / `brew install yamllint` | `yamllint <path>`               | format: prettier                                         |
| JSON           | `eslint-plugin-jsonc`          | `npm i -D eslint eslint-plugin-jsonc`             | `npx eslint <files>`            | alt: Biome; `jq empty <file>` for quick validity         |
| Markdown       | `markdownlint`                 | `npm i -g markdownlint-cli`                       | `markdownlint <path>`           | format: prettier                                         |
| Terraform      | `tflint`                       | `brew install tflint`                             | `tflint`                        | extras: checkov, trivy; format: `terraform fmt`          |
| CSS / SCSS     | `stylelint`                    | `npm i -D stylelint stylelint-config-standard`    | `npx stylelint "**/*.css"`      | alt: Biome                                               |
| HTML           | `htmlhint`                     | `npm i -g htmlhint`                               | `htmlhint <path>`               | —                                                        |
| SQL            | `sqlfluff`                     | `pipx install sqlfluff`                           | `sqlfluff lint <path>`          | format: `sqlfluff fix`                                   |
| GitHub Actions | `actionlint`                   | `brew install actionlint`                         | `actionlint`                    | also: zizmor (`pipx install zizmor`) for security        |
| Kubernetes     | `kubeconform`                  | `brew install kubeconform`                        | `kubeconform <manifests>`       | extras: checkov, trivy                                   |
| EditorConfig   | `editorconfig-checker`         | `brew install editorconfig-checker`               | `editorconfig-checker`          | —                                                        |

## Notes

- **Lint vs format**: linters find problems; formatters rewrite style. Keep them separate in what you write into AGENTS.md so a formatter isn't mistaken for passing a lint gate.
- **Run on changed files when scoped**: when working a feature, pass the changed paths (e.g. `ruff check <changed.py>`) for a fast loop. `make lint` runs across the whole repo.
- **Don't over-install**: one primary linter per language the project actually uses. Optional extras are there for teams that want stricter coverage, not a default.
- **Security linters** (checkov, trivy, zizmor) overlap many languages. Offer them when the project is infra-heavy (Docker, Terraform, Kubernetes, GitHub Actions), not for every repo.
