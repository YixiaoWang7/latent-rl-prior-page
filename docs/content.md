# Content provenance

The supplied review manuscript, *Latent RL Priors for Data-Efficient Dexterous Manipulation*,
contains 12 pages. Its source SHA-256 is recorded in `assets/manifest.json`. No chart values were
estimated from pixels or reconstructed into synthetic curves.

| Website content | Manuscript source |
| --- | --- |
| Frozen flow-matching action decoder and direct visual-to-latent conditioning | Sections 3.2–3.3; Figure 1 |
| Action-only adaptation, no privileged labels or latent targets | Section 3.3 |
| Shared single-arm decoder with joint arm-specific queries | Section 3.3; Figure 1 |
| 100,000 successful RL rollouts for pretraining | Section 4.1; Table 1 |
| Tasks, robot embodiment, and success criteria | Section 4.1; Figures 2–3 |
| 50 versus 500 demonstrations on door lifting | Section 4.2; Figure 4 |
| 1,000 versus 5,000 demonstrations on assembly | Section 4.2; Figure 4 |
| Per-run best of the final five checkpoints, 256 rollouts, three seeds | Section 4.1, page 6 |
| Latent versus explicit transfer and scratch baseline | Section 4.3; Figures 5–6 |
| Image-encoder and decoder adaptation | Section 4.4; Figure 7 |
| 32.6% versus 12.9% door success at 5.0 kg | Section 4.5; Figure 8 |
| Contact-force probe results | Section 4.5; Figure 9 |
| Simulation-only evaluation, pretraining cost, morphology and causal limits | Section 5 |
| Contributions list | Section 1 |
| Dataset sizes, arm–hand systems, and cameras | Section 4.1; Table 1 |
| Baselines, training steps, and evaluation protocol | Section 4.1 |
| Limitations list | Section 5 |
| Author list, affiliations, and internship note | Preprint title block (`\iclrpreprintcopy`) |
| Abstract text | Abstract (preprint version, without the trailing project-website link) |
| Planned code and dataset release | Reproducibility statement |

## Implementation cross-check

The following modules in the research implementation were inspected to verify the method description:

- `src/maniptool/distill/state/policy.py`: privileged state tokenizer, context encoder, and
  flow-matching action-prior objective.
- `src/maniptool/distill/flow/policy.py`: DINOv2 image tokens, camera embeddings, visual context,
  action-only flow loss, and denoising.
- `src/maniptool/networks/qformer.py`: query self-attention followed by cross-attention to input
  tokens.
- `src/maniptool/networks/transformer.py`: action-token cross-attention and adaptive layer
  normalization conditioned on flow time and proprioception.
- `src/maniptool/distill/flow_bimanual/policy.py`: joint visual query processing, per-arm context
  splitting, and both arms processed by the shared single-arm decoder.

The website is a separate artifact; it does not include or publish the research repository.

## Interpretation boundaries

The demonstration-efficiency ratios compare downstream visual-demonstration budgets. They do not
claim reduced total data or compute expenditure. All results are simulated. Task demonstration clips
are illustrative trajectory replays and do not demonstrate a particular policy budget or success rate.
The physical analyses support retained control knowledge without isolating a causal mechanism.

The temporary anonymous BibTeX entry is an unpublished manuscript citation, not a claim of conference
acceptance.

## Interactive figures

The method section shows Figure 1 with its manuscript caption, three stage cards whose trained and
frozen modules follow Sections 3.2–3.3, and the conditioning equations from Section 3. The stage cards
summarize the paper and do not add claims. The overview card "8 / 8 decoder layers" summarizes the
contact-probe data: the RL-prior RMSE is lower than the scratch RMSE for all 4 targets × 5 budgets ×
8 layers in `assets/data/contact-probes.json`.

The 2026-11-05 redesign removed the animated method walkthrough and the data-budget bar comparison.
Copies of the earlier page are in `.local-backups/`, which is not published.

The contact explorer and downloadable vector figure use all 320 means from Figure 9. The prior
values come from the retained per-output RMSE results. For the scratch decoder, per-output R² and
the identical IID test-label variance recover each output's RMSE; outputs are averaged before
averaging the three policy seeds. Averaged R² is never substituted in that calculation.

`scripts/export_contact_data.py` checks the recovered values against every original PDF curve point
under each panel's linear axis transform. The maximum discrepancy is below 0.001 PDF points.
The interaction shows measured layer values, keeps the vertical scale fixed when changing budgets
within a target, and preserves the paper's interpretation limits.
