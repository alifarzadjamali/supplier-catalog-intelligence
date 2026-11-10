# Next session: supplier catalog intelligence

## Where things stand

- `main` is pushed to `origin/main` at `b8af51a`. The project has 15 commits total, the agreed limit.
- The runnable baseline reads CSV, XLSX, and labelled digital PDF product rows. Optional Tesseract OCR handles image files and image-only PDF pages when installed.
- The invented demo has 36 chair options from three suppliers. Three unit/demo tests pass. Output includes source evidence, a comparison, and a review queue.
- The GitHub README has a workflow diagram and example comparison.
- Limits: no real-document benchmark yet; PDF extraction expects `PRODUCT |` rows; OCR is not verified locally; no learned document-layout or image model; no human correction interface.

## Do next, in order

1. **Make a labelled test set.** Find permitted real spreadsheet, ordinary digital PDF, scanned catalogue pages, and product images. Record access/reuse terms. Hand-label products, field values, page/cell evidence, image links, and expected comparisons. Keep private files out of Git.
2. **Set up and evaluate Tesseract.** Install the executable and Python extras, add representative scans, run OCR, and measure word/field errors. Try deskew, contrast, and denoising only where they improve measured results.
3. **Test document layout models.** Establish a simple PDF/OCR layout baseline, then evaluate Table Transformer or another suitable learned model on hard tables and product cards. Keep the model only if it improves the labelled set.
4. **Test image linking and matching.** Link page images to product records, then evaluate an image embedding model for candidate retrieval. Require compatible material, dimensions, variant, and pack size before suggesting a comparison.
5. **Add human review and evaluation.** Allow corrections with preserved original evidence. Report extraction, layout, OCR, image-link, and match metrics, plus arithmetic checks and unresolved delivery terms on held-out documents.

## Start tomorrow

Inspect the current repo and tests, then begin with the labelled test set and Tesseract setup. Do not claim the planned models work before measuring them. The 15-commit cap is already reached; ask about a new commit allowance before making another commit.
