## Summary

<!-- What does this PR do, and why? 2-3 sentences. Link any related issues. -->

Closes #

---

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behaviour)
- [ ] Refactor (no functional change, code quality improvement)
- [ ] Documentation update
- [ ] CI/CD or build system change
- [ ] Dependency update

---

## Testing

- [ ] `python -m pytest tests/ -v` passes
- [ ] `cd frontend && npx tsc --noEmit` passes
- [ ] `cd frontend && npm run build` passes
- [ ] Manual testing performed (describe below)
- [ ] New tests added for new behaviour

**Manual test description:**
<!-- What did you manually test? What inputs/scenarios? -->

---

## Review Checklist

- [ ] No secrets or credentials committed
- [ ] `.env.example` updated if new environment variables added
- [ ] Alembic migration created if schema changed (`alembic revision --autogenerate -m "..."`)
- [ ] BM25 cache invalidated if KB ingestion changed
- [ ] `noUnusedLocals` / `noUnusedParameters` respected (TypeScript)
- [ ] All React hooks called before any conditional return

---

## Screenshots

<!-- For UI changes: include before/after screenshots. Delete this section if not applicable. -->

| Before | After |
|--------|-------|
| | |

---

## Breaking Changes

<!-- If this is a breaking change, describe what breaks and how users should migrate. -->
<!-- Delete this section if not applicable. -->
