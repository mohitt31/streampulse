# Go/no-go gate - lead 3 - product `weather_corr_v1`

**Decision: NO-GO: switch to Track 2: historical thermal-anomaly assessment and monitoring prioritization**

| # | criterion | value | pass |
|---|---|---|---|
| 1 | N paired >= 120 and May-Aug >= 60 | n=225, n_may_aug=108 | yes |
| 2 | S3 >= 10% | 0.1912 | yes |
| 3 | Delta3 >= max(0.1 C, 0.1 x 2024 persistence MAE) = 0.101 C | 0.1776 | yes |
| 4 | 95% moving-block bootstrap lower bound on Delta > 0 (14-day and 28-day blocks) | b14=[0.041, 0.373], b28=[0.045, 0.319] | yes |
| 5 | beats climatology overall and persistence in May-Aug | mae_prod=0.7508, mae_clim=1.1527, mae_prod_may_aug=0.8888, mae_pers_may_aug=0.8312 | NO |
| 6 | chronology assertions pass and 24h-delay sensitivity keeps positive skill | chronology_passed=True, S_delay1=0.2819 | yes |
