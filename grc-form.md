# GRC Case Intake Form - Epoch 366 SPRT False Invalidation

Internal GRC form for this restitution case. Filled from the first
chain-only investigation pass. The audit uses public REST from
`http://node2.gonka.ai:8000`.

## 1. Case Basics

| Field | Answer |
| --- | --- |
| Case ID | GRC-E366 |
| Short title | Epoch 366 in-epoch SPRT false invalidation |
| Reporter / proposer | Host operator (one of the two excluded addresses); GRC asked to investigate with @votkon |
| Date opened (UTC) | 2026-09-11 |
| Related links | https://github.com/gonkalabs/GRC-E366<br>https://gonka.gg/network/proposals/96 |
| Affected epoch(s) / block range | Epoch 366. Exclusions at heights `5652213` and `5652288` (2026-08-20 04:20-04:26 UTC). Epoch window heights `5644461`-`5660251`. |
| Affected software version(s) | Mainnet before proposal 96 SPRT params (`invalidation_h_threshold = 4`) |
| Fix / patch reference | Governance proposal 96, PASSED, expedited. Raises `invalidation_h_threshold` to 40 and sets `bad_participant_invalidation_rate` to 0.18. Submitted 2026-08-20 18:04 UTC, after epoch 366 ended. |

## 2. Short Summary

| Question | Answer |
| --- | --- |
| What happened? | After the first devshard settlements, in-epoch SPRT tripped on a small sample and excluded two hosts with reason `statistical_invalidations`. Both received zero epoch-366 reward. |
| Why might restitution be needed? | Proposal 96 later described this SPRT as unstable on a small sample and changed the params. The two hosts kept serving, passed CPoC, and were paid normally in epochs 365 and 367. The zero payout is from a mainnet-side threshold bug, not a failed CPoC. |
| Who may be affected? | Exactly two addresses: `gonka16dgkvx7mh609ntkzknckwaskgq9lcdp86j0skk` and `gonka1scskt6wpnjnumsah6kjphmdu87vjgvcxmn4rxv`. |
| What is already confirmed? | Chain exclusions, zero rewards, confirmation weights, inference counts, neighbor-epoch payouts, scan isolation to epoch 366, and proposal 96 timing/params. |
| What is still uncertain? | Whether GRC prefers confirmation-weight share (recommended, 65,180.462178 GONKA) or start-of-epoch weight share (68,202.960419 GONKA), and whether `gonka1scskt...` should take a haircut because healthy epochs paid them below CW-share. |

## 3. Timeline

| Event | Epoch | Block | Time (UTC) | Source / link | Notes |
| --- | --- | --- | --- | --- | --- |
| Devshard settlement enabled | | | 2026-08-18 | operator / DevOps report | Context for "first settlements" |
| Epoch 366 PoC start | 366 | 5644461 | 2026-08-19 17:00:57 | `epoch_group_data/366` | |
| Epoch 366 effective | 366 | 5644861 | 2026-08-19 17:36:00 | `epoch_group_data/366` | |
| First exclusion | 366 | 5652213 | 2026-08-20 04:20:17 | `excluded_participants/366` | `gonka16dgkv...`, STAT |
| Second exclusion | 366 | 5652288 | 2026-08-20 04:26:52 | `excluded_participants/366` | `gonka1scskt...`, STAT |
| Epoch 366 end | 366 | 5660251 | 2026-08-20 16:08:48 | `epoch_group_data/366` | Both hosts reward = 0 |
| Fix available | | | 2026-08-20 18:04:19 | proposal 96 submit | Too late for epoch 366 |
| Issue ends | | | 2026-08-21 06:04:19 | proposal 96 passed | Live params now H=40 |

## 4. Initial Technical Claim

| Question | Answer |
| --- | --- |
| What should have happened? | In-epoch SPRT should not mark a host INVALID on a small early sample when the full-epoch invalid rate is 2.1% / 6.0%. Those hosts should have received the normal confirmation-weight epoch reward. |
| What actually happened? | SPRT tripped mid-epoch, wrote `statistical_invalidations`, and zeroed both rewards. The hosts continued serving. |
| What component caused or may have caused it? | In-epoch invalid SPRT with `invalidation_h_threshold = 4`, exposed by the first small-sample settlements after devshard settlement was enabled. |
| What commit, release, config, or migration is involved? | Validation params before proposal 96. The official fix is proposal 96 (`MsgUpdateParams`), not a binary patch. |
| Is the issue fixed? | Yes, on chain. Live `invalidation_h_threshold` is 40. No later STAT rows in the 350-380 scan. |

## 5. Affected Scope

| Question | Answer |
| --- | --- |
| Affected participant type(s) | Epoch-366 ML hosts excluded for `statistical_invalidations` |
| Affected reward stream(s) | Fixed epoch reward only |
| Affected model / subgroup, if relevant | Parent epoch group; not model-specific |
| Affected rounds, CPoCs, or epochs | Epoch 366 only |
| Baseline state to compare against | Same hosts in epochs 365 and 367; post-#96 SPRT floor ~10% |
| Estimated affected count | 2 addresses |
| Estimated restitution exposure | 65,180.462178 GONKA recommended; 68,202.960419 GONKA if GRC uses start-of-epoch weight |

## 6. Eligibility Draft

### Include Participants Who

| Rule | Reason / source |
| --- | --- |
| Appear in `excluded_participants/366` with reason `statistical_invalidations` | Defines this bug |
| Were in the epoch 366 parent group and received zero reward | Defines loss |
| Passed CPoC (`confirmation_weight > 0`) and kept serving | Separates this from ordinary CPoC fail |

### Exclude Participants Who

| Rule | Reason / source |
| --- | --- |
| Were excluded for `failed_confirmation_poc` or any other reason | Different mechanism |
| Appear only in other epochs | Scan shows STAT only in 366 |
| Received a normal epoch-366 reward | No loss |

### Needs Manual Review

| Case type | Why it is ambiguous |
| --- | --- |
| `gonka1scskt...` payout level | Healthy epochs pay below CW-share; GRC may want a haircut |
| Start-of-epoch weight vs confirmation weight | Weight is closer to Case #3; CW matches observed healthy payouts |

## 7. Evidence Needed

| Evidence | Location / command / endpoint | Status |
| --- | --- | --- |
| Chain data source | Public REST `node2.gonka.ai:8000` | Collected in `output/raw_chain/` |
| Historical query method | `e366_audit.py` | Complete |
| Relevant code / commits | Proposal 96 `MsgUpdateParams`; pre-#96 `invalidation_h_threshold = 4` | Identified |
| Release or deployment timestamps | Proposal 96 submit/pass times above | Complete |
| Operator reports, if any | GRC letter; DevOps / Gleb discussion referenced by reporter | Letter on file; chat logs not copied here |
| Existing scripts, CSVs, or JSON files | `e366_audit.py`, `output/e366_*.csv`, `output/e366_summary.json` | Complete |

## 8. Draft Restitution Method

| Question | Answer |
| --- | --- |
| What baseline will be used? | Same-host neighbor epochs 365 and 367, plus the chain formula |
| Why is that baseline fair? | Both hosts were paid in 365 and 367; 366 is the SPRT hole |
| What denominator will be used? | Parent `epoch_group_data.total_weight` = 415,488 |
| Should actual rewards already received be subtracted? | Yes. Actual is 0 for both. |
| Should partial payouts stay eligible? | Not applicable; both are zero |
| Should downtime, misses, invalidation, or slashing affect eligibility? | Recommended: keep both hosts. They have misses and 2-6% invalids, but that is below the post-fix floor and they were not excluded for those reasons. |
| Should the calculation include only fixed rewards or other losses too? | Fixed epoch reward only |

Formula draft:

```
eligible_loss_ngonka = max(0, expected_reward_ngonka - actual_rewarded_ngonka)

expected_reward_ngonka =
  confirmation_weight / root_total_weight * fixed_epoch_reward_ngonka
```

Units and rounding:

| Item | Answer |
| --- | --- |
| Internal unit | ngonka |
| Display unit | GONKA |
| Rounding rule | Integer ngonka, displayed to 6 decimals |
| Final payout precision | 65,180.462178 GONKA recommended |

## 9. Required Investigator Output

- README with short summary and run instructions.
- Reproducible script or notebook.
- Machine-readable output, preferably CSV and JSON.
- Per-participant restitution table.
- List of excluded and manual-review cases.
- Narrative report with caveats.
- At least one raw-data sanity check.

## 10. Required Validator Checks

- Re-run `python3 e366_audit.py` and match `output/e366_summary.json`.
- Confirm proposal 96 title, params, and timing vs epoch 366 end.
- Confirm the five `failed_confirmation_poc` rows stay out.
- Spot-check both restitution rows against the formula.
- Spot-check neighbor-epoch CSV for `gonka16dgkv...` (exact CW match).
- Confirm the paid-pool first draft is rejected.

## 11. GRC Policy Questions

| Question | Decision / link |
| --- | --- |
| Confirmation weight or start-of-epoch weight as numerator? | Draft: confirmation weight |
| Haircut `gonka1scskt...` because healthy epochs paid below CW-share? | Open; default is no |
| Include any `failed_confirmation_poc` host from epoch 366? | Draft: no |
| Include later STAT rows if any appear after #96? | Draft: no; this case is epoch 366 only |
| Paid-pool vs theoretical subsidy? | Draft: theoretical, same as prior GRC cases |

## 12. Conflict Check

| Question | Answer |
| --- | --- |
| Does the proposed investigator benefit from the case? | No |
| Does any proposed validator benefit from the case? | Unknown until validators are named |
| Did any assigned person work on the faulty component? | No |
| Are any conflicts disclosed and accepted by GRC? | No |

## 13. Ready For Assignment

- [x] Case basics are filled.
- [x] Time window is clear.
- [x] Initial technical claim is written.
- [x] Affected scope is described.
- [x] Eligibility draft is written.
- [x] Evidence sources are listed.
- [x] Draft restitution method is written.
- [x] Open policy questions are listed.
- [x] Conflict check is complete.
- [ ] GRC agrees the case is ready to assign.

## 14. Assignment

| Role | Name / handle | Date (UTC) | Notes |
| --- | --- | --- | --- |
| Investigator | Mike @ GonkaLabs | 2026-09-11 | Chain-only audit in this repo |
| Validator | | | |

Expected completion date: 2026-09-14
