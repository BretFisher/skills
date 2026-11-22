# Linters for less common file types

Last checked against the super-linter README "Supported linters and formatters" table: **2026-11-22**
(super-linter `main` at `1f01120`, release v9.0.0).

The languages super-linter supports that [linter-commands.md](linter-commands.md) does not cover. The first
tool in each row is the primary; the rest are optional extras.

<!-- prettier-ignore -->
| Language (files) | Linters, primary first | Install | Run | Formatter |
| --- | --- | --- | --- | --- |
| Ansible (playbooks, roles) | ansible-lint | `pipx install ansible-lint` | `ansible-lint` | YAML and Python formatters |
| Amazon States Language (`*.asl.json`) | asl-validator | `npm i -g asl-validator` | `asl-validator --json-path <file>` | JSON formatters |
| Astro (`.astro`) | Biome | `npm i -D -E @biomejs/biome` | `npx @biomejs/biome lint <path>` | Biome |
| AWS CloudFormation (templates) | cfn-lint, Checkov, Trivy | `pipx install cfn-lint` | `cfn-lint <templates>` | YAML formatters |
| Azure Resource Manager (ARM JSON) | arm-ttk, Checkov, Trivy | clone `Azure/arm-ttk`, then `Import-Module ./arm-ttk.psd1` (PowerShell) | `Test-AzTemplate -TemplatePath <dir>` | JSON formatters |
| C, C++ (`.c`, `.h`, `.cpp`, `.hpp`) | cpplint | `pipx install cpplint` | `cpplint --recursive <path>` | clang-format (`clang-format --dry-run --Werror`) |
| C#, .NET (`.cs`, `.sln`, `.csproj`) | `dotnet format` analyzers and style | .NET SDK (`brew install --cask dotnet-sdk`) | `dotnet format --verify-no-changes` | `dotnet format whitespace` |
| Clojure (`.clj`, `.cljs`, `.edn`) | clj-kondo | `brew install borkdude/brew/clj-kondo` | `clj-kondo --lint <path>` | — |
| CoffeeScript (`.coffee`) | coffeelint | `npm i -D @coffeelint/cli` | `npx coffeelint <path>` | — |
| Commit messages | commitlint | `npm i -D @commitlint/cli @commitlint/config-conventional` | `npx commitlint --from HEAD~1` | — |
| Copy/paste detection (any code) | jscpd | `npm i -g jscpd` | `jscpd <path>` | — |
| Dart (`.dart`) | `dart analyze` | Dart SDK (`brew install dart-sdk`) | `dart analyze --fatal-infos --fatal-warnings` | `dart format` |
| Git merge conflict markers (any file) | conflict marker check | built into git | `git grep -n -e '^<<<<<<< ' -e '^>>>>>>> '` | — |
| GoReleaser (`.goreleaser.yaml`) | goreleaser check | `brew install goreleaser` | `goreleaser check` | YAML formatters |
| GraphQL (`.graphql`, `.gql`) | Biome | `npm i -D -E @biomejs/biome` | `npx @biomejs/biome lint <path>` | Prettier, Biome |
| GritQL (`.grit`) | none (formatter only) | `npm i -D -E @biomejs/biome` | — | Biome (`npx @biomejs/biome format`) |
| Groovy (`.groovy`, `Jenkinsfile`, `.gradle`) | npm-groovy-lint | `npm i -g npm-groovy-lint` | `npm-groovy-lint <path>` | — |
| JSONC, JSON5 (`.jsonc`, `.json5`) | eslint-plugin-jsonc, Biome | `npm i -D eslint eslint-plugin-jsonc` | `npx eslint <files>` | Prettier, Biome |
| Kotlin (`.kt`, `.kts`) | ktlint | `brew install ktlint` | `ktlint` | `ktlint --format` |
| LaTeX (`.tex`) | ChkTeX | TeX Live (`brew install --cask mactex-no-gui`) | `chktex <file>` | — |
| Licenses (dependencies) | Trivy | `brew install trivy` | `trivy fs --scanners license .` | — |
| Lua (`.lua`) | luacheck | `brew install luacheck` | `luacheck <path>` | — |
| Natural language (prose in `.md`, `.txt`) | textlint | `npm i -D textlint` plus a rule preset | `npx textlint <files>` | — |
| OpenAPI (`openapi.yaml`, `swagger.json`) | Spectral | `npm i -g @stoplight/spectral-cli` | `spectral lint <file>` | YAML formatters |
| Perl (`.pl`, `.pm`) | perlcritic | `cpanm Perl::Critic` | `perlcritic <path>` | — |
| PHP (`.php`) | PHPStan, `php -l`, PHP_CodeSniffer, Psalm | `composer require --dev phpstan/phpstan` | `vendor/bin/phpstan analyse <path>` | — |
| PowerShell (`.ps1`, `.psm1`) | PSScriptAnalyzer | `Install-Module PSScriptAnalyzer` | `Invoke-ScriptAnalyzer -Path <path> -Recurse` | — |
| pre-commit config (`.pre-commit-config.yaml`) | pre-commit | `pipx install pre-commit` | `pre-commit run --all-files` | — |
| Protocol Buffers (`.proto`) | protolint | `brew install protolint` | `protolint lint <path>` | — |
| R (`.R`, `.Rmd`) | lintr | `Rscript -e 'install.packages("lintr")'` | `Rscript -e 'lintr::lint_dir()'` | — |
| Renovate (`renovate.json`) | renovate-config-validator | none (runs with npx) | `npx --yes --package renovate -- renovate-config-validator --strict` | JSON formatters |
| Scala (`.scala`) | none (formatter only) | `cs install scalafmt` (Coursier) | — | scalafmt (`scalafmt --check`) |
| SBOM and vulnerabilities (dependencies) | Trivy | `brew install trivy` | `trivy fs --scanners vuln .` | — |
| Snakemake (`Snakefile`, `.smk`) | `snakemake --lint` | `pipx install snakemake` | `snakemake --lint` | snakefmt (`snakefmt --check .`) |
| Svelte (`.svelte`) | Biome | `npm i -D -E @biomejs/biome` | `npx @biomejs/biome lint <path>` | Biome |
| Terragrunt (`terragrunt.hcl`) | terragrunt | `brew install terragrunt` | `terragrunt hcl format --check` | — |
| Vue (`.vue`) | eslint-plugin-vue, Biome | `npm i -D eslint eslint-plugin-vue` | `npx eslint <path>` | Prettier, Biome |
| XML (`.xml`) | xmllint (LibXML) | built into macOS; `brew install libxml2` elsewhere | `xmllint --noout <files>` | — |

For a language in neither file, say that super-linter has no linter for it, and ask the user before you
pick one.
