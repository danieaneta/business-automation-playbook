# Blueprint 04 -- CFPB Real-Data Routing Validation

Engine: imported from 04-support-ticket-routing/src (classify + route).
Data:   data/cfpb_sample.json (CFPB-schema consumer complaints).
Label:  CFPB Product -> support topic (see adapter.py; a coarse proxy).

## Summary

Total records:           32
Skipped (empty narrative): 2
Scored:                  30
Routing-match accuracy:  63.3%  (19/30)

## Per-topic breakdown (expected topic -> match rate)

    topic       scored   matched   rate
    ---------   ------   -------   -----
    account          5         3     60%
    billing         13        10     77%
    general          7         3     43%
    technical        5         3     60%

## 5 worked examples (subject -> predicted vs expected)

    [OK ] Problem with a purchase shown on your statement
           predicted: billing    expected: billing
    [OK ] Fees or interest
           predicted: billing    expected: billing
    [OK ] Managing an account
           predicted: account    expected: account
    [OK ] Closing an account
           predicted: account    expected: account
    [OK ] Trouble during payment process
           predicted: billing    expected: billing

Note: topics in scope are billing/technical/account/sales/general.
CFPB is a financial-product taxonomy and does not map cleanly to a
support desk, so this measures routing behaviour, not gold-label accuracy.
