"""2 - Who finds the hidden defect? Four learners on the Qiskit circuit's clicks.

The click records come from experiment 1: the perfect simulator (with a perfect detector and with v5's good detector
applied afterwards), and the noisy IBM device simulator (its own readout as the detector, calibrated). Each set is fit
by:
- the physics-shaped QRSM with v5's search (experiment 5's, called unchanged): 0, 1 and 2 defects, the emission and
  the detector known, as a lab would after calibrating them;
- the physics-shaped QRSM plus decoherence: the same shape with one relaxation and one dephasing number per memory
  qubit, started from the search's fit of each size. v5's experiment 5 suggested one relaxation number per defect,
  after a free channel of 64-512 numbers (the grey box) fitted noise instead;
- the free-unitary black box (v5's FreeHybrid at the true memory size, trained as v5 trained it);
- an LSTM, tuned over its size and learning rate on the validation records.
Everything is scored on the 4,096 held-out counting records: log loss, the number of defects the clicks support
(experiment 5's counting rule), and how far the fitted numbers are from the truth in Cramer-Rao standard deviations.

Run with v1's environment, from the hackathon folder (-B writes nothing into v1 or v5):
  & "..\\Quantum research\\.venv\\Scripts\\python.exe" -B experiments\\2_who_finds.py --piece search
  ... --piece learners (free unitary, LSTM, data-efficiency curve) / noise (after search); --report; --quick
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")  # one thread per worker process

import argparse
import functools
import importlib.util
import json
import math
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parents[1]
V5 = HERE.parent / "Quantum research v5"
V1 = HERE.parent / "Quantum research"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sf = _load("search_fix", V5 / "experiments" / "5_search_fix.py")
hd = sf.hd  # experiment 4's module, as the search loaded it: the one to point at the circuit's records
torch.set_default_dtype(torch.float64)
CD = hd.CD
DATA = HERE / "results" / "1_qrsm_circuit" / "data"
OUT = HERE / "results" / "2_who_finds"
T = hd.T_TRAIN

NAMES = ["ideal-k1-perfect", "ideal-k1-good", "ideal-k0-good", "device-k1", "device-k0"]
HARDWARE = ["hardware-k1", "hardware-k0"]  # used when experiments/3_hardware.py has saved them
CURVE = [256, 1024]  # training records for the data-efficiency curve (and the full 4,096), on ideal-k1-good
FREE_ON = ["ideal-k1-perfect", "ideal-k1-good", "device-k1"]
LSTM_ON = ["ideal-k1-perfect", "ideal-k1-good", "device-k1", "device-k0"]
LSTM_HIDDEN, LSTM_LR, LSTM_SEEDS = (16, 64), (3e-3, 1e-2), 1
LSTM_BIG, LSTM_BIG_ON = (128, 3e-3), ["ideal-k1-perfect", "device-k1"]  # timed at 8.5 min a run, so on the two
# headline datasets only; in the timing run it beat hidden 8 (held-out 0.2692 against 0.2719 nats per step)
LSTM_STEPS, LSTM_EVAL, LSTM_PATIENCE = 4000, 50, 12  # Adam steps at most, validation every 50, stop after 12 without gain
NOISE_START = 0.02  # starting relaxation and dephasing per step for the noise-aware fits
NOISE_EVALS = {0: 60, 1: 60, 2: 40}  # L-BFGS evaluations on all the training records: about 2 s each at 1 defect
# and 15 s at 2, so the 2-defect noise-aware fit runs only where the counting needs it (device-k1)
NOISE_K2_ON = ["device-k1"]
EXTRA_START, EXTRA_EVALS = 0.002, {0: 60, 1: 60, 2: 40}  # the third noise-aware model (noise2): a depolarizing chance
# per memory qubit and a fitted dark-count rate, added after the decoherence fits left the drive biased (design log)
EXTRA_ON = {"device-k0": (0, 1), "device-k1": (1, 2), "ideal-k1-perfect": (1,)}
GOOD = hd.GOOD


# ----------------------------------------------------------------------------
# Data, and v5's search pointed at it


def base(name: str) -> str:
    return name.split("@")[0]


def n_train(name: str):
    return int(name.split("@")[1]) if "@" in name else None


def all_names() -> list:
    names = NAMES + [n for n in HARDWARE if (DATA / f"{n}.npz").exists()]
    return names + [f"ideal-k1-good@{n}" for n in CURVE]


@functools.lru_cache(maxsize=None)
def meta(name: str) -> dict:
    return json.loads((DATA / f"{base(name)}.json").read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def records(name: str) -> dict:
    """Training, validation and counting records as v5's search expects them: part -> (X, None). The exact click
    probabilities v5 kept beside each record don't exist for device data, so none are passed."""
    d = np.load(DATA / f"{base(name)}.npz")
    X = {p: torch.from_numpy(d[p].astype(np.int64)) for p in ("train", "val", "count")}
    if n_train(name):
        X["train"] = X["train"][:n_train(name)]
    return {"train": (X["train"], None), "val": (X["val"], None), "test": (X["count"], None)}


def detector(name: str) -> tuple:
    det = meta(name)["detector"]
    return det["eta"], det["p_dark"]


def scored(model, ops: dict, d: dict, eta: float, p_dark: float, k_true: int) -> dict:
    """Replaces v5's scored(), which needed the exact click probabilities: a fit with its log loss on the training,
    validation and counting records (nats; per record on the counting records, for the counting rule)."""
    fit = model.numbers()
    with torch.no_grad():
        U = model.unitary(ops)[None]
        val = hd.run_filter(U, d["val"][0], eta, p_dark)[0][0]
        count = torch.cat([hd.run_filter(U, x, eta, p_dark)[0][0] for x in d["test"][0].split(1024)])
    out = {"fit": fit, "train_nll": sf.mean_nll(ops, model, d["train"][0], eta, p_dark),
           "val_nll": float(val.mean()), "count_nll": count.tolist()}
    if ops["k"] == k_true:
        out["errors"] = hd.aligned(fit, k_true)
    return out


# v5's search reads its datasets through these; pointed at the circuit's records instead. Done at import, so the
# worker processes see it too.
hd.datasets = lambda: {n: (meta(n)["k_true"], n, 0.0) for n in all_names()}
hd.data_for = records
for _n in all_names():
    hd.DETECTORS[_n] = detector(_n)
sf.data_copy = lambda name, copy: records(name)
sf.scored = scored


# ----------------------------------------------------------------------------
# The physics shape plus decoherence


PAULI = [torch.tensor([[0, 1], [1, 0]], dtype=CD), torch.tensor([[0, -1j], [1j, 0]], dtype=CD),
         torch.tensor([[1, 0], [0, -1]], dtype=CD)]


def channel_superop(n: int, relax: torch.Tensor, dephase: torch.Tensor, flip: torch.Tensor = None) -> torch.Tensor:
    """Amplitude damping (relax) then phase damping (dephase) on each of n qubits, as a matrix on the row-major
    vec(rho) that v5's super_filter uses: what the device's T1 and T2 do to an idle qubit. With flip, each qubit is
    then depolarized with that chance (X, Y or Z, a third each): a stand-in for gate errors."""
    d = 2 ** n
    S = torch.eye(d * d, dtype=CD)
    one = torch.tensor(1.0, dtype=CD)
    for q in range(n):
        p, lam = relax[q].to(CD), dephase[q].to(CD)
        zero = torch.zeros((), dtype=CD)
        E = [torch.stack([torch.stack([one, zero]), torch.stack([zero, torch.sqrt(1 - p)])]),
             torch.stack([torch.stack([zero, torch.sqrt(p)]), torch.stack([zero, zero])])]
        F = [torch.stack([torch.stack([one, zero]), torch.stack([zero, torch.sqrt(1 - lam)])]),
             torch.stack([torch.stack([zero, zero]), torch.stack([zero, torch.sqrt(lam)])])]
        left, right = torch.eye(2 ** q, dtype=CD), torch.eye(2 ** (n - 1 - q), dtype=CD)
        embed = lambda K: torch.kron(torch.kron(left, K), right)
        Sq = 0
        for f in F:
            for e in E:
                K = embed(f @ e)
                Sq = Sq + torch.kron(K, K.conj())
        if flip is not None:
            fq = flip[q].to(CD)
            dep = (1 - fq) * torch.eye(d * d, dtype=CD)
            for P in PAULI:
                K = embed(P)
                dep = dep + fq / 3 * torch.kron(K, K.conj())
            Sq = dep @ Sq
        S = Sq @ S
    return S


class NoisyQRSM(nn.Module):
    """The physics shape (theta, phi, zeta) plus, for the emitter and each defect, a relaxation and a dephasing
    chance per step, applied at the start of each step: in the circuit they act while the light is read out and reset,
    between one step's emission and the next drive. Chances are sigmoids of free numbers."""

    def __init__(self, k: int, fit: dict, start: float, extra: bool = False, p_dark: float = None):
        super().__init__()
        self.k, self.extra = k, extra
        self.theta = nn.Parameter(torch.tensor(float(fit["theta"])))
        self.phi = nn.Parameter(torch.tensor(fit["phi"], dtype=torch.float64))
        self.zeta = nn.Parameter(torch.tensor(fit["zeta"], dtype=torch.float64))
        logit = lambda x: math.log(x / (1 - x))
        warm = lambda key, default: [logit(min(max(x, 1e-4), 0.5)) for x in fit.get(key, [default] * (1 + k))]
        self.a = nn.Parameter(torch.tensor(warm("relax", start)))
        self.b = nn.Parameter(torch.tensor(warm("dephase", start)))
        if extra:  # gate errors and the dark counts they add, started small and at the calibration
            self.f = nn.Parameter(torch.tensor(warm("flip", EXTRA_START)))
            self.dark = nn.Parameter(torch.tensor(logit(min(max(fit.get("p_dark", p_dark), 1e-4), 0.5))))

    def unitary(self, ops: dict) -> torch.Tensor:
        return hd.step_unitary(ops, self.theta, self.phi, self.zeta)

    def superops(self, ops: dict, eta: float, p_dark: float) -> tuple:
        if self.extra:
            p_dark = torch.sigmoid(self.dark)
        S1, S0 = hd.superops(ops, self.unitary(ops), eta, p_dark)
        D = channel_superop(1 + self.k, torch.sigmoid(self.a), torch.sigmoid(self.b),
                            torch.sigmoid(self.f) if self.extra else None)
        return S1 @ D, S0 @ D

    def numbers(self) -> dict:
        out = {"theta": self.theta.item(), "phi": self.phi.tolist(), "zeta": self.zeta.tolist(),
               "relax": torch.sigmoid(self.a).tolist(), "dephase": torch.sigmoid(self.b).tolist()}
        if self.extra:
            out.update({"flip": torch.sigmoid(self.f).tolist(), "p_dark": torch.sigmoid(self.dark).item()})
        return out


def noisy_superops_at(k: int, v: torch.Tensor, ops: dict, eta: float, p_dark: float, extra: bool = False) -> tuple:
    """The noise-aware model's step from one flat vector (theta, phi, zeta, relax, dephase, and with extra: flip and
    the dark-count rate), for the Hessian."""
    th, ph, ze = v[0], v[1:1 + k], v[1 + k:1 + 2 * k]
    relax, deph = v[1 + 2 * k:2 + 3 * k], v[2 + 3 * k:3 + 4 * k]
    flip = v[3 + 4 * k:4 + 5 * k].clamp(1e-9, 1) if extra else None
    if extra:
        p_dark = v[4 + 5 * k].clamp(1e-9, 1)
    S1, S0 = hd.superops(ops, hd.step_unitary(ops, th, ph, ze), eta, p_dark)
    D = channel_superop(1 + k, relax.clamp(1e-9, 1), deph.clamp(1e-9, 1), flip)
    return S1 @ D, S0 @ D


def sd_from_hessian(f, v0: torch.Tensor) -> list:
    H = torch.autograd.functional.hessian(f, v0).numpy()
    try:
        return np.sqrt(np.clip(np.diag(np.linalg.inv(H)), 0, None)).tolist()
    except np.linalg.LinAlgError:
        return [float("nan")] * len(v0)


def physics_sd(name: str, k: int, fit: dict) -> list:
    """Cramer-Rao standard deviations at a physics fit, from all the training records, in the order theta, then phi
    and zeta per defect (as hd.fisher_sd, with the circuit's records)."""
    if k == 0:
        X = records(name)["train"][0]
        ops = hd.register_ops(0)
        eta, p_dark = detector(name)
        return sd_from_hessian(lambda v: hd.super_filter(*hd.superops(ops, hd.step_unitary(ops, v[0], v[1:1], v[1:1]),
                                                                      eta, p_dark), X).sum(),
                               torch.tensor([fit["theta"]]))
    return hd.fisher_sd(name, fit, k)


def noise_run(job: dict) -> dict:
    """The noise-aware fit of one size, started from the search's fit of that size with a small relaxation and
    dephasing, polished with full-batch L-BFGS on all the training records. Cramer-Rao standard deviations at the
    true size only (the Hessian at 2 defects would cost as much as the fit)."""
    torch.set_num_threads(1)
    name, k = job["data"], job["k"]
    k_true = meta(name)["k_true"]
    eta, p_dark = detector(name)
    d = records(name)
    Xtr = d["train"][0]
    part = json.loads(Path(job["from_part"]).read_text(encoding="utf-8"))
    fit = part["fit"] if part["kind"] == "noise" else part[f"fit{k}"]["fit"]  # warm start from a noise-aware fit
    ops = hd.register_ops(k)
    t0 = time.perf_counter()
    extra = job.get("extra", False)
    model = NoisyQRSM(k, fit, job["start"], extra, p_dark)
    evals = sf.polish(model, lambda: model.superops(ops, eta, p_dark), Xtr, job["evals"])
    with torch.no_grad():
        S1, S0 = model.superops(ops, eta, p_dark)
        train = float(sum(hd.super_filter(S1, S0, x).sum() for x in Xtr.split(1024)) / len(Xtr))
        val = sf.super_probs(S1, S0, d["val"][0])[0]
        count = torch.cat([sf.super_probs(S1, S0, x)[0] for x in d["test"][0].split(1024)])
    nums = model.numbers()
    out = {**{key: job[key] for key in ("key", "kind", "data", "k", "start", "evals")}, "k_true": k_true,
           "extra": extra, "fit": nums, "polish_evals": evals, "train_nll": train, "val_nll": float(val.mean()),
           "count_nll": count.tolist()}
    if extra:
        if k == k_true and k > 0:
            out["errors"] = hd.aligned(nums, k)
    elif k == k_true:
        v0 = torch.tensor([nums["theta"]] + nums["phi"] + nums["zeta"] + nums["relax"] + nums["dephase"])
        out["sd_flat"] = sd_from_hessian(
            lambda v: hd.super_filter(*noisy_superops_at(k, v, ops, eta, p_dark), Xtr).sum(), v0)
        if k > 0:
            out["errors"] = hd.aligned(nums, k)
    out["seconds"] = time.perf_counter() - t0
    return out


# ----------------------------------------------------------------------------
# The free-unitary black box and the LSTM


def free_run(job: dict) -> dict:
    """v5's free_run (experiment 4) on the circuit's records: the free-unitary hybrid at memory size D, Adam from a
    random start with experiment 1's short-to-long schedule. Scored by log loss instead of the exact probabilities."""
    torch.set_num_threads(1)
    name, D, seed = job["data"], job["D"], job["seed"]
    d = records(name)
    Xtr = d["train"][0]
    gen = torch.Generator().manual_seed(seed)
    model = hd.FreeHybrid(D, gen)
    rng = np.random.default_rng(seed)
    opt = torch.optim.Adam(model.parameters(), lr=job["lr"])
    schedule = job["schedule"]
    total = sum(steps for _, steps in schedule)
    decay = torch.optim.lr_scheduler.CosineAnnealingLR(opt, total)
    t0 = time.perf_counter()
    for Tn, steps in schedule:
        for _ in range(steps):
            batch = Xtr[torch.from_numpy(rng.integers(0, len(Xtr), hd.BATCH))][:, :Tn]
            K = model.kraus()
            S1, S0 = (sum(torch.kron(K[x, a], K[x, a].conj()) for a in range(2)) for x in (1, 0))
            loss = hd.super_filter(S1, S0, batch).sum() / batch.numel()
            opt.zero_grad()
            if torch.isfinite(loss):
                loss.backward()
                if torch.isfinite(model.M.grad).all():
                    opt.step()
            decay.step()
    with torch.no_grad():
        K = model.kraus()
        val = hd.free_filter(K, d["val"][0])[0]
        count = torch.cat([hd.free_filter(K, x)[0] for x in d["test"][0].split(1024)])
    return {**{key: job[key] for key in ("key", "kind", "data", "D", "seed", "lr")}, "numbers": 2 * 4 * D * D,
            "val_nll": float(val.mean()), "count_nll": count.tolist(), "seconds": time.perf_counter() - t0}


class ClickLSTM(nn.Module):
    """A next-click predictor: an LSTM reads the previous click (and a first-step flag) and outputs P(click now)."""

    def __init__(self, hidden: int):
        super().__init__()
        self.lstm = nn.LSTM(2, hidden, batch_first=True)
        self.out = nn.Linear(hidden, 1)

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        S, Tn = X.shape
        prev = torch.cat([torch.zeros(S, 1, dtype=torch.float32), X[:, :-1].float()], 1)
        first = torch.zeros(S, Tn, dtype=torch.float32)
        first[:, 0] = 1
        h, _ = self.lstm(torch.stack([prev, first], -1))
        return self.out(h).squeeze(-1)


def lstm_nll(model: ClickLSTM, X: torch.Tensor) -> torch.Tensor:
    """Negative log-likelihood per record (nats)."""
    with torch.no_grad():
        logits = model(X)
        return nn.functional.binary_cross_entropy_with_logits(logits, X.float(), reduction="none").sum(1).double()


def lstm_run(job: dict) -> dict:
    """Adam on random batches of 256 training records, validation every LSTM_EVAL steps, early stopping; the best
    validation state is kept. Runs in float32, as LSTMs usually do."""
    torch.set_num_threads(1)
    name = job["data"]
    d = records(name)
    Xtr, Xva, Xco = d["train"][0], d["val"][0], d["test"][0]
    torch.manual_seed(job["seed"])
    model = ClickLSTM(job["hidden"]).float()
    rng = np.random.default_rng(job["seed"])
    opt = torch.optim.Adam(model.parameters(), lr=job["lr"])
    t0 = time.perf_counter()
    best, best_state, since, steps = float("inf"), None, 0, 0
    for step in range(1, job["max_steps"] + 1):
        batch = Xtr[torch.from_numpy(rng.integers(0, len(Xtr), min(hd.BATCH, len(Xtr))))]
        loss = nn.functional.binary_cross_entropy_with_logits(model(batch), batch.float())
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % job["eval"] == 0:
            v = float(lstm_nll(model, Xva).mean())
            if v < best - 1e-4:
                best, best_state, since, steps = v, {k: t.clone() for k, t in model.state_dict().items()}, 0, step
            else:
                since += 1
                if since >= job["patience"]:
                    break
    model.load_state_dict(best_state)
    count = lstm_nll(model, Xco)
    return {**{key: job[key] for key in ("key", "kind", "data", "hidden", "lr", "seed")},
            "numbers": sum(p.numel() for p in model.parameters()), "val_nll": best, "best_step": steps,
            "count_nll": count.tolist(), "seconds": time.perf_counter() - t0}


# ----------------------------------------------------------------------------
# Jobs


def run_one(job: dict) -> dict:
    return {"one": sf.search_one, "two": sf.search_two, "noise": noise_run, "free": free_run,
            "lstm": lstm_run}[job["kind"]](job)


def part_path(parts: Path, key: str) -> Path:
    return parts / (re.sub(r"[^A-Za-z0-9_.=@-]+", "_", key) + ".json")


def search_settings(quick: bool) -> tuple:
    if quick:
        return ({"grid": 5, "screen": 64, "candidates": 2, "refine_one": 10, "polish": 1},
                {"grid_phi": 4, "grid_zeta": 6, "bases": 2, "candidates_add": 1, "candidates_split": 1,
                 "refine_add": (5, 5), "keep_add": 2, "polish": 1})
    return ({"grid": sf.GRID_ONE, "screen": sf.SCREEN_RECORDS, "candidates": sf.CANDIDATES_ONE,
             "refine_one": sf.REFINE_ONE, "polish": sf.POLISH},
            {"grid_phi": sf.GRID_PHI, "grid_zeta": sf.GRID_ZETA, "bases": sf.BASES, "candidates_add": sf.CANDIDATES_ADD,
             "candidates_split": sf.CANDIDATES_SPLIT, "refine_add": sf.REFINE_ADD, "keep_add": sf.KEEP_ADD,
             "polish": sf.POLISH})


def one_key(name: str, one: dict) -> str:
    return sf.search_key("one", name, 0, one, None)


def two_key(name: str, one: dict, two: dict) -> str:
    return sf.search_key("two", name, 0, one, two)


def jobs_for(piece: str, quick: bool, parts: Path, only: list = None) -> list:
    one, two = search_settings(quick)
    names = [n for n in all_names() if "@" not in n]
    if only:
        names = [n for n in names if n in only]
    jobs = []
    if piece == "search":
        for name in names + ([] if only else [f"ideal-k1-good@{n}" for n in CURVE]):
            screen = min(one["screen"], n_train(name) or one["screen"])
            o = {**one, "screen": screen}
            jobs.append({"key": one_key(name, o), "kind": "one", "data": name, "copy": 0, **o,
                         "cost": 1 + meta(name)["k_true"]})
            if meta(name)["k_true"] >= 1 and "@" not in name:  # 2 defects, for counting on the 1-defect data
                jobs.append({"key": two_key(name, o, two), "kind": "two", "data": name, "copy": 0, "screen": screen,
                             **two, "one_part": str(part_path(parts, one_key(name, o))), "after": one_key(name, o),
                             "cost": 10})
    elif piece == "noise":
        for name in names:
            k_true = meta(name)["k_true"]
            # every size for counting on the device data and the 0-defect control; elsewhere the true size, to see
            # whether the noise-aware shape invents noise in clean data
            sizes = [k for k in sf.SIZES[k_true] if k < 2 or name in NOISE_K2_ON]
            if name.startswith("ideal") and k_true == 1:
                sizes = [1]
            for k in sizes:
                src = one_key(name, one) if k < 2 else two_key(name, one, two)
                evals = 4 if quick else NOISE_EVALS[k]
                if part_path(parts, src).exists():
                    jobs.append({"key": f"noise {name} k{k} start{NOISE_START} evals{evals} from {src}",
                                 "kind": "noise", "data": name, "k": k, "start": NOISE_START, "evals": evals,
                                 "from_part": str(part_path(parts, src)), "cost": 4 ** k})
    elif piece == "noise2":  # warm-started from each decoherence fit
        for name in names:
            for k in EXTRA_ON.get(name, ()):
                src = one_key(name, one) if k < 2 else two_key(name, one, two)
                evals = 4 if quick else NOISE_EVALS[k]
                noise_key = f"noise {name} k{k} start{NOISE_START} evals{evals} from {src}"
                if part_path(parts, noise_key).exists():
                    e2 = 4 if quick else EXTRA_EVALS[k]
                    jobs.append({"key": f"noise2 {name} k{k} start{EXTRA_START} evals{e2} from {noise_key}",
                                 "kind": "noise", "extra": True, "data": name, "k": k, "start": NOISE_START,
                                 "evals": e2, "from_part": str(part_path(parts, noise_key)), "cost": 4 ** k})
    elif piece == "learners":
        schedule = [(2, 5), (4, 5), (8, 5)] if quick else hd.FREE_SCHEDULE
        for name in [n for n in names if n in FREE_ON]:
            D = 2 ** (1 + meta(name)["k_true"])
            for lr in hd.FREE_RATES:
                for seed in range(1 if quick else hd.FREE_SEEDS):
                    jobs.append({"key": f"free {name} D{D} lr{lr} seed{seed}" + (" quick" if quick else ""),
                                 "kind": "free", "data": name, "D": D, "lr": lr, "seed": seed, "schedule": schedule,
                                 "cost": 3})
        lstm_names = [n for n in names if n in LSTM_ON] + ([] if only else [f"ideal-k1-good@{n}" for n in CURVE])
        for name in lstm_names:
            configs = [(h, lr) for h in ((8,) if quick else LSTM_HIDDEN) for lr in ((1e-2,) if quick else LSTM_LR)]
            if name in LSTM_BIG_ON and not quick:
                configs.append(LSTM_BIG)
            for hidden, lr in configs:
                for seed in range(1 if quick else LSTM_SEEDS):
                    jobs.append({"key": f"lstm {name} h{hidden} lr{lr} seed{seed}" + (" quick" if quick else ""),
                                 "kind": "lstm", "data": name, "hidden": hidden, "lr": lr, "seed": seed,
                                 "max_steps": 100 if quick else LSTM_STEPS, "eval": 25 if quick else LSTM_EVAL,
                                 "patience": 2 if quick else LSTM_PATIENCE, "cost": 1 + hidden / 64})
    return jobs


def run_jobs(jobs: list, parts: Path, workers: int) -> None:
    """Costliest first; a job with "after" starts once that part exists (as v5's run_jobs)."""
    parts.mkdir(parents=True, exist_ok=True)
    todo = sorted([j for j in jobs if not part_path(parts, j["key"]).exists()], key=lambda j: -j["cost"])
    print(f"  {len(jobs) - len(todo)} cached, {len(todo)} to run", flush=True)
    t0 = time.time()
    ready = lambda j: "after" not in j or part_path(parts, j["after"]).exists()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        running = {}
        while todo or running:
            for j in [j for j in todo if ready(j)][:max(0, workers - len(running))]:
                running[pool.submit(run_one, j)] = j
                todo.remove(j)
            done = next(as_completed(running))
            running.pop(done)
            r = done.result()
            part_path(parts, r["key"]).write_text(json.dumps(r), encoding="utf-8")
            fit = r.get("fit2") or r.get("fit1") or r
            print(f"  {time.time() - t0:5.0f} s  {r['key']}: held-out loss {np.mean(fit['count_nll']) / T:.5f} "
                  f"nats per step, {r['seconds'] / 60:.1f} min", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--piece", nargs="+", choices=["search", "noise", "noise2", "learners"])
    ap.add_argument("--only", nargs="+", help="only these datasets (for the hardware records)")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=5)
    args = ap.parse_args()
    out = OUT / "quick" if args.quick else OUT
    parts = out / "parts"
    if args.piece:
        t0 = time.time()
        for piece in args.piece:  # in order: noise needs the search's parts
            run_jobs(jobs_for(piece, args.quick, parts, args.only), parts, args.workers)
        print(f"done in {(time.time() - t0) / 60:.1f} min", flush=True)
    if args.report:
        report_mod = _load("who_finds_report", HERE / "experiments" / "2_report.py")
        report_mod.report(out, sys.modules[__name__])


if __name__ == "__main__":
    main()
