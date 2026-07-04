# CodeRabbit DSP Review + Release Workflow

## CodeRabbit review cycle (PR #283)

CodeRabbit posts inline review comments on DSP script PRs. The review is high-quality — it catches real DSP bugs (NaN, undefined variables, unstable filters, fake lookahead). Process:

1. **Fetch review comments** via `gh api repos/andremichelle/openDAW/pulls/{PR}/comments --jq '.[] | {path, line, body[:200], id}'`
2. **Triage by severity** — CodeRabbit tags each: `🔴 Critical`, `🟠 Major`, `🟡 Minor`
3. **Fix all comments** — even minors (markdownlint, README formatting). andremichelle expects clean reviews.
4. **Validate fixes** — JS syntax validation via bridge (see pitfalls reference for the `eval()` pattern)
5. **Commit + push** with detailed message listing each fix
6. **Sync to opendaw-mcp** — copy fixed scripts from openDAW `examples/` → opendaw-mcp `scripts/`

## 10 bug categories CodeRabbit catches (v1.11.2 session)

1. **Undefined variable from typo** — `outR` vs `outGain`. Name gain variables explicitly.
2. **Delay buffer too small** — modulation can push delay beyond buffer. Size for 2× max excursion.
3. **Negative modulo** — JS `%` returns negative for negative operands. Use `((x % n) + n) % n`.
4. **Shared state across channels** — stereo needs per-channel buffers/phases.
5. **Parameter scaling disconnect** — `@param slew 0 0 1 linear` gives 0–1, `/100` in process() disables it.
6. **Fake lookahead** — envelope tracks current input, gain must apply to delayed signal.
7. **Unstable filter topologies** — non-standard allpass recursions blow up. Use 1st-order forms.
8. **Swing dropping notes** — in Spielwerk generators, don't `break` on `notePos >= to`; yield anyway.
9. **Comb filter stuck index** — advance `c.idx` each sample, not just once per block.
10. **Width as channel balance** — use M/S decode for true stereo width, not gain cross-mix.

## gh CLI for PR management

`gh pr edit` fails on upstream PRs with "Projects (classic) deprecated" error. Use `gh api` instead:
```bash
gh api repos/andremichelle/openDAW/pulls/283 --method PATCH -f title="..." -F body=@/tmp/body.md
```

For issue comments:
```bash
gh issue comment {N} --repo andremichelle/openDAW --body "..."
```

## Release workflow (v1.11.2)

When PyPI token is unavailable, GitHub releases with artifacts are the fallback:

```bash
# 1. Version bump (pyproject.toml, server.py, server.json, README.md changelog)
# 2. Build
cd opendaw-mcp && uv build  # produces dist/{name}-{version}.tar.gz + .whl
# 3. GitHub release with artifacts
gh release create v{VERSION} --repo AMEOBIUS/opendaw-mcp \
  --title "v{VERSION} — ..." --notes "..." \
  dist/{name}-{version}.tar.gz dist/{name}-{version}-py3-none-any.whl
# 4. CI auto-runs on push (tests + MCP Registry publish via OIDC)
```

`uv build` is preferred over `python3 -m build` — faster, handles metadata correctly. Both produce valid wheel+sdist.

## Issue commenting strategy

When commenting on open upstream issues, reference PR #283 and explain:
- What script addresses the issue
- How it works (brief)
- Limitations (e.g., "Werkstatt has no MIDI input, so this is a workaround")
- Related issues (e.g., #211 sidechain for #277 MIDI input)

Don't close issues — just comment. andremichelle decides what closes.
