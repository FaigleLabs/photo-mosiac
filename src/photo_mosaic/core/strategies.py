from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from photo_mosaic.core.tile_index import TileDescriptor


@dataclass(slots=True)
class SelectionContext:
    max_repeats: int | None
    max_usage_percent: float | None
    total_tiles: int


def build_usage_limit(ctx: SelectionContext) -> int | None:
    limits: list[int] = []
    if ctx.max_repeats is not None:
        limits.append(ctx.max_repeats)
    if ctx.max_usage_percent is not None:
        limits.append(max(1, math.floor((ctx.max_usage_percent / 100.0) * ctx.total_tiles)))
    if not limits:
        return None
    return min(limits)


def _score(assign: list[int], source_cell_rgbs: np.ndarray, tile_colors: np.ndarray) -> float:
    selected = tile_colors[np.array(assign)]
    return float(np.mean(np.sum((selected - source_cell_rgbs) ** 2, axis=1)))


def greedy_assign(
    source_cell_rgbs: np.ndarray,
    tiles: list[TileDescriptor],
    ctx: SelectionContext,
) -> list[int]:
    if not tiles:
        raise ValueError("No tile images found")

    tile_colors = np.array([t.avg_rgb for t in tiles], dtype=np.float32)
    assignments: list[int] = []
    usage = defaultdict(int)
    usage_limit = build_usage_limit(ctx)

    for source_rgb in source_cell_rgbs:
        dists = np.sum((tile_colors - source_rgb) ** 2, axis=1)
        for idx in np.argsort(dists):
            if usage_limit is None or usage[idx] < usage_limit:
                usage[idx] += 1
                assignments.append(int(idx))
                break
        else:
            # If all limits are exhausted, relax constraints for completion.
            idx = int(np.argmin(dists))
            usage[idx] += 1
            assignments.append(idx)
    return assignments


def lazy_assign(
    source_cell_rgbs: np.ndarray,
    tiles: list[TileDescriptor],
    ctx: SelectionContext,
    top_k: int,
    randomness: float,
    seed: int = 7,
) -> list[int]:
    if not tiles:
        raise ValueError("No tile images found")

    rng = random.Random(seed)
    tile_colors = np.array([t.avg_rgb for t in tiles], dtype=np.float32)
    assignments: list[int] = []
    usage = defaultdict(int)
    usage_limit = build_usage_limit(ctx)

    for source_rgb in source_cell_rgbs:
        dists = np.sum((tile_colors - source_rgb) ** 2, axis=1)
        candidate_indices = np.argsort(dists)[: max(1, min(top_k, len(tiles)))].tolist()

        if rng.random() < randomness:
            rng.shuffle(candidate_indices)

        selected_idx: int | None = None
        for idx in candidate_indices:
            idx_int = int(idx)
            if usage_limit is None or usage[idx_int] < usage_limit:
                selected_idx = idx_int
                break

        if selected_idx is None:
            for idx in np.argsort(dists):
                idx_int = int(idx)
                if usage_limit is None or usage[idx_int] < usage_limit:
                    selected_idx = idx_int
                    break

        if selected_idx is None:
            selected_idx = int(np.argmin(dists))

        usage[selected_idx] += 1
        assignments.append(selected_idx)

    return assignments


def random_improve_assign(
    source_cell_rgbs: np.ndarray,
    tiles: list[TileDescriptor],
    initial_assignments: list[int],
    steps: int,
    seed: int = 7,
) -> list[int]:
    if steps <= 0:
        return initial_assignments

    rng = random.Random(seed)
    tile_colors = np.array([t.avg_rgb for t in tiles], dtype=np.float32)
    assignments = initial_assignments[:]

    best = assignments[:]
    best_score = _score(best, source_cell_rgbs, tile_colors)

    for _ in range(steps):
        i = rng.randrange(len(assignments))
        j = rng.randrange(len(assignments))
        if i == j:
            continue
        candidate = assignments[:]
        candidate[i], candidate[j] = candidate[j], candidate[i]
        cand_score = _score(candidate, source_cell_rgbs, tile_colors)
        if cand_score < best_score:
            best_score = cand_score
            best = candidate
            assignments = candidate
    return best


def full_optimize_assign(
    source_cell_rgbs: np.ndarray,
    tiles: list[TileDescriptor],
    initial_assignments: list[int],
    ctx: SelectionContext,
    steps: int,
    seed: int = 7,
) -> list[int]:
    if steps <= 0:
        return initial_assignments

    rng = random.Random(seed)
    tile_colors = np.array([t.avg_rgb for t in tiles], dtype=np.float32)
    assignments = initial_assignments[:]
    usage_limit = build_usage_limit(ctx)
    usage = defaultdict(int)
    for idx in assignments:
        usage[idx] += 1

    current_score = _score(assignments, source_cell_rgbs, tile_colors)
    best = assignments[:]
    best_score = current_score

    for _ in range(steps):
        pos = rng.randrange(len(assignments))
        old_idx = assignments[pos]

        local_dists = np.sum((tile_colors - source_cell_rgbs[pos]) ** 2, axis=1)
        shortlist = np.argsort(local_dists)[: min(20, len(tiles))]
        cand_idx = int(rng.choice(shortlist.tolist()))
        if cand_idx == old_idx:
            continue

        if usage_limit is not None and usage[cand_idx] >= usage_limit:
            continue

        candidate = assignments[:]
        candidate[pos] = cand_idx
        cand_score = _score(candidate, source_cell_rgbs, tile_colors)

        if cand_score <= current_score:
            assignments = candidate
            current_score = cand_score
            usage[old_idx] -= 1
            usage[cand_idx] += 1
            if cand_score < best_score:
                best_score = cand_score
                best = candidate

    return best
