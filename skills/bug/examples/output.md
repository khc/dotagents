### Root Cause
- `src/cli.ts:42-51` reads the new `--format` flag, but the output renderer still falls through to the legacy summary branch when `format === "full"`.
- That branch never emits the new sectioned bug response, so the user only sees the old compact text even though the symptom requests the new format.
- The fix must preserve the existing default path for other formats and only redirect the full bug response to the new template.

### Fix
- `src/cli.ts:42-51` route `--format full` to the sectioned bug response template instead of the legacy summary branch.
- `src/renderer.ts:10-28` keep the default renderer unchanged so other formats continue to behave as before.

### Verification
- Confirmed the full-format path now renders `Root Cause`, `Fix`, and `Verification` sections in the expected order.
- Direct regression risk is low: the change is limited to the new output path and does not alter the legacy summary format.
