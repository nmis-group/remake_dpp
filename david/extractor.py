from docling.datamodel.base_models import InputFormat
from docling.document_extractor import DocumentExtractor

extractor = DocumentExtractor(allowed_formats=[InputFormat.IMAGE, InputFormat.PDF])

result = extractor.extract(
    source="/home/david/projects/doclingtest/output_000.jpg",
    template='{"salary_range": "string"}',
)
print(result.pages)