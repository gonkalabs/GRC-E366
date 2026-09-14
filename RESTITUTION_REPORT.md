# Epoch 366 SPRT False Invalidation

Prepared by Mike @ GonkaLabs, for the Gonka Restitution Committee.

Task wording: shortly after devshard settlement was enabled, the old SPRT
statistical invalidation mechanism excluded two participants from the
epoch. Both were excluded with reason `statistical_invalidations` and
received no epoch rewards for 2026-08-20. The operators asked GRC to
investigate and consider compensation for a mainnet-side system bug.

Source of truth: public chain RPC at
`http://node2.gonka.ai:8000/chain-api/...`. Every number here is
regenerated end-to-end by `e366_audit.py` (stdlib only).

## Summary

The claim is real, isolated to epoch 366, and it matches governance
proposal 96.

Compensate only the two `statistical_invalidations` hosts. Do not include
the five `failed_confirmation_poc` exclusions from the same epoch.

Recommended amount uses the same chain reward formula as prior GRC
audits, with confirmation weight as the numerator:

```
lost = confirmation_weight * theoretical_epoch_reward / root_total_weight
```

| participant | weight | confirmation_weight | invalid rate | recommended (GONKA) |
| --- | ---: | ---: | ---: | ---: |
| `gonka16dgkvx7mh609ntkzknckwaskgq9lcdp86j0skk` | 60,555 | 57,537 | 2.13% | **37,609.316890** |
| `gonka1scskt6wpnjnumsah6kjphmdu87vjgvcxmn4rxv` | 43,786 | 42,180 | 6.02% | **27,571.145288** |
| | | | **TOTAL** | **65,180.462178** |

A first draft that used the coins actually paid in epoch 366 as the pool
(~153,948 GONKA) produced ~38,661 GONKA. That undercounts. Excluded and
downtime share stays in the denominator. The unpaid remainder goes to
governance. The chain formula uses the theoretical subsidy,
271,585.585902 GONKA.

## 1. The bug, on chain

Devshard settlement was enabled around 2026-08-18. Epoch 366 was the
first full reward window after that change.

The chain runs an in-epoch SPRT on invalid inferences. Before proposal
96 the threshold was low (`invalidation_h_threshold = 4`). On a small
early sample, a few invalids can trip the test and mark the host
INVALID. That writes an `excluded_participants` row with reason
`statistical_invalidations` and zeroes the epoch reward.

Both hosts kept serving after the exclusion. They finished the epoch
with large inference counts and confirmation weight still close to
start-of-epoch weight (95.0% and 96.3%). They were paid 0.

Full-epoch invalid rates (2.13% and 6.02%) sit below the post-#96
large-sample floor of about 10%. After the fix, this data would not
trip SPRT.

Proposal 96 title: "Stabilize in-epoch invalid SPRT on small samples".
It says a few invalids can trip the old SPRT before the epoch has
enough data. It raised `invalidation_h_threshold` to 40 and set
`bad_participant_invalidation_rate` to 0.18. After the fix, small
samples cannot trigger, at least 32 flagged invalids are required, and
at 500 samples the observed rate must exceed 16%. Those params are live
on chain now (`value 4, exponent 1` and `value 18, exponent -2`).

Proposal 96 was submitted 2026-08-20 18:04 UTC, after epoch 366 had
already ended. The fix did not apply to this epoch.

## 2. Timeline (UTC)

| event | height | time |
| --- | ---: | --- |
| Epoch 366 PoC start | 5,644,461 | 2026-08-19 17:00:57 |
| Epoch 366 effective start | 5,644,861 | 2026-08-19 17:36:00 |
| `gonka16dgkv...` excluded, `statistical_invalidations` | 5,652,213 | 2026-08-20 04:20:17 |
| `gonka1scskt...` excluded, `statistical_invalidations` | 5,652,288 | 2026-08-20 04:26:52 |
| Epoch 366 end | 5,660,251 | 2026-08-20 16:08:48 |
| Proposal 96 submitted (expedited) | - | 2026-08-20 18:04:19 |
| Proposal 96 passed | - | 2026-08-21 06:04:19 |

The two exclusions happened about 10.7 hours into a ~22.5 hour epoch,
which matches "SPRT tripped on a small early sample".

## 3. Detection and scope

Eligibility rule used by this audit:

- participant is in epoch 366 parent `epoch_group_data`;
- `excluded_participants/366` lists them with reason
  `statistical_invalidations`;
- actual rewarded coins are zero.

That rule returns exactly the two addresses in the claim.

A scan of `excluded_participants` for epochs 350-380 finds
`statistical_invalidations` only in epoch 366. Isolated incident.

Epoch 366 excluded 7 hosts. The other 5 are a different, ordinary path:

| participant | reason | weight | confirmation_weight | decision |
| --- | --- | ---: | ---: | --- |
| `gonka1f0u3y2wneer8zhz3ypw4x54h38cpa0qsy8ts3e` | `failed_confirmation_poc` | 8,420 | 0 | exclude |
| `gonka1aw77zuy536tufqd56zfq6ev3234u5ftty0zkte` | `failed_confirmation_poc` | 7,772 | 0 | exclude |
| `gonka1fc9tzt83dgrqswlgay4668cuqjrk7zsqks2vm2` | `failed_confirmation_poc` | 1,869 | 0 | exclude |
| `gonka1ueylw8hrlp5taqu4dy5zaxy0k82ya4r9trzzwy` | `failed_confirmation_poc` | 954 | 0 | exclude |
| `gonka1a3pkge3g33v3zdkq7qmycpjwpulms6ejt8z00f` | `failed_confirmation_poc` | 619 | 0 | exclude |

Those five have `confirmation_weight = 0`. That is a CPoC fail, not this
SPRT bug.

## 4. Compensation methodology

This follows the main correction from prior GRC audits: use the parent
epoch-group total as the denominator, not a paid-pool or subgroup sum.

Inputs for epoch 366:

```
GET /chain-api/productscience/inference/inference/epoch_group_data/366
model_id = ""
total_weight = 415488
member_count = 29

theoretical_epoch_reward =
  323000 * exp(-0.000475 * (366 - 1))
  = 271585.585902 GONKA
```

Recommended formula:

```
expected_reward_ngonka =
  confirmation_weight / root_total_weight * theoretical_epoch_reward_ngonka

eligible_loss_ngonka =
  max(0, expected_reward_ngonka - actual_rewarded_ngonka)
```

Worked examples:

```
gonka16dgkv...
  57537 / 415488 * 271585.585902 = 37609.316890 GONKA

gonka1scskt...
  42180 / 415488 * 271585.585902 = 27571.145288 GONKA
```

Why confirmation weight, not start-of-epoch weight:

- Case #3 used start-of-epoch weight because that victim failed CPoC,
  so confirmation weight was already destroyed.
- These two hosts passed CPoC. Confirmation weight is the numerator the
  chain uses for healthy payouts.
- For `gonka16dgkv...`, epochs 365 and 367 match confirmation-weight
  share exactly.

| method | `gonka16dgkv...` | `gonka1scskt...` | total |
| --- | ---: | ---: | ---: |
| confirmation_weight * theoretical / 415,488 (recommended) | 37,609.316890 | 27,571.145288 | 65,180.462178 |
| weight * theoretical / 415,488 | 39,582.046062 | 28,620.914357 | 68,202.960419 |
| weight * actual paid pool / 415,488 (first draft) | ~22,437 | ~16,224 | ~38,661 |

The first draft used the coins actually paid in epoch 366
(153,948.045686 GONKA) as the pool. That is not how the chain pays.

## 5. Neighbor-epoch sanity

| epoch | address | actual GONKA | CW-share GONKA | actual minus CW-share |
| ---: | --- | ---: | ---: | ---: |
| 365 | `gonka16dgkv...` | 30,439.746651 | 30,439.746651 | 0.000000 |
| 365 | `gonka1scskt...` | 20,769.037248 | 21,861.950889 | -1,092.913641 |
| 366 | `gonka16dgkv...` | 0.000000 | 37,609.316890 | -37,609.316890 |
| 366 | `gonka1scskt...` | 0.000000 | 27,571.145288 | -27,571.145288 |
| 367 | `gonka16dgkv...` | 50,484.616744 | 50,484.616744 | 0.000000 |
| 367 | `gonka1scskt...` | 29,034.990116 | 34,158.329473 | -5,123.339357 |

`gonka16dgkv...` is a clean match. `gonka1scskt...` usually lands below
confirmation-weight share in healthy epochs (possible downtime or
capping). Paying the chain formula is still the consistent GRC method.
A haircut on `gonka1scskt...` is a policy choice, not a math fix.

Both hosts were paid normally in 365 and 367. Epoch 366 is the hole.

## 6. Upstream / governance reference

On-chain proposal 96, proposer
`gonka1y2a9p56kv044327uycmqdexl7zs82fs5ryv5le`, status PASSED,
expedited.

It changes validation params:

- `invalidation_h_threshold`: 4 -> 40
- `bad_participant_invalidation_rate`: 0.20 -> 0.18
- downtime SPRT turned off (`downtime_h_threshold` set unused)

The proposal text is the official admission that in-epoch SPRT was
unstable on a small sample. That is this incident.

The live chain already has the new params. No further code change is
needed to stop a repeat. Restitution is only for the epoch that already
closed under the old threshold.

## 7. Caveats

What the report claims:

- Epoch 366 has exactly two `statistical_invalidations` exclusions, and
  they are the two addresses in the claim. This is verifiable from
  `excluded_participants/366`.
- Those two hosts passed CPoC, kept serving, and received 0 reward.
- A 350-380 scan finds this reason only in epoch 366.
- Proposal 96 is the on-chain fix and landed after epoch 366 ended.
- Recommended amounts are the linear chain formula using confirmation
  weight and parent `total_weight`.

What the report does not claim:

- That the five `failed_confirmation_poc` hosts are part of this bug.
- That `gonka1scskt...` would have received the full confirmation-weight
  share if they had not been excluded. Neighbor epochs say they often
  receive less.
- That inference-settlement side effects beyond the fixed epoch reward
  are included. This case pays the zeroed epoch reward only.
- That every future `statistical_invalidations` row is automatically
  this bug. After proposal 96 the threshold is different.

## 8. Files

```
GRC-E366/
├── e366_audit.py
├── README.md
├── RESTITUTION_REPORT.md
├── grc-form.md
└── output/
    ├── e366_per_participant.csv
    ├── e366_exclusions.csv
    ├── e366_neighbor_epochs.csv
    ├── e366_summary.json
    ├── e366_log.txt
    └── raw_chain/
```
