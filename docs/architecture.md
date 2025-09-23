## Architecture

```mermaid
flowchart LR
  A[Playwright Scraper] -->|ndjson/csv| B[GCS Bucket]
  B --> C[Snowflake Staging]
  C --> D[CTEs Transform]
  D --> E[RIGHTMOVE_ANALYSIS (Semantic View)]
  E --> F[Cortex Analyst]
  E --> G[Cortex Search]

  subgraph Runtime
  A
  end
  subgraph Cloud Run Job
  A
  end
```

