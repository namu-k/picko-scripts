# PR: feat(render-media): add CLI-based image rendering pipeline

**Create PR at:** https://github.com/namu-k/picko-scripts/pull/new/003-auto-collector

---

## Title (copy to PR title field)

```
feat(render-media): add CLI-based image rendering pipeline
```

---

## Body (copy to PR description)

```markdown
## Summary

- **Input template parser** (`picko/multimedia_io.py`): Parses YAML frontmatter templates with validation and reference document loading
- **Proposal generator** (`picko/proposal_generator.py`): Auto-detects content types (quote, card, list, data, carousel) from input text
- **HTML templates** (`templates/images/`): 5 Jinja2 templates with dynamic dimensions and platform-specific sizing
- **Playwright renderer** (`picko/html_renderer.py`): HTML-to-PNG rendering with platform dimension support
- **CLI interface** (`scripts/render_media.py`): status, review, and render commands with 2-step approval workflow
- **Security hardening**: Path traversal prevention, template whitelist validation

## Key Features

| Feature            | Description                                                |
|--------------------|------------------------------------------------------------|
| Content detection  | Auto-detect quote, card, list, data, carousel types        |
| Platform dimensions| LinkedIn 1200×627, Twitter 1200×675, Instagram 1080×1080   |
| Dynamic sizing     | Templates support custom width/height                      |
| 2-step review      | Proposal approval → render → final approval                |

## Test Plan

- 19 tests in `test_image_templates.py` pass
- Template rendering with Korean text verified
- Platform dimension lookup (LinkedIn, Twitter, Instagram, Threads)
- Trend indicators (up/down) in data template
- Invalid template validation
- Dynamic dimensions support

---

Commits included (14): feat(multimedia) parser + loader, feat(proposal) generator, feat(templates) HTML, feat(renderer) Playwright, feat(cli) render_media, test(integration), fix(security), feat(templates) data/carousel, fix(templates) dimensions, test(templates), docs(changelog), chore(uv lockfile).
```

---

## Commits included (14)

- feat(multimedia): add input template parser
- feat(multimedia): add reference document loader
- feat(proposal): add proposal generator with content type detection
- feat(templates): add HTML image templates (quote, card, list)
- feat(renderer): add Playwright HTML-to-PNG renderer
- feat(cli): add render_media CLI with status and review commands
- test(integration): add render_media pipeline integration test
- fix(security): address code review security issues
- feat(templates): add data and carousel templates, platform dimensions
- fix(templates): add position:relative and dynamic dimensions
- test(templates): add trend and platform dimension tests
- docs(changelog): add image rendering pipeline entry
- chore: add uv lockfile
