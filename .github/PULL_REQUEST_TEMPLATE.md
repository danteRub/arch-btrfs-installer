## Summary

Describe the change.

## Type of change

- [ ] Documentation only
- [ ] Tests or fixtures
- [ ] CLI behavior
- [ ] Diagnostics
- [ ] Hardware parser
- [ ] Planner
- [ ] Risk classifier
- [ ] Explainer / LLM boundary
- [ ] Installer script
- [ ] Other

## Safety impact

Answer these before requesting review:

- [ ] This change does not execute destructive commands automatically.
- [ ] This change does not downgrade risk labels.
- [ ] This change does not hide warnings about Windows, NTFS, EFI or multiple disks.
- [ ] This change does not allow an LLM to override deterministic safety logic.
- [ ] This change does not write outside documented output paths.

If any box cannot be checked, explain why:

```text
N/A or explanation here.
```

## Testing

- [ ] `pytest -q` passes locally, or this PR is documentation-only.
- [ ] New behavior has tests, or no behavior changed.
- [ ] Fixtures were added/updated if this affects hardware scenarios.

## Notes for reviewers

Mention any specific files or safety boundaries that deserve extra attention.
