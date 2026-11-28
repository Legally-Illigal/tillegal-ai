# Live Query → Search → Judge → Summary example

Question: Nhà cũ tại Cần Thơ chưa có chống sét nhưng được yêu cầu lắp bổ sung thì phải làm gì, và hệ thống phải có những bộ phận nào?

Selected real execution artifacts, published at the user’s request. Query/Search/Judge come from `live-20261128-181726`; Summary comes from `summary-readable-03`, reusing the same validated Judge carrier. These are sequential API/script stages, not an integrated LangGraph orchestration run.

Files are numbered by stage: 01–02 Query input/output; 03–04 Search input/output; 05–06 Judge input/output; 07 Judge telemetry; 08–09 Summary input/output; 10 Summary telemetry. Summary input includes the original carrier for traceability. Scores and stored hashes are not legal-verification verdicts.

Search uses the configured Supabase corpus; membership specifically in the 10/11 crawl batch has not been independently verified. Summary is a draft, not a verified legal answer. No Verify stage or quality gold evaluation is claimed. Provider/model identifiers and limitations are preserved in the JSON. Gemini calls are live, not fixture replay.

Only selected artifacts are published here; `.env`, credentials and other local outputs remain excluded. Do not use these files as fixtures that pretend to be a new live run.
