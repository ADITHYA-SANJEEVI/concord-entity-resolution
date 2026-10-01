# Architecture

## System boundary

The historical pipeline accepts organizer TSV directories and produces two TSVs: one with the full candidate set per Source-1 record and one with accepted matches. It performs no external business lookup, geocoding, registry query, or web search.

## Retrieval

Retrieval runs independently by country. Names and addresses use Unicode NFKD decomposition, combining-mark removal, and case folding. Query and target text jointly fit deterministic TF-IDF vectorizers from a seed-0 sample capped at 3,000,000 records per country and view.

| View | Representation | Depth |
|---|---|---:|
| Name | `char_wb` trigrams | 5 |
| Compact name | spaces removed, character trigrams | 5 |
| Address | `[a-z0-9]+` word unigrams | 5 |
| Combined | separately L2-normalized name and address, equal weight | 10 |
| Reverse combined | targets query Source 1 | 8 |

Vectorizers use float32, `min_df=2`, `max_df=0.05`, sublinear term frequency, smoothed IDF, and L2 normalization. Sparse top-K multiplication avoids a full Cartesian similarity matrix. The five outputs are unioned on `(s1_id, target_id)`.

## Features

The 55 base features cover normalized name and address similarity, numeric agreement, exact TF-IDF cosine values, retrieval ranks, query and target rank context, rival margins, candidate counts, and target competition.

The additional four features are:

- `f55`: transliterated-name character-trigram Jaccard.
- `f56`: maximum RapidFuzz ratio across original and transliterated name combinations.
- `f57`: dominant-script difference indicator.
- `f58`: transliterated-address token Jaccard.

All 59 inputs are float32 and must follow the exact order in `ordered_59_feature_schema.json`.

## Model

The classifier is `LGBMClassifier` with 600 estimators, learning rate 0.05, 63 leaves, minimum 100 samples per child, L2 regularization 1, full row and column sampling, and random seed 42. Training used 3,376,945 labeled candidate rows, no class weights, and no early stopping.

## Decision policy

The model emits pair probabilities. Before thresholding, every S2 or S3 target is assigned to the S1 record with the highest score. Equal scores are resolved by ascending `s1_id`. A probability threshold of 0.64 is then applied to both sources.

Accepted targets within each Source-1 row are ordered by score descending, then target ID ascending. Candidate IDs are ordered by target ID. All Source-1 rows are emitted, including empty match rows.

## Historical and future boundaries

Files under `src/concord/legacy_amazon/` are the historical implementation and should not be silently refactored. New implementations belong in the neighboring Concord modules and should be compared against the frozen contracts before replacing any historical behavior.
