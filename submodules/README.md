## Submodules (LMM/LCM)

Elyra v2 composes two external components:

- LargeMemoryModel (LMM): `https://github.com/jtwolfe/LargeMemoryModel.git`
- LargeCognitiveModel (LCM): `https://github.com/jtwolfe/LargeCognitiveModel.git`

### Current status

Those repositories are currently **empty** (no initial commit). Git submodules require the remote repo to have at least one commit (a default branch tip) to pin.

### Once the repos have an initial commit

Run:

```bash
git submodule add --name LargeMemoryModel https://github.com/jtwolfe/LargeMemoryModel.git submodules/LargeMemoryModel
git submodule add --name LargeCognitiveModel https://github.com/jtwolfe/LargeCognitiveModel.git submodules/LargeCognitiveModel
git submodule update --init --recursive
```

Then commit the resulting `.gitmodules` and gitlinks.
