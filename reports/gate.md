# Go/no-go gate - lead 3 - product `weather_corr_v1`

**Decision: GO: Track 6 forecast product**

| # | criterion | value | pass |
|---|---|---|---|
| 1 | N paired >= 120 and May-Aug >= 60 | n=224, n_may_aug=107 | yes |
| 2 | S3 >= 10% | 0.3406 | yes |
| 3 | Delta3 >= max(0.1 C, 0.1 x 2024 persistence MAE) = 0.118 C | 0.4085 | yes |
| 4 | 95% moving-block bootstrap lower bound on Delta > 0 (14-day and 28-day blocks) | b14=[0.190, 0.635], b28=[0.149, 0.689] | yes |
| 5 | beats climatology overall and persistence in May-Aug | mae_prod=0.7908, mae_clim=1.7494, mae_prod_may_aug=0.7790, mae_pers_may_aug=1.3230 | yes |
| 6 | chronology assertions pass and 24h-delay sensitivity keeps positive skill | chronology_passed=True, S_delay1=0.3846 | yes |
