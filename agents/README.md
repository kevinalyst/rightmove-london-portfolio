Agents — Snowflake Cortex Analyst & Search

Overview
- Analyst: structured Q&A over semantic view `RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.RIGHTMOVE_ANALYSIS`
- Search: hybrid semantic over descriptions/key_features via Cortex Search service `UNSTRUCTURED_RAG`

Usage
1) Ensure transformed data exists in `RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF`.
2) Open Snowflake Worksheets and run example SQL in this folder against `RIGHTMOVE_ANALYSIS`.

Notes
- Ground prompts with table/view names and business context.
- Evaluate with small, curated questions first; guard for hallucinations.

