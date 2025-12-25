## Submodules (LMM/LCM)

Elyra v2 composes two external components:

- LargeMemoryModel (LMM): `https://github.com/jtwolfe/LargeMemoryModel.git`
- LargeCognitiveModel (LCM): `https://github.com/jtwolfe/LargeCognitiveModel.git`

### Current status

These repositories are now initialized and pinned as git submodules (see `.gitmodules` and `git submodule status`).

### Clone and init

Run:

```bash
git submodule update --init --recursive
```

### Updating submodules

To pull the latest commits from the configured branches:

```bash
git submodule update --remote --recursive
```

Then commit the updated gitlink SHAs in Elyra.
