---
name: snapy-multi-block-output
description: Debug multi-MeshBlock-per-process bugs in snapy, especially geometry partitioning, process-group lifecycle, and output combining.
---

# Snapy Multi-Block Output

Use this skill when `repos/snapy` is running more than one `MeshBlock` on the
same process and behavior differs from the one-block-per-process case.

## Workflow

1. Compare three decompositions on the same case:
   `1 proc x 1 block`, `1 proc x N blocks`, and `N proc x 1 block`.
2. If `1x1` matches `Nx1` but not `1xN`, inspect same-process assumptions
   before changing backend communication.
3. Check that each local block has a distinct global block rank and that
   geometry/coordinate partitioning is recomputed from that block rank.
4. Check process-group lifetime and shutdown paths for duplicate collectives or
   duplicate `shutdown()` calls from multiple local blocks.
5. Check output-combine timing:
   combine once per process only after all local block files for that output
   step exist.
6. Validate merged outputs numerically across decompositions and inspect merged
   coordinates for monotonicity and duplication.

## Common Failure Modes

- Coordinate options are partitioned from env rank before `Mesh` rewrites the
  local block's global rank, so multiple local blocks write the same spatial
  slab.
- Output combine runs once per block instead of once per process, so process-
  local files are merged too early or by the wrong root.
- Shared process-group shutdown is executed by each local block, which can
  abort NCCL or deadlock Gloo near finalize.
- Standalone `MeshBlock::initialize()` exchange logic is reused block-by-block
  under `Mesh`, causing deadlocks because local-copy orchestration is bypassed.

## NCCL Multi-Block Note

- For NCCL with multiple `MeshBlock`s per process, point-to-point tags are not
  a reliable discriminator the way they are with Gloo.
- For cubed-sphere multi-block-per-process runs, per-block `send/recv` launch
  is insufficient even if local copies and topology are correct.
- The durable fix pattern is:
  route cubed-sphere exchange through the shared `Layout::launch_exchange()`
  path, order remote ops by actual exchange-loop order rather than buffer id,
  and for NCCL launch remote work process-wide across all local blocks so
  `recv/send` posting order is identical on both processes.

## Guardrails

- Prefer fixing shared `Mesh` orchestration and output code over adding
  case-specific workarounds in examples.
- Treat duplicated coordinates in merged NetCDF as an upstream geometry/output
  bug, not a physics discrepancy.
- Validate both `gloo` and `nccl` when the change touches communication or
  output ownership.
- Keep trial runs short first; only start full runs after the three
  decomposition variants match exactly.
