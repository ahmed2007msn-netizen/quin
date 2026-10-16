# quin

## ECC (Everything Claude Code)

This repo has the ECC plugin (`ecc@ecc`, from github.com/affaan-m/ECC) enabled at project scope.

- Plugin + marketplace: `.claude/settings.json`
- Rules (always loaded): `.claude/rules/ecc/common/`
- Hook profile: `ECC_HOOK_PROFILE=standard` (change to `minimal` or `strict` in `.claude/settings.json`)

When the stack gets chosen, add its rule pack from ECC (e.g. `rules/typescript`, `rules/python`)
into `.claude/rules/ecc/`.
