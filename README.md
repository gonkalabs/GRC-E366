# Epoch 366 SPRT False Invalidation

Prepared by Mike @ GonkaLabs.

Reproducer for the 2026-08-20 mainnet incident raised with the Gonka
Restitution Committee:

> Shortly after devshard settlement was enabled, the old SPRT statistical
> invalidation mechanism excluded two participants from the epoch with
> reason `statistical_invalidations`. The affected hosts received no
> epoch rewards for August 20.

`e366_audit.py` runs end-to-end against the public chain RPC. No local DB,
no auth, Python 3.9+ stdlib only. Anyone can re-run it and get the same
numbers.

The narrative report with restitution tables is `RESTITUTION_REPORT.md`.
The filled intake form is `grc-form.md`.

## Current result

Revised after GRC archive review. Direct hosts use confirmation weight,
then the 5% Kimi delegation from `gonka1scskt` to `gonka1gvrrhj`.

| participant | recommended |
| --- | ---: |
| `gonka16dgkvx7mh609ntkzknckwaskgq9lcdp86j0skk` | **37,609.316890 GONKA** |
| `gonka1scskt6wpnjnumsah6kjphmdu87vjgvcxmn4rxv` | **26,192.588023 GONKA** |
| **Direct total** | **63,801.904914 GONKA** |
| `gonka1gvrrhjmy4w4mayvs2s5l23edj8ertcmtd2v4zr` (indirect, needs a vote) | **8,226.895083 GONKA** |
| **Total if the indirect row is accepted** | **72,028.799996 GONKA** |

The first draft's 65,180.462178 paid `gonka1scskt` the full CW share and
missed the delegatee. Paying both that full share and the indirect 5%
would count 1,378.557264 GONKA twice.

Five other epoch-366 exclusions are `failed_confirmation_poc`. Those are
ordinary CPoC fails and are not part of this case.

A scan of `excluded_participants` for epochs 350-380 finds
`statistical_invalidations` only in epoch 366.

## Run it

```bash
python3 e366_audit.py
```

Takes around 30 seconds (HTTP round-trips against the public node). Outputs
land in `./output/`.

```bash
python3 e366_audit.py --epoch 366 --scan-lo 350 --scan-hi 380
```

## What the script does

1. Reads parent `epoch_group_data/366` (`model_id` empty) for
   `root_total_weight` and per-host `weight` / `confirmation_weight`.
2. Reads `excluded_participants/366` and classifies each row by reason.
3. Reads `epoch_performance_summary` for inference counts, invalid rate,
   misses, and actual reward.
4. Scans epochs 350-380 for any other `statistical_invalidations`.
5. Checks epochs 365 and 367 to show how the same hosts were paid when
   they were not excluded.
6. Records governance proposal 96, which raised
   `invalidation_h_threshold` to 40 after epoch 366 had already ended.

Direct per-host loss:

```
gross = confirmation_weight * fixedEpochReward(366) / rootTotalWeight(366)
        - actual_rewarded_ngonka
```

`gonka1scskt` then keeps 95% of that gross. The other 5% is added to
`gonka1gvrrhj`, together with the power-cap delta (reward weight 84,847
cut to 74,370 once the two STAT hosts left the ACTIVE set).

`fixedEpochReward(E)` is the chain's own
`initial * exp(decay_rate * (E - genesis))` from
`inference.params.bitcoin_reward_params`. For epoch 366 that is
271,585.585902 GONKA. `rootTotalWeight(366)` is 415,488.

Epoch 366's own `validation_params` store `bad_participant_invalidation_rate`
= 0.10 and `invalidation_h_threshold` = 4. The live params are the
post-#96 values and are not the ones that fired.

## CLI flags

```
--rpc URL              Public chain RPC base (default http://node2.gonka.ai:8000)
--epoch N              Epoch to audit (default 366)
--scan-lo N            Inclusive lower bound for STAT-reason scan (default 350)
--scan-hi N            Inclusive upper bound for STAT-reason scan (default 380)
--proposal-id N        Governance proposal to record (default 96)
```

## Outputs (`./output/`)

| file | description |
| --- | --- |
| `e366_per_participant.csv` | the two STAT victims, naive CW share, and delegation-adjusted amount |
| `e366_indirect.csv` | `gonka1gvrrhj` power-cap delta plus the 5% transfer |
| `e366_exclusions.csv` | all seven epoch-366 exclusions, with eligibility |
| `e366_neighbor_epochs.csv` | 365/366/367 actual vs formula check |
| `e366_summary.json` | totals, scan hits, proposal 96, live SPRT params |
| `e366_log.txt` | full RPC trace from the last run |
| `raw_chain/` | cached JSON from the endpoints used above |

## Sanity check against the chain directly

Confirm both hosts are the only `statistical_invalidations` rows in
epoch 366, that they have confirmation weight, and that they were paid 0:

```bash
curl -s --max-time 8 \
  "http://node2.gonka.ai:8000/chain-api/productscience/inference/inference/excluded_participants/366" \
  | python3 -c "
import json, sys
items = (json.load(sys.stdin).get('items') or [])
for i in items:
    print(i.get('reason'), i.get('address'), 'h=', i.get('exclusion_block_height'))
"
```

Then check weight, confirmation weight, and actual reward for one victim:

```bash
ADDR=gonka16dgkvx7mh609ntkzknckwaskgq9lcdp86j0skk

curl -s --max-time 8 \
  "http://node2.gonka.ai:8000/chain-api/productscience/inference/inference/epoch_group_data/366" \
  | python3 -c "
import json, sys
g = json.load(sys.stdin).get('epoch_group_data') or {}
print('total_weight', g.get('total_weight'))
for vw in g.get('validation_weights') or []:
    if vw.get('member_address') != '$ADDR':
        continue
    print('weight', vw.get('weight'), 'confirmation_weight', vw.get('confirmation_weight'))
"

curl -s --max-time 8 \
  "http://node2.gonka.ai:8000/chain-api/productscience/inference/inference/epoch_performance_summary/366/${ADDR}" \
  | python3 -c "
import json, sys
r = json.load(sys.stdin).get('epochPerformanceSummary') or {}
print('inferences', r.get('inference_count'),
      'invalidated', r.get('invalidated_inferences'),
      'missed', r.get('missed_requests'),
      'rewarded', r.get('rewarded_coins'))
"
```

You should see `total_weight = 415488`, `weight = 60555`,
`confirmation_weight = 57537`, about 24,778 inferences with a 2.1%
invalid rate, and `rewarded_coins = 0`.

The same address in epochs 365 and 367 is paid exactly

```
confirmation_weight * theoretical_epoch_reward / root_total_weight
```

That is why the recommended numerator is confirmation weight, not raw
start-of-epoch weight.

## Dependencies

Python 3.9+ stdlib only. No `pip install` required.
