from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmPipelineOptions, PdfPipelineOptions, TableFormerMode
from docling.pipeline.vlm_pipeline import VlmPipeline
import pandas as pd
from docling.datamodel.pipeline_options_vlm_model import InlineVlmOptions, InferenceFramework, TransformersModelType, ResponseFormat
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 2.0
pipeline_options.accelerator_options=AcceleratorOptions(
        num_threads=12, device=AcceleratorDevice.CUDA
)

# pipeline_options = VlmPipelineOptions(
#     vlm_options=InlineVlmOptions(
#         repo_id="ibm-granite/granite-docling-258m",
#         prompt="Convert this page to markdown. Do not miss any text and only output the bare markdown!",
#         response_format=ResponseFormat.MARKDOWN,
#         inference_framework=InferenceFramework.TRANSFORMERS,
#         transformers_model_type=TransformersModelType.AUTOMODEL_VISION2SEQ,
#         supported_devices=[
#             AcceleratorDevice.CPU,
#             AcceleratorDevice.CUDA
#         ],
#         scale=2.0,
#         temperature=0.0,
#     accelerator_options=AcceleratorOptions(
#         num_threads=12, device=AcceleratorDevice.CUDA
#     )
#     )
# )

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)
word_converter = DocumentConverter(
    format_options={InputFormat.DOCX: WordFormatOption(pipeline_options=pipeline_options)}
)

# filepath = "/mnt/c/Users/yyb19161/Documents/Click here for full details.pdf"
#filepath = "/mnt/c/Users/yyb19161/Downloads/Data management in digital twins a systematic literature review, Knowledge and Information Systems.pdf"
filepath = "/mnt/c/Users/yyb19161/Documents/Self-Certification_Form.pdf"
# filepath = "/mnt/c/Users/yyb19161/Downloads/Self-Triage_Product_All_Sectors_V2 1.xlsx"

# Process the document with Docling
result = converter.convert(filepath)
#print(result)

tables = []
for i, table in enumerate(result.document.tables, 1):
    df = table.export_to_dataframe(doc=result.document)
    tables.append(df)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)

print(tables)
# Export to markdown
markdown_content = result.document.export_to_markdown()
print(markdown_content)
print(result.document.export_to_doctags())

# for i, image in enumerate(result.document.pictures, 1):
#     image.image.pil_image.show()