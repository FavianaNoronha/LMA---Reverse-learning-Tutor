# Prior art we borrow from (and what we did with it)

All results below were measured by the papers' authors in other domains (programming, math, English writing),
mostly with small samples. They justify design choices; they are not evidence that SETU works. Our evidence will
come from `scripts/plain_prompt_leak_test.py` (Gemma baseline), `scripts/simulated_eval.py` and the 5-learner study.

| Source | Idea | Where in the repo | Test |
|---|---|---|---|
| Jin et al. 2024, AlgoBo (arXiv 2309.14534) | Raju asks "why?" every 3rd checked fix (their mode-shifting raised knowledge-building messages, p=0.03, d=0.73, 40 novices). Fixed phrases, no model call; the answer goes to the teacher queue and changes nothing. | `session.py` (`WHY_EVERY`, `why` pending), `classmate.py` (`RAJU_WHY`) | `test_why_question_after_every_third_fix_and_it_changes_nothing` |
| Jin et al. 2024 | Reconfigurability, persistence, adaptability tests of the knowledge state | - | `test_reconfigurable_*`, `test_persistence_*`, `test_adaptability_*` |
| Moribe & Ushiama 2025 (arXiv 2507.12801) | Peer reproduces the learner's own error mix. Ours: planner weights unknown rules by the learner's wrong count; the filter verifies the error type (they did not). | `planner.py` (`weights`), `session.py` | `test_planner_prefers_rules_the_learner_gets_wrong`, `test_session_weights_follow_wrong_counts` |
| Do, Sonkar & Sachan 2026 (arXiv 2605.12748) | Selective Flip Score under targeted / misaligned / generic feedback | `metrics.py` (`selective_flip_score`) | `test_raju_flips_only_after_targeted_feedback` |
| Apartsin et al. 2026 (arXiv 2605.25601) | RMSE and controllability against a target skill vector; cross-skill influence | `metrics.py` (`rmse`, `controllability`) | `test_controllability_*`, `test_teaching_one_rule_does_not_change_the_others` |
| StudentSim 2026 (arXiv 2609.01591) | Guidance responsiveness (right after a correct fix) | `scripts/simulated_eval.py` | `test_guidance_responsiveness_*` |
| Yuan et al. 2026 (arXiv 2601.05473) | Epistemic State Specification (access, error structure, change); conceptual, no experiments | paper section 4 | - |
| Arun et al. 2025, Chrysalis (arXiv 2510.05271) | Warning: prompt-only student dropped its role; quiz ceiling effect (36 students). Our delayed test uses hard and unseen items. | paper section 8.3 | - |

Not adopted: unlearning (Song et al. 2026), SFT/DPO/GRPO or per-student adapters (Do et al., StudentSim), AlgoBo's
Teaching Helper classifier (71% accuracy, no significant metacognition gain). Listed as future work.

Simulated results with the mock model are in `docs/results_simulated.json`. They hold by construction and test the
machinery, not Gemma.
