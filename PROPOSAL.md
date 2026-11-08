# Proposal: Supplier Catalog Intelligence

## The question

An interior design team receives product information from several suppliers. One sends Excel sheets, another sends CSV files, and others send PDF catalogues, scanned pages, or product photos. Can we pull the useful facts out of all of them and make a comparison the team can actually trust?

The comparison should answer things like: Which suppliers offer the material and finish we need? Are these products really comparable? What is the unit price? What will delivery cost, and when could the order arrive? Where did each answer come from?

## The task

Build a reproducible document and product intelligence workflow that reads mixed supplier files, extracts product and delivery details, links images to the right products, normalizes the data, and produces a side-by-side report. Every reported value should point back to a source file and location. Missing or uncertain information should stay visible so a person can check it.

The first version will focus on a small interior product category, such as chairs or lighting, and a few suppliers. It should compare actual purchase options, including variants, units, currencies, minimum order quantities, delivery fees, and lead times when those details are available. A quote with no shipping information is incomplete, not free shipping.

This is an independent public portfolio project inspired by real procurement and interior design briefs. It is not commissioned by, affiliated with, or endorsed by the clients behind those briefs.

## Planned approach

1. **Collect and inventory files.** Keep source files, hashes, dates, and supplier names in a manifest. Record access and reuse terms for each source. Keep private supplier files out of the public repository.
2. **Read each format properly.** Parse CSV and Excel cells directly. Extract text and tables directly from digital PDFs. Render scanned pages and images for OCR. Use OpenCV for deskewing, denoising, contrast fixes, and simple line-based table detection where it helps.
3. **Understand pages and products.** Compare a classical CV/layout baseline with a suitable learned document model. Detect tables and product-card regions; connect text, prices, and pictures on the same page. OCR supplies words and boxes. A table structure model such as Table Transformer is a strong candidate for difficult tables.
4. **Extract a consistent record.** Capture supplier, source reference, SKU, product name, category, material, finish, dimensions, variant, quantity/unit, currency, unit price, MOQ, availability, delivery charge, delivery condition, and lead time. Keep raw values beside normalized values. Use a constrained extractor where simple parsing rules fail, and validate types, units, and arithmetic.
5. **Match products carefully.** Start with SKU, manufacturer ID, and exact specs. Add text and image similarity for candidate matching, then require compatible dimensions, material, pack size, and variant. Give each match a reason and confidence; send doubtful cases to review.
6. **Compare landed cost and timing.** Show price per comparable unit, shipping, tax assumptions, currency conversion date/rate when relevant, and estimated delivered total. Report lead-time ranges and missing terms explicitly. Generate a CSV/Excel report and a short, source-linked summary.

### Where computer vision fits

- **Classical:** OpenCV preprocessing, morphology, contours, and line detection for scans and simple tables.
- **Document models:** A DETR-style table model and, if needed, a page-layout detector for tables, product blocks, captions, and images.
- **Product images:** A pretrained ResNet or modern image embedding model can help retrieve visually similar products. Images are supporting evidence, not proof of exact material or specifications.
- **Optional segmentation:** U-Net, SegFormer, or SAM only if a concrete task needs masks, such as separating fabric swatches or products from catalogue backgrounds. YOLO is an option if locating product images or cards is a measured bottleneck. We will choose models based on error analysis rather than add every architecture to the pipeline.

## Data plan

No single public dataset I found covers linked supplier spreadsheets, scanned catalogues, product images, prices, delivery fees, and lead times. The plan is to combine public task datasets with a small, clearly documented end-to-end benchmark.

| Source | What it helps with | What it does not provide |
| --- | --- | --- |
| [DocILE](https://github.com/rossumai/docile) | Business-document OCR, fields, and line items | Interior supplier comparisons |
| [DocLayNet](https://github.com/DS4SD/DocLayNet) | Page layout from PDF and page images | Product prices and shipping ground truth |
| [PubTables-1M / Table Transformer](https://github.com/microsoft/table-transformer) | Table detection and structure | Supplier-specific decisions |
| [Amazon Berkeley Objects](https://www.amazon.science/code-and-datasets/amazon-berkeley-objects-abo-dataset) | Household-product images and metadata, including materials | Quotations or delivery terms |
| [Neumärker public product files](https://www.neumaerker.de/en/price-lists-product-data) | A real Excel/CSV price-list example | Interior-focused, fully linked multi-supplier data |

For the end-to-end set, collect a few permitted public catalogues and price lists, then create realistic synthetic quotes and delivery sheets with known answers. Annotate a small set by hand, including file/page/cell evidence. Keep original train, validation, and test documents separate by supplier or template so near-identical pages do not leak across splits. Check every source's licence before downloading, redistributing, or publishing derived data.

## Evaluation: does it actually help?

- **Extraction:** Field-level precision, recall, and F1 for names, SKUs, materials, dimensions, prices, fees, and lead times. Exact and numeric-tolerance accuracy for amounts and units.
- **Tables and layout:** Detection precision/recall, cell or row structure quality, and OCR word error rate on a small labelled scan set.
- **Matching:** Precision, recall, and F1 for same-product or truly comparable-product pairs. Measure how often the right option appears in the top few suggestions, and inspect false matches closely.
- **Comparison maths:** Correct normalized unit prices and landed totals on a fixed answer key. Count missing delivery terms that are correctly left unknown.
- **Trust and workflow:** Evidence-link accuracy, calibration of confidence flags, review workload, and time to finish a supplier comparison versus a manual baseline.
- **Robustness:** Check scans, rotated pages, mixed currencies and units, updated price lists, and unseen supplier layouts. Freeze the final holdout before tuning.

The first milestone is a complete, reviewable comparison for roughly three suppliers and 30–50 products. It should work across at least one spreadsheet, one digital PDF, and one scanned catalogue. The report should show successful comparisons, mistakes, and cases that need a human decision.

## Writing and coding style

Keep **all project docs, reports, interface text, comments, and code explanations casual, clear, and useful**. Write like a teammate explaining what the system does and where it gets confused. Avoid academic phrasing, paper-style claims, and jargon for its own sake. Use normal, readable names in code; short comments should explain the reason for a choice, not narrate obvious syntax. Accuracy, source links, and honest limitations still matter.

## Scope right now

This repository is only the handoff and proposal. There is no data pipeline, model, application, dataset download, or benchmark result yet. The methodology and model choices above are plans to test, not claims that they already work.
