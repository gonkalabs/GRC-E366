# Epoch 366 SPRT False Invalidation

Prepared by Mike @ GonkaLabs, for the Gonka Restitution Committee.

Revised after GRC archive-node review. The incident and the eligibility
rule are unchanged. The amounts now follow the chain reward estimator,
including the 5% delegation transfer and the 30% power cap.

Source of truth for exclusions, weights, and rewards: public chain RPC at
`http://node2.gonka.ai:8000/chain-api/...`. The power-cap weights 84,847
to 74,370 come from the reviewer's `estimate_bitcoin_reward` at the
exclusion block. Public nodes do not serve that historical query. The
GNK delta from those weights is recomputed here.

## Summary

Compensate the two `statistical_invalidations` hosts. Do not include the
five `failed_confirmation_poc` exclusions.

`gonka1scskt` does not keep its full confirmation-weight share. The epoch
366 delegation snapshot moves 5% of its reward weight to `gonka1gvrrhj`.
That same 5% is the second half of the indirect loss on `gonka1gvrrhj`.
Pay it once, on the delegatee, or the 1,378.56 is paid twice.

| participant | role | recommended (GONKA) |
| --- | --- | ---: |
| `gonka16dgkvx7mh609ntkzknckwaskgq9lcdp86j0skk` | direct, full CW share | **37,609.316890** |
| `gonka1scskt6wpnjnumsah6kjphmdu87vjgvcxmn4rxv` | direct, 95% of CW share | **26,192.588023** |
| **Direct total** | | **63,801.904914** |
| `gonka1gvrrhjmy4w4mayvs2s5l23edj8ertcmtd2v4zr` | indirect: power cap + the 5% | **8,226.895083** |
| **Total if GRC accepts the indirect row** | | **72,028.799996** |

The first published draft paid both direct hosts their full CW share,
**65,180.462178 GONKA**. That overpays `gonka1scskt` by the 5% the chain
would have transferred, and it misses `gonka1gvrrhj`.

`gonka1gvrrhj` is the first indirect loss in a GRC case. It belongs in
the case if the goal is to put epoch 366 back where the chain would have
been. It needs an explicit vote. Memorandum 6.6 ("pure restitutions based
on code") points at including it.

## 1. The bug, on chain

Devshard settlement was enabled around 2026-08-18. Epoch 366 was the
first full reward window after that change.

Neither host had a counted inference until its first devshard settlement.
`gonka16dgkv` tripped on that first batch: 25 invalid out of 263, LLR
4.46 against H=4. The chain then wrote `statistical_invalidations` and
zeroed the epoch reward. Both hosts kept serving. Final invalid rates
are 2.13% and 6.02%.

Epoch 366 stores the pre-#96 SPRT params on
`epoch_group_data.validation_params`:

| param | epoch 366 value | meaning |
| --- | --- | --- |
| `invalidation_h_threshold` | value 4, exponent 0 | H = 4 |
| `bad_participant_invalidation_rate` | value 1, exponent -1 | 0.10 |

The earlier draft cited the code default 0.20. That was wrong for this
epoch. The live chain, after proposal 96, is H=40 and bad rate 0.18.
Under those params neither host's LLR goes above 0 at any point in the
epoch.

Proposal 96, "Stabilize in-epoch invalid SPRT on small samples", was
submitted 2026-08-20 18:04 UTC, after epoch 366 had already ended.

## 2. Timeline (UTC)

| event | height | time |
| --- | ---: | --- |
| Epoch 366 PoC start | 5,644,461 | 2026-08-19 17:00:57 |
| Epoch 366 effective start | 5,644,861 | 2026-08-19 17:36:00 |
| CPoC round 0 trigger | 5,648,350 | |
| CPoC round 1 trigger | 5,651,952 | |
| `gonka16dgkv...` excluded, `statistical_invalidations` | 5,652,213 | 2026-08-20 04:20:17 |
| Confirmation weight last written | 5,652,233 | CPoC round 1 result |
| `gonka1scskt...` excluded, `statistical_invalidations` | 5,652,288 | 2026-08-20 04:26:52 |
| CPoC round 2 trigger | 5,657,937 | after both exclusions |
| CPoC round 3 trigger | 5,658,826 | after both exclusions |
| Epoch 366 end | 5,660,251 | 2026-08-20 16:08:48 |
| Proposal 96 submitted (expedited) | - | 2026-08-20 18:04:19 |
| Proposal 96 passed | - | 2026-08-21 06:04:19 |

## 3. Scope

Include:

- `excluded_participants/366` reason `statistical_invalidations`
- the delegatee who lost the 5% transfer and was pushed through the 30%
  power cap because those two hosts left the ACTIVE set

Exclude the five `failed_confirmation_poc` hosts. Their confirmation
weight is 0. That is a different mechanism.

A scan of epochs 350-380 finds `statistical_invalidations` only in 366.

## 4. Direct amounts

```
GET /chain-api/productscience/inference/inference/epoch_group_data/366
model_id = ""
total_weight = 415488

theoretical_epoch_reward =
  323000 * exp(-0.000475 * 365)
  = 271585.585902 GONKA
```

`math.exp` in this script is 271,585,585,901,851 ngonka. The chain value
cited in review is 271,585,585,901,857 ngonka. The gap is 6 ngonka. It
does not move any 6-decimal GONKA figure.

Naive confirmation-weight share, before delegation:

```
gonka16dgkv  57537 / 415488 * theoretical = 37609.316890 GONKA
gonka1scskt  42180 / 415488 * theoretical = 27571.145288 GONKA
```

`gonka1scskt` delegates Kimi to `gonka1gvrrhj`. The current
`poc_delegation` record still shows that pair. Had `gonka1scskt` stayed
ACTIVE, 5% of its reward weight would have been transferred:

```
transfer_weight = 42180 * 0.05 = 2109
kept_weight     = 42180 - 2109 = 40071
kept_reward     = 40071 / 415488 * theoretical = 26192.588023 GONKA
```

That is the chain's own `estimate_bitcoin_reward` for `gonka1scskt` at
block 5,652,287, one block before the exclusion.

The same rule matches the neighbor epochs at 4 decimals:

| epoch | what the chain did | actual / CW-share |
| ---: | --- | ---: |
| 365 | same 5% Kimi transfer | 0.9500 |
| 366 | excluded, reward 0 | 0 |
| 367 | 15% `no_participation_penalty` | 0.8500 |

`gonka16dgkv` has no such transfer. Epochs 365 and 367 pay it at exactly
the confirmation-weight share. Its epoch 366 amount stays
**37,609.316890 GONKA**.

Confirmation-weight caveat: both hosts' stored CW was last set at block
5,652,233 by CPoC round 1. Rounds 2 and 3 ran after the exclusions and
did not update them. Final CW is a slight upper bound on what a full
healthy epoch would have confirmed.

## 5. Indirect amount: `gonka1gvrrhj`

Two effects, both caused by the exclusions.

Power cap. The 30% cap is checked only against ACTIVE hosts. Removing
the two STAT hosts took about 100k weight out of that base, so
`gonka1gvrrhj` went from 23.7% to 32.8% of active weight. The chain cut
its reward weight from 84,847 to 74,370.

```
(84847 - 74370) / 415488 * theoretical = 6848.337818 GONKA
```

If either STAT host had stayed ACTIVE, the cap would not have applied.

Delegation inflow. `gonka1gvrrhj` is the host that should have received
the 2,109 weight from section 4.

```
2109 / 415488 * theoretical = 1378.557264 GONKA
```

```
6848.337818 + 1378.557264 = 8226.895083 GONKA
```

`estimate_bitcoin_reward` for `gonka1gvrrhj` drops in block 5,652,288,
the same block `gonka1scskt` was excluded. Its actual epoch payout was
50,502.651191 GONKA, not zero. This row is only the delta, not a second
full reward.

Do not add this 1,378.557264 on top of the old 27,571.145288 figure for
`gonka1scskt`. The 26,192.588023 figure already removed it.

## 6. What this does not pay

Going INVALID also cost the two direct hosts:

| host | work coins | collateral slash | reputation |
| --- | ---: | ---: | --- |
| `gonka16dgkv...` | 1.193 GONKA | 40,692 ngonka | reset to 0 |
| `gonka1scskt...` | 0.657 GONKA | 29,423 ngonka | reset to 0 |

Those amounts are tiny next to the fixed reward and are not in the
totals above. `epoch_performance_summary` shows `earned_coins = 0` for
both, which is consistent with the work coins being wiped rather than
paid.

## 7. Caveats

What the report claims:

- Exactly two `statistical_invalidations` rows in epoch 366, and they
  are the two addresses in the claim.
- Those two passed CPoC, kept serving, and received 0 reward.
- `gonka1scskt`'s chain-exact direct loss is 95% of its CW share.
- `gonka1gvrrhj` lost the power-cap delta plus that 5%, measured at the
  exclusion block.
- Proposal 96 is the fix and landed after epoch 366 ended.
- Epoch 366 on-chain bad rate was 0.10, H was 4.

What the report does not claim:

- That the five `failed_confirmation_poc` hosts are this bug.
- That public REST can replay `estimate_bitcoin_reward` at height
  5,652,287. The cap weights are from the archive review. The script
  turns those weights into GNK with the same formula as the direct rows.
- That final stored CW is a full-epoch healthy CW. Rounds 2 and 3 did
  not update it.
- That work coins, the collateral slash, or the reputation reset are
  inside the recommended total.
