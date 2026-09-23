#!/usr/bin/env python3
"""
e366_audit.py - Epoch 366 in-epoch SPRT false invalidation

Mechanism (verified on chain):
  Shortly after the first mainnet devshard settlements, the old in-epoch SPRT
  on invalid inferences tripped on a small sample. Two hosts were excluded
  with reason statistical_invalidations and received zero epoch-366 reward.
  Governance proposal 96 later raised invalidation_h_threshold from 4 to 40
  so a few early invalids cannot trip the check.

Detection:
  Read excluded_participants/{epoch} and keep only
  reason == statistical_invalidations. Default scan window 350..380 is used
  to show the reason appears only in epoch 366.

Compensation:
  gross_cw = confirmation_weight * fixedEpochReward(E) / rootTotalWeight(E)
             - actual_rewarded_ngonka

  rootTotalWeight(E) is parent EpochGroupData.total_weight from
  epoch_group_data/{E} with model_id == "".
  fixedEpochReward(E) is initial * exp(decay_rate * (E - genesis)) from
  inference.params.bitcoin_reward_params.

  For epoch 366 the chain-exact direct amounts then apply the 5% Kimi
  delegation from gonka1scskt to gonka1gvrrhj. scskt keeps 95% of its CW
  share. The other 5%, plus the 30% power-cap delta on gvrrhj, is an
  indirect row. Paying both the full CW share and that 5% would double count.

Outputs (./output/):
  - e366_per_participant.csv   : STAT victims and recommended amounts
  - e366_exclusions.csv        : every exclusion in the audited epoch
  - e366_neighbor_epochs.csv   : 365/366/367 payout vs formula check
  - e366_summary.json          : totals, policy notes, proposal 96
  - e366_log.txt               : full RPC trace
  - raw_chain/                 : cached JSON used by the last run

Usage:
  python3 e366_audit.py
  python3 e366_audit.py --epoch 366 --scan-lo 350 --scan-hi 380
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
import urllib.request
from decimal import Decimal, getcontext
from typing import Any

getcontext().prec = 50

DEFAULT_RPC = "http://node2.gonka.ai:8000"
STAT_REASON = "statistical_invalidations"
PROPOSAL_ID = 96
NG = Decimal(10) ** 9
# Epoch 366 delegation snapshot: 5% of scskt reward weight transfers to gvrrhj
# (Kimi delegation). Neighbor epoch 365 pays scskt at 0.9500 of CW share.
DELEGATOR = "gonka1scskt6wpnjnumsah6kjphmdu87vjgvcxmn4rxv"
DELEGATEE = "gonka1gvrrhjmy4w4mayvs2s5l23edj8ertcmtd2v4zr"
DELEGATION_SHARE = Decimal("0.05")
# Archive estimate_bitcoin_reward: gvrrhj reward weight falls 84847 -> 74370
# in the scskt exclusion block, because the 30% cap is checked only on ACTIVE
# hosts. Public nodes do not serve that historical query; the weights are the
# reviewed chain observation and the GNK delta is computed here.
CAP_WEIGHT_BEFORE = 84847
CAP_WEIGHT_AFTER = 74370
HTTP_TIMEOUT = 20
HTTP_RETRIES = 3

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
RAW_DIR = os.path.join(OUT_DIR, "raw_chain")
LOG_PATH = os.path.join(OUT_DIR, "e366_log.txt")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def http_get(url: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            time.sleep(0.4 * attempt)
    log(f"  WARN: GET {url} failed after {HTTP_RETRIES} retries: {last_err}")
    return {}


def slug(path: str) -> str:
    return path.strip("/").replace("/", "_").replace("?", "_").replace("=", "_").replace("&", "_")


def fetch_json(rpc: str, path: str, cache: bool = True) -> dict:
    url = f"{rpc}{path}"
    body = http_get(url)
    if cache and body:
        out = os.path.join(RAW_DIR, slug(path) + ".json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)
    return body


def gonka(ngonka: int) -> str:
    return str((Decimal(ngonka) / NG).quantize(Decimal("0.000001")))


def fixed_to_decimal(fp: Any) -> Decimal:
    if isinstance(fp, dict):
        return Decimal(str(fp.get("value"))) * (Decimal(10) ** int(fp.get("exponent", 0)))
    return Decimal(str(fp or 0))


def theoretical_reward_ngonka(params: dict, epoch: int) -> int:
    br = params.get("bitcoin_reward_params") or {}
    initial = Decimal(str(br.get("initial_epoch_reward") or "0"))
    decay = fixed_to_decimal(br.get("decay_rate"))
    genesis = int(str(br.get("genesis_epoch") or "1"))
    elapsed = max(0, epoch - genesis)
    return int((initial * Decimal(math.exp(float(decay) * elapsed))).to_integral_value())


def share_ngonka(numerator: int, total_weight: int, epoch_reward: int) -> int:
    if not total_weight or not numerator:
        return 0
    return int((Decimal(numerator) * Decimal(epoch_reward) / Decimal(total_weight)).to_integral_value())


def block_time(rpc: str, height: int) -> str:
    body = fetch_json(rpc, f"/chain-rpc/block?height={height}")
    return ((body.get("result") or {}).get("block") or {}).get("header", {}).get("time") or ""


def excluded(rpc: str, epoch: int) -> list[dict]:
    body = fetch_json(rpc, f"/chain-api/productscience/inference/inference/excluded_participants/{epoch}")
    return body.get("items") or []


def epoch_group(rpc: str, epoch: int) -> dict:
    body = fetch_json(rpc, f"/chain-api/productscience/inference/inference/epoch_group_data/{epoch}")
    return body.get("epoch_group_data") or {}


def performance(rpc: str, epoch: int, addr: str) -> dict:
    body = fetch_json(
        rpc,
        f"/chain-api/productscience/inference/inference/epoch_performance_summary/{epoch}/{addr}",
    )
    return body.get("epochPerformanceSummary") or {}


def members_of(grp: dict) -> dict[str, dict]:
    return {v.get("member_address"): v for v in (grp.get("validation_weights") or [])}


def write_csv(path: str, rows: list[dict]) -> None:
    fields: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    if not fields:
        fields = ["address"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rpc", default=DEFAULT_RPC)
    parser.add_argument("--epoch", type=int, default=366)
    parser.add_argument("--scan-lo", type=int, default=350)
    parser.add_argument("--scan-hi", type=int, default=380)
    parser.add_argument("--proposal-id", type=int, default=PROPOSAL_ID)
    args = parser.parse_args()

    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    log(f"rpc={args.rpc} epoch={args.epoch} scan={args.scan_lo}..{args.scan_hi}")

    params = fetch_json(args.rpc, "/chain-api/productscience/inference/inference/params").get("params") or {}
    vp = params.get("validation_params") or {}
    er = theoretical_reward_ngonka(params, args.epoch)
    grp = epoch_group(args.rpc, args.epoch)
    tw = int(grp.get("total_weight") or 0)
    members = members_of(grp)
    exc = excluded(args.rpc, args.epoch)

    log(
        f"epoch {args.epoch} members={len(members)} total_weight={tw} "
        f"theoretical={gonka(er)} GNK exclusions={len(exc)}"
    )
    log(
        f"live SPRT params invalidation_h_threshold={vp.get('invalidation_h_threshold')} "
        f"bad_participant_invalidation_rate={vp.get('bad_participant_invalidation_rate')}"
    )

    paid = 0
    for addr in members:
        rec = performance(args.rpc, args.epoch, addr)
        paid += int(rec.get("rewarded_coins") or 0)
    log(f"actual paid pool in epoch {args.epoch}: {gonka(paid)} GNK")

    log(f"scanning statistical_invalidations in {args.scan_lo}..{args.scan_hi}")
    scan_hits = []
    for epoch in range(args.scan_lo, args.scan_hi + 1):
        items = excluded(args.rpc, epoch)
        stat = [i for i in items if i.get("reason") == STAT_REASON]
        if stat:
            scan_hits.append({"epoch": epoch, "count": len(stat), "addresses": [i.get("address") for i in stat]})
            log(f"  epoch {epoch}: {len(stat)} statistical_invalidations")
    if not scan_hits:
        log("  no statistical_invalidations in scan window")

    proposal = fetch_json(
        args.rpc, f"/chain-api/cosmos/gov/v1/proposals/{args.proposal_id}"
    ).get("proposal") or {}
    log(
        f"proposal {args.proposal_id} status={proposal.get('status')} "
        f"expedited={proposal.get('expedited')} title={proposal.get('title')}"
    )

    exclusion_rows = []
    for item in exc:
        addr = item.get("address") or ""
        vw = members.get(addr) or {}
        rec = performance(args.rpc, args.epoch, addr)
        weight = int(vw.get("weight") or 0)
        cw = int(vw.get("confirmation_weight") or 0)
        inf = int(rec.get("inference_count") or 0)
        inv = int(rec.get("invalidated_inferences") or 0)
        miss = int(rec.get("missed_requests") or 0)
        actual = int(rec.get("rewarded_coins") or 0)
        lost_w = max(0, share_ngonka(weight, tw, er) - actual)
        lost_cw = max(0, share_ngonka(cw, tw, er) - actual)
        height = int(item.get("exclusion_block_height") or 0)
        row = {
            "epoch": args.epoch,
            "address": addr,
            "reason": item.get("reason") or "",
            "eligible": "yes" if item.get("reason") == STAT_REASON else "no",
            "exclusion_block_height": height,
            "exclusion_time_utc": block_time(args.rpc, height) if height else "",
            "weight": weight,
            "confirmation_weight": cw,
            "cw_over_weight": (cw / weight) if weight else 0.0,
            "inference_count": inf,
            "invalidated_inferences": inv,
            "invalid_rate": (inv / inf) if inf else 0.0,
            "missed_requests": miss,
            "actual_rewarded_ngonka": actual,
            "actual_rewarded_gonka": gonka(actual),
            "lost_by_weight_ngonka": lost_w,
            "lost_by_confirmation_weight_ngonka": lost_cw,
            "lost_by_weight_gonka": gonka(lost_w),
            "lost_by_confirmation_weight_gonka": gonka(lost_cw),
            "recommended_lost_ngonka": lost_cw,
            "recommended_lost_gonka": gonka(lost_cw),
            "root_total_weight": tw,
            "theoretical_reward_ngonka": er,
            "denominator_mode": "root_total_weight",
        }
        exclusion_rows.append(row)
        log(
            f"  {row['reason']} {addr} w={weight} cw={cw} "
            f"inval={row['invalid_rate']*100:.2f}% actual={gonka(actual)} "
            f"lost_cw={row['lost_by_confirmation_weight_gonka']}"
        )

    victims = [r for r in exclusion_rows if r["reason"] == STAT_REASON]
    excluded_other = [r for r in exclusion_rows if r["reason"] != STAT_REASON]

    epoch_vp = grp.get("validation_params") or {}
    log(
        f"epoch-snapshot SPRT bad_rate={epoch_vp.get('bad_participant_invalidation_rate')} "
        f"H={epoch_vp.get('invalidation_h_threshold')}"
    )

    delegation_transfer_weight = 0
    for row in victims:
        row["delegation_share"] = "0"
        row["delegation_transfer_weight"] = 0
        row["reward_weight_after_delegation"] = row["confirmation_weight"]
        row["naive_cw_lost_ngonka"] = row["lost_by_confirmation_weight_ngonka"]
        row["naive_cw_lost_gonka"] = row["lost_by_confirmation_weight_gonka"]
        if args.epoch == 366 and row["address"] == DELEGATOR:
            transfer = int((Decimal(row["confirmation_weight"]) * DELEGATION_SHARE).to_integral_value())
            kept = row["confirmation_weight"] - transfer
            kept_share = share_ngonka(kept, tw, er)
            lost = max(0, kept_share - row["actual_rewarded_ngonka"])
            delegation_transfer_weight = transfer
            row["delegation_share"] = str(DELEGATION_SHARE)
            row["delegation_transfer_weight"] = transfer
            row["reward_weight_after_delegation"] = kept
            row["recommended_lost_ngonka"] = lost
            row["recommended_lost_gonka"] = gonka(lost)
            log(f"  delegation {DELEGATOR[:18]} keeps {kept} of cw, transfer {transfer} -> {DELEGATEE[:18]}")

    indirect = None
    if args.epoch == 366 and delegation_transfer_weight:
        cap_before = share_ngonka(CAP_WEIGHT_BEFORE, tw, er)
        cap_after = share_ngonka(CAP_WEIGHT_AFTER, tw, er)
        cap_ng = max(0, cap_before - cap_after)
        deleg_ng = share_ngonka(delegation_transfer_weight, tw, er)
        gv = members.get(DELEGATEE) or {}
        gv_rec = performance(args.rpc, args.epoch, DELEGATEE)
        indirect = {
            "address": DELEGATEE,
            "role": "indirect_delegatee_and_power_cap",
            "eligible_if": "GRC accepts indirect loss",
            "weight": int(gv.get("weight") or 0),
            "confirmation_weight": int(gv.get("confirmation_weight") or 0),
            "actual_rewarded_ngonka": int(gv_rec.get("rewarded_coins") or 0),
            "actual_rewarded_gonka": gonka(int(gv_rec.get("rewarded_coins") or 0)),
            "cap_weight_before": CAP_WEIGHT_BEFORE,
            "cap_weight_after": CAP_WEIGHT_AFTER,
            "cap_loss_ngonka": cap_ng,
            "cap_loss_gonka": gonka(cap_ng),
            "delegation_in_weight": delegation_transfer_weight,
            "delegation_in_ngonka": deleg_ng,
            "delegation_in_gonka": gonka(deleg_ng),
            "recommended_lost_ngonka": cap_ng + deleg_ng,
            "recommended_lost_gonka": gonka(cap_ng + deleg_ng),
        }
        log(
            f"  indirect {DELEGATEE[:18]} cap={indirect['cap_loss_gonka']} "
            f"deleg_in={indirect['delegation_in_gonka']} total={indirect['recommended_lost_gonka']}"
        )

    neighbor_rows = []
    for epoch in (args.epoch - 1, args.epoch, args.epoch + 1):
        ngrp = epoch_group(args.rpc, epoch)
        ntw = int(ngrp.get("total_weight") or 0)
        nmembers = members_of(ngrp)
        ner = theoretical_reward_ngonka(params, epoch)
        for victim in victims:
            addr = victim["address"]
            vw = nmembers.get(addr) or {}
            rec = performance(args.rpc, epoch, addr)
            weight = int(vw.get("weight") or 0)
            cw = int(vw.get("confirmation_weight") or 0)
            actual = int(rec.get("rewarded_coins") or 0)
            pred_cw = share_ngonka(cw, ntw, ner)
            pred_w = share_ngonka(weight, ntw, ner)
            neighbor_rows.append({
                "epoch": epoch,
                "address": addr,
                "weight": weight,
                "confirmation_weight": cw,
                "root_total_weight": ntw,
                "theoretical_reward_ngonka": ner,
                "theoretical_reward_gonka": gonka(ner),
                "actual_rewarded_ngonka": actual,
                "actual_rewarded_gonka": gonka(actual),
                "pred_cw_ngonka": pred_cw,
                "pred_cw_gonka": gonka(pred_cw),
                "pred_weight_ngonka": pred_w,
                "pred_weight_gonka": gonka(pred_w),
                "actual_minus_pred_cw_gonka": gonka(actual - pred_cw),
            })
            log(
                f"  neighbor e{epoch} {addr[:18]}... actual={gonka(actual)} "
                f"pred_cw={gonka(pred_cw)} delta={gonka(actual - pred_cw)}"
            )

    recommended_ng = sum(r["recommended_lost_ngonka"] for r in victims)
    naive_ng = sum(r["naive_cw_lost_ngonka"] for r in victims)
    weight_ng = sum(r["lost_by_weight_ngonka"] for r in victims)
    indirect_ng = indirect["recommended_lost_ngonka"] if indirect else 0

    summary = {
        "epoch": args.epoch,
        "denominator_mode": "root_total_weight",
        "restitution_policy": "statistical_invalidations_plus_indirect_delegatee",
        "root_total_weight": tw,
        "member_count": len(members),
        "theoretical_reward_ngonka": er,
        "theoretical_reward_gonka": gonka(er),
        "actual_paid_pool_ngonka": paid,
        "actual_paid_pool_gonka": gonka(paid),
        "poc_start_block_height": grp.get("poc_start_block_height"),
        "effective_block_height": grp.get("effective_block_height"),
        "last_block_height": grp.get("last_block_height"),
        "scan_window": [args.scan_lo, args.scan_hi],
        "stat_invalidation_epochs_in_scan": scan_hits,
        "excluded_count": len(exclusion_rows),
        "stat_invalidation_count": len(victims),
        "failed_confirmation_poc_count": len(excluded_other),
        "recommended_numerator": "confirmation_weight_after_delegation",
        "naive_cw_total_ngonka": naive_ng,
        "naive_cw_total_gonka": gonka(naive_ng),
        "direct_total_ngonka": recommended_ng,
        "direct_total_gonka": gonka(recommended_ng),
        "indirect_total_ngonka": indirect_ng,
        "indirect_total_gonka": gonka(indirect_ng),
        "recommended_total_ngonka": recommended_ng + indirect_ng,
        "recommended_total_gonka": gonka(recommended_ng + indirect_ng),
        "weight_alternative_total_ngonka": weight_ng,
        "weight_alternative_total_gonka": gonka(weight_ng),
        "epoch_validation_params": {
            "invalidation_h_threshold": epoch_vp.get("invalidation_h_threshold"),
            "bad_participant_invalidation_rate": epoch_vp.get("bad_participant_invalidation_rate"),
            "note": "Frozen on epoch_group_data/366. Pre-#96 on-chain bad rate is 0.10, not the 0.20 code default.",
        },
        "proposal": {
            "id": str(proposal.get("id") or args.proposal_id),
            "title": proposal.get("title"),
            "status": proposal.get("status"),
            "expedited": proposal.get("expedited"),
            "proposer": proposal.get("proposer"),
            "submit_time": proposal.get("submit_time"),
            "voting_end_time": proposal.get("voting_end_time"),
            "summary": proposal.get("summary"),
        },
        "live_validation_params": {
            "invalidation_h_threshold": vp.get("invalidation_h_threshold"),
            "bad_participant_invalidation_rate": vp.get("bad_participant_invalidation_rate"),
        },
        "affected": [
            {
                "address": r["address"],
                "recommended_lost_gonka": r["recommended_lost_gonka"],
            }
            for r in sorted(victims, key=lambda x: -x["recommended_lost_ngonka"])
        ],
        "excluded_not_this_bug": [r["address"] for r in excluded_other],
        "indirect": indirect,
    }

    victim_csv = [
        {
            "address": r["address"],
            "epoch": r["epoch"],
            "reason": r["reason"],
            "exclusion_block_height": r["exclusion_block_height"],
            "exclusion_time_utc": r["exclusion_time_utc"],
            "weight": r["weight"],
            "confirmation_weight": r["confirmation_weight"],
            "inference_count": r["inference_count"],
            "invalidated_inferences": r["invalidated_inferences"],
            "invalid_rate": r["invalid_rate"],
            "missed_requests": r["missed_requests"],
            "actual_rewarded_gonka": r["actual_rewarded_gonka"],
            "naive_cw_lost_gonka": r["naive_cw_lost_gonka"],
            "delegation_share": r["delegation_share"],
            "delegation_transfer_weight": r["delegation_transfer_weight"],
            "reward_weight_after_delegation": r["reward_weight_after_delegation"],
            "recommended_lost_gonka": r["recommended_lost_gonka"],
            "weight_alternative_lost_gonka": r["lost_by_weight_gonka"],
            "root_total_weight": r["root_total_weight"],
            "theoretical_reward_gonka": gonka(r["theoretical_reward_ngonka"]),
            "denominator_mode": r["denominator_mode"],
        }
        for r in sorted(victims, key=lambda x: -x["recommended_lost_ngonka"])
    ]

    write_csv(os.path.join(OUT_DIR, "e366_per_participant.csv"), victim_csv)
    if indirect:
        write_csv(os.path.join(OUT_DIR, "e366_indirect.csv"), [indirect])
    write_csv(os.path.join(OUT_DIR, "e366_exclusions.csv"), exclusion_rows)
    write_csv(os.path.join(OUT_DIR, "e366_neighbor_epochs.csv"), neighbor_rows)
    with open(os.path.join(OUT_DIR, "e366_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== Epoch", args.epoch, "exclusions ===")
    print(f"root_total_weight     = {tw}")
    print(f"theoretical pool      = {summary['theoretical_reward_gonka']} GNK")
    print(f"actual paid pool      = {summary['actual_paid_pool_gonka']} GNK")
    print(f"stat epochs in scan   = {[h['epoch'] for h in scan_hits]}")
    print()
    print(f"{'eligible':8} {'reason':26} {'address':46} {'w':>7} {'cw':>7} {'inval%':>7} {'lost_cw':>12}")
    for r in sorted(exclusion_rows, key=lambda x: (x["eligible"], x["reason"], -x["weight"])):
        print(
            f"{r['eligible']:8} {r['reason']:26} {r['address']:46} {r['weight']:7} "
            f"{r['confirmation_weight']:7} {r['invalid_rate']*100:6.1f}% "
            f"{r['recommended_lost_gonka']:>12}"
        )
    print()
    print(f"Naive CW share (first published draft):          {summary['naive_cw_total_gonka']} GNK")
    print(f"Direct, after 5% delegation:                     {summary['direct_total_gonka']} GNK")
    print(f"Indirect (cap + delegated 5%), needs GRC vote:   {summary['indirect_total_gonka']} GNK")
    print(f"Chain-exact total if indirect is accepted:       {summary['recommended_total_gonka']} GNK")
    print(f"Wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
