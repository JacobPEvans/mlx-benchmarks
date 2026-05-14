# Quick performance reset

When local LLM benchmarks crawl on this M4 Max and you don't want to reboot
or close apps, this is the field manual. Read top to bottom the first time
— the explanations matter because the obvious-looking commands (`curl
/unload`) lie about what they actually do.

## TL;DR

```bash
clear-mem     # shell alias; defined in nix-home/modules/home-manager/zsh/aliases.nix
```

That runs the two kills below and prints the new memory state.

```bash
pkill -9 -f 'vllm-mlx serve'   # the big one
pkill -f pi-coding-agent       # screenpipe's agent loop
vm_stat | grep -E 'Pages (wired|free)'
sysctl vm.swapusage
```

llama-swap respawns vllm-mlx on the next inference request — you don't
need to start anything.

## Why a "small" model balloons to 100+ GB

This is the question you actually want answered. Several mechanisms compound:

### 1. `--cache-memory-mb 32768` is a pool, not a budget

Each vllm-mlx instance is launched with `--cache-memory-mb 32768`, which
reserves a **32 GB** paged KV cache pool up front. vllm-mlx doesn't shrink
it. Even a model that never sees concurrent traffic carries 32 GB of pool
forever.

For the workloads in this registry (`--max-num-seqs 4`, `--max-tokens 8192`)
the working set is ~6–8 GB. 32 GB is a 4x over-reservation.

**Fix:** `--cache-memory-mb 8192`. Already merged in nix-ai PR #764.

### 2. `--enable-prefix-cache` retains KV blocks indefinitely

Prefix caching pins the KV blocks for every prompt prefix it sees so future
requests with the same prefix skip recomputation. There is no TTL on the
prefix cache itself. With lm-eval running thousands of unique GSM8K /
HumanEval problems, every prefix accumulates into the pool until it caps
at `--cache-memory-mb`, at which point eviction is LRU within the pool.

This is great for repeated-prompt workloads (interactive coding, chat) and
costly for benchmark sweeps (every prompt is unique).

**Tradeoff:** Worth keeping enabled for normal use. Use `--disable-prefix-cache`
on the command line for benchmark sweeps if cache growth is the bottleneck.

### 3. `ttl: 0` on the default model means it NEVER unloads

llama-swap's `ttl` controls idle unload. Other models in the registry use
`ttl: 1800` (30 min). The default model had `ttl: 0` — never unload. Every
allocation grows the high-water mark forever; nothing ever resets it.

**Fix:** Normalize TTL across all models (3600s). Already merged in nix-ai PR #764.

### 4. Metal allocator does not return memory to the OS

`mlx-core`'s Metal allocator pools deallocations. Once a buffer is wired it
stays wired and gets reused — `free()` returns memory to the pool, not the
kernel. Combined with #1–3, every burst of activation memory expands the
high-water mark of wired memory and it never comes back.

There is no userland command to drain this pool. `mx.metal.clear_cache()`
exists inside an MLX Python process but nothing calls it periodically, and
it doesn't release memory the kernel has marked wired for the process.

**Only fix:** kill the process. SIGKILL if the system is thrashing — SIGTERM
won't deliver to a process stuck in swap I/O.

### 5. `curl /unload` is a router-level signal, not a process kill

It tells llama-swap to drop the model from its routing table. The vllm-mlx
process keeps running with all its Metal buffers wired. Verified empirically:
115 GB `phys_footprint` after a successful `/unload` returned `OK`.

**This is the trap.** You'll see "unload OK" and assume memory came back. It
didn't. Always verify with `footprint -p <pid>` not `ps`.

## What `ps` doesn't show, and what does

On Apple Silicon unified memory, Metal/GPU buffers are wired to the process
but excluded from RSS. A process can show 10 MB RSS while the kernel holds
115 GB for it.

```bash
PID=$(pgrep -f "vllm-mlx serve")
footprint -p "$PID" | grep phys_footprint
```

Reference: page size on M-series is 16 KB. `vm_stat`'s "Pages wired down"
× 16 KB = wired bytes.

| Scenario | Wired | Free | Swap |
| --- | --- | --- | --- |
| Healthy (1 model loaded, idle) | ~30 GB | >1 GB | 0 |
| Healthy under load | ~40–60 GB | >500 MB | 0 |
| **Sick (this doc's cause)** | **>100 GB** | <100 MB | **>10 GB** |

## The full reset, in order

### 1. Kill vllm-mlx

```bash
pkill -9 -f 'vllm-mlx serve'
```

`-9` (SIGKILL) is the right default here. When the system is thrashing,
the process can be stuck waiting on swap I/O and won't respond to SIGTERM.

### 2. Kill screenpipe's pi-coding-agent

```bash
pkill -f pi-coding-agent
```

Fires every ~6 hours against the default model alias and queues a
multi-turn conversation in front of your benchmark. screenpipe respawns
it on schedule.

### 3. (Optional) Tell llama-swap its view is stale

```bash
curl -s http://localhost:11434/unload
```

Cosmetic after step 1 — llama-swap notices the dead backend on its own.

### 4. Verify

```bash
vm_stat | grep -E 'Pages (wired|free)|Swapouts'
sysctl vm.swapusage
```

After SIGKILL of a bloated vllm-mlx, expect free pages to climb over the
next 30–60 seconds as the kernel reaps the wired allocations and the
page-out backlog drains.

### 5. Find any other hidden-wired processes

`footprint -p` reveals what RSS hides. Common suspects on this box:

```bash
for p in $(pgrep -fl "vllm-mlx|OrbStack Helper vmgr|coreaudiod" | awk '{print $1}'); do
  fp=$(footprint -p "$p" 2>/dev/null | awk '/phys_footprint:/ {print $2,$3; exit}')
  name=$(ps -p "$p" -o comm= 2>/dev/null | head -c 60)
  printf "PID %-7s %-12s %s\n" "$p" "$fp" "$name"
done
```

| Process | Why it hides | Fix |
| --- | --- | --- |
| `vllm-mlx serve` | Metal/GPU buffers (unified memory) | `pkill -9 -f 'vllm-mlx serve'` |
| `OrbStack Helper vmgr` | Linux VM allocates kernel-side | `orb stop` (kills Docker/k8s too) |
| `coreaudiod` | AudioTap assertions park wired buffers | Quit the app holding the mic |

### 6. Audio assertions (structural — no kill safe)

```bash
pmset -g assertions | grep -E 'AudioTap|MicrophoneDevice'
```

Each assertion parks wired buffers in `coreaudiod`. The only safe fix is
to quit the app holding the mic (Zoom, Teams, Wispr Flow, screenpipe audio
capture). `pkill coreaudiod` is **not safe** — launchd respawns it but
system audio breaks until next login.

### 7. Connection leaks (canary, not perf)

```bash
lsof -iTCP:11445 -nP | grep CLOSE_WAIT
```

Growing CLOSE_WAIT on vllm-mlx's port = sloppy client cleanup. Doesn't
slow inference but flags instability — `pkill -9 -f 'vllm-mlx serve'` if
it keeps climbing.

## Permanent fix (deploy the merged config change)

`~/.config/mlx/llama-swap.json` is generated by nix-ai. The config that
caused this incident is fixed in **nix-ai PR #764** (merged), which:

- Drops `cacheMemoryMb` default from 32768 → 8192
- Removes `ttl: 0` on the default model — every model gets uniform idle TTL

Your nix-darwin `flake.lock` pins an older nix-ai rev, so the fix isn't
deployed yet:

```bash
cd ~/git/nix-darwin/main
nix flake update nix-ai
sudo darwin-rebuild switch --flake .
```

After rebuild, `~/.config/mlx/llama-swap.json` regenerates with the new
defaults. Verify with `grep cache-memory-mb ~/.config/mlx/llama-swap.json`
— should print `8192` everywhere, not `32768`.

## What this does NOT fix

- Kernel-level memory fragmentation after days of uptime — only a reboot
  clears that.
- OrbStack VM reservation (`memory_mib: 65536` in `~/.orbstack/vmconfig.json`
  reserves up to 64 GB but only uses what k8s is actively running).
  `orb stop` if you don't need Docker/k8s right now.
- Real Bifrost / network issues — out of scope here.
