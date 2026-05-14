# Quick reset for local LLM memory

A field guide for refreshing memory held by the local LLM stack on Apple
Silicon. Useful after long benchmark sweeps, between very large model
runs, or any time you want vllm-mlx to start from a clean allocation
without rebooting.

## TL;DR

```bash
clear-mem
```

Defined in `nix-home/modules/home-manager/zsh/aliases.nix`. Equivalent to:

```bash
pkill -9 -f 'vllm-mlx serve'
vm_stat | grep -E 'Pages (wired|free)'
sysctl vm.swapusage
```

llama-swap respawns vllm-mlx automatically on the next inference request,
so there is nothing else to start.

## Why this exists

vllm-mlx serves models through MLX, which uses a Metal memory allocator
that pools buffer allocations for efficient reuse. This is the right
default for interactive workloads — it makes repeated inference fast and
keeps the prefix cache hot. The tradeoff is that the allocator's
high-water mark grows over the lifetime of the process and never shrinks
back to the OS:

- `--cache-memory-mb` sets the size of the paged KV cache pool, which is
  reserved up front and not returned until the process exits
- `--enable-prefix-cache` retains KV blocks across requests until the
  pool is full, then evicts LRU within the pool
- The MLX Metal allocator pools `free()`d buffers for reuse rather than
  releasing them to the kernel

After a long benchmark sweep — every prompt unique, thousands of requests
— the process can accumulate far more wired memory than the active working
set requires. Restarting the backend gives you the baseline footprint
back.

## How to verify before and after

`ps`/`top` show resident memory (RSS), which excludes Metal/GPU buffers
on Apple Silicon's unified memory architecture. Use `footprint -p <pid>`
for the kernel's complete view, including wired GPU allocations.

```bash
PID=$(pgrep -f "vllm-mlx serve")
footprint -p "$PID" | grep phys_footprint
```

Reference: page size on M-series is 16 KB. `vm_stat`'s "Pages wired down"
× 16 KB = wired bytes.

A freshly respawned vllm-mlx serving a 35B-class MoE model at mxfp4 sits
around 22 GB phys_footprint. A long-running process under heavy benchmark
load can grow several times larger — restarting brings it back to baseline.

## Why `curl /unload` is not enough

llama-swap exposes `POST /unload`, which drops models from its routing
table. The underlying vllm-mlx process keeps running with its Metal
buffers wired. To reclaim that memory you need to stop the process — the
allocator releases everything when vllm-mlx exits, and llama-swap
respawns it on demand.

## Tuning the underlying defaults

The vllm-mlx flags that control allocation are owned by nix-ai's MLX
module:

- `services.aiStack.cacheMemoryMb` → `--cache-memory-mb`
- `services.aiStack.proxy.idleTtl` → llama-swap idle unload TTL

Smaller cache pools mean less memory reserved up front, at the cost of
fewer prefix-cache slots. Idle TTL controls how long an unused model
stays loaded; lowering it frees memory automatically between distinct
workloads. Adjust those in nix-ai when you want a permanent change;
`clear-mem` is the on-demand refresh.

## When `clear-mem` isn't the answer

- **OrbStack VM reservation** (k8s/Docker): `orb stop` if the cluster
  isn't in use.
- **Audio assertions**: `pmset -g assertions | grep -E 'AudioTap|MicrophoneDevice'`.
  Each assertion holds wired buffers in `coreaudiod`. Quit the app
  holding the mic — `pkill coreaudiod` is not safe (system audio breaks
  until next login).
- **Kernel-level fragmentation** after many days of uptime — only a
  reboot clears that.
