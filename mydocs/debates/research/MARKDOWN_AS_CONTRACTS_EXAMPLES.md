# Markdown as Contracts: Specification-Driven Development in the Wild

**Research Date:** March 2026
**Scope:** Real-world open source projects using markdown/prose files as executable specifications or contracts

---

## 1. BDD / Gherkin / Cucumber Ecosystem

### Core Pattern
Behavior-Driven Development (BDD) tools use structured natural language (Given/When/Then) as executable specifications. While Gherkin has its own `.feature` format, several tools have evolved to use **markdown directly**.

### Key Projects

#### **Cucumber** (★ 3.4k+)
- **Repo:** https://github.com/cucumber/cucumber
- **Pattern:** `.feature` files written in Gherkin syntax serve as both documentation and test specifications
- **How it works:** Step definitions map Gherkin clauses to executable code. The spec IS the test.
- **Languages:** Ruby, Java, JavaScript, Go, and more
- **Notable:** Cucumber has been exploring **Markdown with Gherkin** (`.feature.md`) — allowing Gherkin scenarios embedded in markdown prose
- **RFC:** https://github.com/cucumber/common/blob/main/gherkin/MARKDOWN_WITH_GHERKIN.md

#### **Gauge** (★ 3.1k+)
- **Repo:** https://github.com/getgauge/gauge
- **By:** ThoughtWorks
- **Pattern:** Uses **markdown files (`.spec` or `.md`)** as executable specifications
- **How it works:** Markdown headings become spec names, bullet points become steps, code blocks hold data tables
- **Key insight:** Gauge was specifically designed to use markdown as the specification format, making it the purest example of "markdown as contracts"
- **Example:**
  ```markdown
  # Search specification
  
  ## Search for a term
  * Navigate to search page
  * Search for "gauge"
  * Verify results contain "Gauge - Test Automation"
  ```

#### **Concordion** (★ 400+)
- **Repo:** https://github.com/concordion/concordion
- **Pattern:** HTML/Markdown specifications that are instrumented with test assertions
- **How it works:** Write prose specifications in markdown, annotate specific words/phrases with assertions that get executed
- **Key insight:** The rendered specification becomes a "living document" — green for passing, red for failing
- **Language:** Java, .NET, Python, Ruby ports

#### **SpecFlow** (★ 2.2k+)
- **Repo:** https://github.com/SpecFlowOSS/SpecFlow
- **Pattern:** .NET BDD framework using Gherkin specs
- **How it works:** Feature files serve as the single source of truth for behavior
- **Now:** Evolved into Reqnroll after SpecFlow was archived

#### **behave** (★ 3.1k+)
- **Repo:** https://github.com/behave/behave
- **Pattern:** Python BDD using Gherkin feature files
- **How it works:** Feature files are plain-text specifications that drive test execution

### The Gherkin-in-Markdown Evolution

The Cucumber team has been working on allowing Gherkin scenarios to be embedded directly in Markdown files. This means you can write rich documentation around your specifications:

```markdown
# User Authentication

Users must authenticate before accessing protected resources.
The system supports both email/password and OAuth2 flows.

## Scenario: Successful login with email

* Given a registered user with email "user@example.com"
* When they submit valid credentials
* Then they should be redirected to the dashboard
* And a session token should be created
```

---

## 2. Literate Programming

### Core Pattern
Knuth's original vision: programs as literature, where prose explains intent and code implements it. The document IS the program.

### Key Projects

#### **Jupyter Notebooks** (★ 11k+)
- **Repo:** https://github.com/jupyter/notebook
- **Pattern:** Interleaved markdown and executable code cells
- **How it works:** The notebook is simultaneously documentation, specification, and executable code
- **Scale:** Millions of notebooks on GitHub, used in data science, research, education
- **Key insight:** The most successful modern literate programming tool, though not always used that way

#### **Org-mode / Org-babel** (★ part of Emacs)
- **Pattern:** Org files contain prose, code blocks, and results — all executable
- **How it works:** Code blocks in any language can be executed in-place, results captured inline
- **Key insight:** Perhaps the most powerful literate programming environment, supporting 50+ languages
- **Notable:** Org-mode files are used as both configuration AND documentation in many Emacs setups

#### **Eve** (★ 3.8k+, archived)
- **Repo:** https://github.com/witheve/Eve
- **By:** Chris Granger (of Light Table fame)
- **Pattern:** Programs written as prose documents with embedded code blocks
- **How it works:** The markdown document IS the program. Prose explains, code executes.
- **Key insight:** The most ambitious attempt at "prose-first programming"

#### **Literate** (★ 800+)
- **Repo:** https://github.com/zyedidia/Literate
- **Pattern:** A modern literate programming tool
- **How it works:** Write markdown, code blocks are extracted ("tangled") into source files
- **Inspired by:** Knuth's WEB/CWEB system

#### **mdBook** (★ 4k+)
- **Repo:** https://github.com/rust-lang/mdBook
- **Pattern:** Rust documentation tool where code examples in markdown are compiled and tested
- **How it works:** Code blocks marked as `rust` are extracted and run as tests via `rustdoc`
- **Key insight:** Rust's `rustdoc` tests are perhaps the most mainstream example of "docs as tests"

#### **doctest** (Python stdlib)
- **Pattern:** Code examples in docstrings are executed as tests
- **How it works:** `python -m doctest` or `pytest --doctest-modules` extracts and runs examples
- **Key insight:** Built into Python since 1999 — one of the oldest "docs as tests" systems

---

## 3. Documentation-Driven Development

### Core Pattern
Write the documentation first, then implement to match. The docs are the specification.

### Key Projects & Patterns

#### **Readme Driven Development (RDD)**
- **Origin:** Tom Preston-Werner (GitHub co-founder), 2010 blog post
- **URL:** https://tom.preston-werner.com/2010/08/23/readme-driven-development.html
- **Pattern:** Write the README before writing any code
- **Key insight:** Forces you to think about the API and user experience before implementation
- **Influence:** Widely adopted in the open source world

#### **Amazon's "Working Backwards"**
- **Pattern:** Write the press release and FAQ before building the product
- **How it works:** 6-page narrative documents replace PowerPoint; the document IS the specification
- **Key insight:** Prose forces clarity of thought; bullet points hide fuzzy thinking

#### **Stripe's API Documentation**
- **Pattern:** API docs are written first and serve as the contract
- **How it works:** Documentation changes require API review; docs and implementation must match
- **Key insight:** The documentation IS the specification for API consumers

#### **Django REST Framework**
- **Pattern:** Browsable API where documentation is auto-generated from code contracts
- **Related:** Tools like `drf-spectacular` generate OpenAPI specs from code annotations

---

## 4. Specification Languages & API Contracts

### Core Pattern
Formal specification languages that define contracts, often in YAML/JSON but increasingly in markdown-adjacent formats.

### Key Projects

#### **OpenAPI / Swagger** (★ 30k+)
- **Repo:** https://github.com/OAI/OpenAPI-Specification
- **Pattern:** YAML/JSON specifications that define API contracts
- **How it works:** The spec generates docs, client SDKs, server stubs, and tests
- **Key insight:** The most successful specification-as-contract system in web development
- **Tools:** Swagger UI, Swagger Codegen, openapi-generator

#### **AsyncAPI** (★ 4k+)
- **Repo:** https://github.com/asyncapi/spec
- **Pattern:** Like OpenAPI but for event-driven/async APIs
- **How it works:** Spec defines message formats, channels, and protocols
- **Key insight:** Extends the spec-as-contract pattern to message-driven systems

#### **JSON Schema** (★ 3.5k+)
- **Repo:** https://github.com/json-schema-org/json-schema-spec
- **Pattern:** Schema definitions serve as contracts for data validation
- **How it works:** Schema validates data at runtime; schema IS the contract

#### **Protocol Buffers** (★ 65k+)
- **Repo:** https://github.com/protocolbuffers/protobuf
- **Pattern:** `.proto` files define data contracts and service interfaces
- **How it works:** Proto definitions generate code in multiple languages
- **Key insight:** The proto file is the single source of truth for data shapes

#### **GraphQL Schema** (★ 14k+)
- **Repo:** https://github.com/graphql/graphql-spec
- **Pattern:** SDL (Schema Definition Language) defines the API contract
- **How it works:** The schema is both documentation and runtime enforcement
- **Key insight:** Schema-first development is the recommended GraphQL pattern

---

## 5. Test Generation from Markdown Specs

### Core Pattern
Tools that parse prose specifications (often using RFC-style "MUST/SHOULD/MAY" language) to generate or drive tests.

### Key Projects & Approaches

#### **Dredd** (★ 4.1k+)
- **Repo:** https://github.com/apiaryio/dredd
- **Pattern:** Tests API implementations against API Blueprint or OpenAPI specifications
- **How it works:** Reads your API spec, makes HTTP requests, validates responses match the contract
- **Key insight:** The spec is literally the test suite

#### **Schemathesis** (★ 2.2k+)
- **Repo:** https://github.com/schemathesis/schemathesis
- **Pattern:** Property-based testing driven by OpenAPI/GraphQL schemas
- **How it works:** Generates test cases from your API schema, finds edge cases automatically
- **Key insight:** Combines spec-as-contract with fuzzing

#### **API Blueprint** (★ 8.6k+)
- **Repo:** https://github.com/apiaryio/api-blueprint
- **Pattern:** Markdown-based API specification format
- **How it works:** Write API specs in markdown; tools generate docs, mocks, and tests
- **Example:**
  ```markdown
  # GET /message
  + Response 200 (text/plain)
  
      Hello World!
  ```
- **Key insight:** One of the earliest "markdown as API contract" formats

#### **RAML** (★ 3.8k+)
- **Pattern:** YAML-based API spec language
- **How it works:** Spec defines API; tools generate tests, docs, and mocks

#### **Pact** (★ 3.3k+)
- **Repo:** https://github.com/pact-foundation/pact-specification
- **Pattern:** Consumer-driven contract testing
- **How it works:** Consumers define expected interactions; providers verify against these contracts
- **Key insight:** Contracts are generated from consumer tests, not written manually

#### **RFC 2119 in Practice**
- The IETF's RFC 2119 defines "MUST", "SHOULD", "MAY" as testable requirements
- Several projects use these keywords in markdown specs with the intent of generating compliance tests
- **W3C specs** use this pattern extensively — specs define behavior, test suites verify implementations
- **Example:** The HTTP/2 spec (RFC 7540) uses MUST/SHOULD extensively; h2spec tests implementations against these requirements

#### **h2spec** (★ 1.8k+)
- **Repo:** https://github.com/summerwind/h2spec
- **Pattern:** Conformance testing tool for HTTP/2 implementations
- **How it works:** Tests are derived from RFC 7540's MUST/SHOULD requirements
- **Key insight:** The RFC specification directly drives the test suite

---

## 6. Major Projects Using Markdown Specs

### Kubernetes
- **KEPs (Kubernetes Enhancement Proposals):** Markdown documents that specify feature behavior
  - Repo: https://github.com/kubernetes/enhancements
  - Pattern: Each KEP is a markdown file with structured sections (motivation, proposal, design details)
  - Key insight: KEPs serve as the specification of record; implementation must match
- **API conventions:** https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md
  - Uses MUST/SHOULD/MAY language throughout
  - Serves as the contract for all Kubernetes API design

### Go Language
- **Go Specification:** https://go.dev/ref/spec
  - The language spec is a single document that serves as the definitive contract
  - Test suite is derived from specification requirements
  - **Notable:** `go/types` package implements the spec; changes require spec changes first

### Rust
- **Rust Reference:** https://doc.rust-lang.org/reference/
  - Markdown source files that define language behavior
  - `rustdoc` tests ensure code examples in docs actually compile and run
- **Rust RFCs:** https://github.com/rust-lang/rfcs (★ 5.9k+)
  - Markdown RFCs define all language changes
  - Implementation must conform to the RFC

### Python
- **PEPs (Python Enhancement Proposals)**
  - Pattern: reStructuredText documents that specify language features
  - PEP 8 (style guide), PEP 484 (type hints), etc. serve as contracts
  - Tools like `mypy`, `ruff`, `black` implement these specs

### W3C / Web Standards
- **HTML, CSS, WebAssembly specs** are written in prose with MUST/SHOULD/MAY
- **Web Platform Tests:** https://github.com/web-platform-tests/wpt (★ 5k+)
  - Test suite derived from W3C specifications
  - Each test references specific spec sections
  - Key insight: The largest example of "specs drive tests" in the world

### IETF / Internet Standards
- RFCs written in structured prose define protocols
- Implementations are tested for conformance against spec language
- Example: TLS 1.3 (RFC 8446) — `tlsfuzzer` tests implementations against the spec

---

## 7. AI/LLM Projects Using Markdown Contracts

### Emerging Pattern (2023-2026)
The rise of LLMs has created a new pattern: **markdown files as contracts for AI code generation**.

### Key Projects & Patterns

#### **Cursor Rules / .cursorrules**
- **Pattern:** Markdown files that instruct AI coding assistants on project conventions
- **How it works:** `.cursorrules` or `.cursor/rules` files define coding standards, patterns, and constraints
- **Key insight:** These are essentially contracts between the developer and the AI

#### **GitHub Copilot Custom Instructions**
- **Pattern:** `.github/copilot-instructions.md` files define project-specific AI behavior
- **How it works:** Markdown instructions constrain how Copilot generates code
- **Key insight:** Documentation becomes a contract for AI behavior

#### **Aider Conventions**
- **Pattern:** `.aider.conf.yml` and convention files guide AI code generation
- **How it works:** Project conventions in markdown guide the AI's coding decisions

#### **Claude Projects / System Prompts**
- **Pattern:** Markdown system prompts as contracts for AI behavior
- **How it works:** Detailed markdown documents define expected behavior, constraints, output formats
- **Key insight:** The prompt IS the specification; the AI implements it

#### **Promptware / Prompt-as-Code**
- **Emerging pattern:** Treating prompts as versioned, tested, specification artifacts
- **Tools:** PromptFlow (Microsoft), LangChain, DSPy
- **Key insight:** Prompts in markdown files are becoming first-class software artifacts

#### **AI-Assisted Specification Testing**
- **Pattern:** Using LLMs to parse natural language specs and generate test cases
- **Tools:** Various experimental projects using GPT-4/Claude to read markdown specs and produce test suites
- **Key insight:** LLMs can bridge the gap between prose specifications and executable tests

#### **Amplifier / Superpowers Skills**
- **Pattern:** Markdown files define tool behavior, workflows, and constraints
- **How it works:** `.md` skill files serve as executable specifications for AI agent behavior
- **Key insight:** The markdown file IS the program — the AI interprets and executes it

---

## 8. The "Living Documentation" Pattern

### Core Concept
Documentation that is automatically verified against the system it describes. If the system changes and the docs don't, the build breaks.

### Key Resources

#### **Book: "Living Documentation" by Cyrille Martraire (2019)**
- Defines the pattern of documentation that stays in sync with code
- Introduces concepts like "evergreen documents" and "documentation as code"
- Covers Concordion, Cucumber, and other tools

#### **Book: "Specification by Example" by Gojko Adzic (2011)**
- The definitive guide to using examples as specifications
- Covers collaborative specification workshops
- Documents how teams like Spotify, uSwitch use this pattern

#### **Book: "BDD in Action" by John Ferguson Smart**
- Covers the full BDD lifecycle from specs to living documentation
- Practical examples with Cucumber, JBehave, SpecFlow

### Tools for Living Documentation

#### **Pickles** (★ 300+)
- Generates living documentation from Gherkin feature files
- Output: Searchable HTML documentation that shows test status

#### **Serenity BDD** (★ 700+)
- Generates "living documentation" reports from BDD test runs
- Shows which specs pass/fail with narrative context

---

## 9. Notable Academic Work

### Papers & Research

1. **"Executable Specifications with Scrum" (Adzic, 2009)**
   - Early formalization of specs-as-tests in agile contexts

2. **"Literate Programming" (Knuth, 1984)**
   - The foundational paper: programs should be written for humans first
   - CSLI Lecture Notes, Stanford University

3. **"Design by Contract" (Meyer, 1986-1992)**
   - Eiffel language with built-in contracts (preconditions, postconditions, invariants)
   - Contracts are part of the source code, not external documentation

4. **"Specification-Driven Development of REST APIs" (Ed-Douibi et al., 2018)**
   - Academic formalization of API-spec-first development
   - Published in ICWE 2018

5. **"Generating Tests from Natural Language Specifications" (various, 2023-2025)**
   - Multiple papers exploring LLM-based test generation from prose specs
   - Key venues: ICSE, FSE, ASE conferences

---

## 10. Summary: Taxonomy of Patterns

| Pattern | Spec Format | Execution Method | Example Tools |
|---------|------------|------------------|---------------|
| **BDD** | Gherkin / Markdown | Step definitions map to code | Cucumber, Gauge, Concordion |
| **Literate Programming** | Prose + Code blocks | Tangle/weave extraction | Jupyter, Org-mode, Eve |
| **Doc-Driven Dev** | README / Prose | Manual conformance | RDD, Amazon Working Backwards |
| **API Contracts** | YAML/JSON/Markdown | Code generation + validation | OpenAPI, AsyncAPI, API Blueprint |
| **Living Documentation** | Gherkin + Annotations | Auto-verified against system | Serenity, Pickles, Concordion |
| **RFC-Style Specs** | Prose with MUST/SHOULD | Conformance test suites | W3C WPT, h2spec, RFC compliance |
| **AI Contracts** | Markdown instructions | LLM interpretation | Cursor Rules, Copilot Instructions |
| **Design by Contract** | In-code annotations | Runtime enforcement | Eiffel, Python `contracts`, Ada SPARK |

---

## 11. Key Takeaways

### What Works
1. **Gauge** is the purest example of "markdown as executable spec" — it was designed for this from the start
2. **API Blueprint** pioneered "markdown as API contract"
3. **Cucumber's Gherkin-in-Markdown** is evolving toward richer prose around specs
4. **Rust's rustdoc tests** show that code examples in docs can be first-class tests
5. **W3C Web Platform Tests** demonstrate that prose specs CAN drive comprehensive test suites at scale
6. **AI instruction files** (.cursorrules, copilot-instructions.md) represent a new frontier where markdown IS the program

### What Doesn't Work (Yet)
1. **Automatic parsing of MUST/SHOULD/MAY** into tests remains largely manual — no widely-adopted tool does this automatically
2. **Prose-to-test generation** via LLMs is promising but immature
3. **Living documentation** tools have limited adoption outside BDD-heavy teams
4. **Literate programming** remains niche despite being intellectually compelling

### The Emerging Frontier
The most interesting development is the convergence of:
- **Markdown specifications** (human-readable contracts)
- **LLM interpretation** (AI that can read and implement specs)
- **Automated verification** (testing that specs are met)

This creates a potential future where:
1. You write a markdown specification
2. An AI generates implementation from the spec
3. Tests are auto-generated from the spec's MUST/SHOULD/MAY clauses
4. The spec serves as living documentation
5. Changes to the spec trigger re-generation and re-verification

This is essentially **Knuth's literate programming vision**, but with AI as the "compiler" that reads prose and produces programs.

---

## Sources & Further Reading

- Gauge: https://gauge.org/ / https://github.com/getgauge/gauge
- Cucumber Markdown RFC: https://github.com/cucumber/common/blob/main/gherkin/MARKDOWN_WITH_GHERKIN.md
- Concordion: https://concordion.org/
- API Blueprint: https://apiblueprint.org/
- OpenAPI: https://www.openapis.org/
- Dredd: https://dredd.org/
- Web Platform Tests: https://web-platform-tests.org/
- RDD: https://tom.preston-werner.com/2010/08/23/readme-driven-development.html
- Kubernetes KEPs: https://github.com/kubernetes/enhancements
- Rust RFCs: https://github.com/rust-lang/rfcs
- h2spec: https://github.com/summerwind/h2spec
- Schemathesis: https://github.com/schemathesis/schemathesis
- Living Documentation (book): https://www.pearson.com/en-us/subject-catalog/p/living-documentation/P200000009424
- Specification by Example (book): https://gojko.net/books/specification-by-example/