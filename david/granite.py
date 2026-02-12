from docling.datamodel import vlm_model_specs
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    VlmPipelineOptions
)
from docling.datamodel.pipeline_options_vlm_model import (
    InlineVlmOptions, ApiVlmOptions,
    InferenceFramework,
    ResponseFormat,
    TransformersModelType,
    TransformersPromptStyle,
)
from docling.datamodel.accelerator_options import AcceleratorDevice
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.datamodel.settings import settings
import pandas as pd
                        
source = "/mnt/c/Users/yyb19161/Documents/testdoc.pdf"
source = "/mnt/c/Users/yyb19161/Documents/Click here for full details.pdf"
# source = "/mnt/c/Users/yyb19161/Documents/Self-Certification_Form.pdf"
source = "https://arxiv.org/pdf/2501.17887" 

# a = InlineVlmOptions(
#     repo_id="ibm-granite/granite-docling-258M",
#     prompt="Convert this page to docling.",
#     response_format=ResponseFormat.DOCTAGS,
#     inference_framework=InferenceFramework.TRANSFORMERS,
#     transformers_model_type=TransformersModelType.AUTOMODEL_IMAGETEXTTOTEXT,
#     supported_devices=[
#         AcceleratorDevice.CPU,
#         AcceleratorDevice.CUDA
#     ],
#     extra_generation_config=dict(skip_special_tokens=False),
#     scale=2.0,
#     temperature=0.0,
#     max_new_tokens=8192,
#     stop_strings=["</doctag>", "<|end_of_text|>"],
# )

BATCH_SIZE = 8
settings.perf.page_batch_size = 8

# Configure VLM options
# pipeline_options = VlmPipelineOptions(
#         enable_remote_services=True  # required when calling remote VLM endpoints
#     )
# pipeline_options.vlm_options = vlm_model_specs.GRANITEDOCLING_VLLM_API
# pipeline_options.vlm_options.concurrency = BATCH_SIZE
# pipeline_options.vlm_options.params["model"] = "ibm-granite/granite-docling-258M"
# pipeline_options.vlm_options.params["max_tokens"] = 4096
# pipeline_options.vlm_options.params["skip_special_tokens"] = False
# pipeline_options.vlm_options.timeout = 120

# print(pipeline_options.vlm_options)
# settings.perf.page_batch_size = BATCH_SIZE

# vlm_options = VlmPipelineOptions(
#     enable_remote_services=True,
#     vlm_options={
#         "url": "http://localhost:8000/v1/chat/completions",  # or any other compatible endpoint
#         "params": {
#             "model": "ibm-granite/granite-docling-258M",
#             "max_tokens": 4096,
#         },
#         "concurrency": 64,  # default is 1
#         "prompt": "Convert this page to docling.",
#         "timeout": 300,
#         "response_format": ResponseFormat.DOCTAGS,
#         "temperature": 0.0
#     }
# )

vlm_optionss = VlmPipelineOptions(
    enable_remote_services=True,
    vlm_options=ApiVlmOptions(
        url="http://localhost:8000/v1/chat/completions",  # LM studio defaults to port 1234, VLLM to 8000
        params={
            "model": "ibm-granite/granite-docling-258M",
            "max_tokens": 4096,
            "skip_special_tokens": False,
        },
        prompt="Convert this page to docling. Convert any tables to OTSL",
        timeout=900,
        scale=2.0,
        temperature=0.0,
        concurrency=8,
        stop_strings=["</doctag>", "<|end_of_text|>"],
        response_format=ResponseFormat.DOCTAGS,
    )
)


# Create converter with VLM pipeline
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_cls=VlmPipeline, pipeline_options=vlm_optionss
        ),
    }
)
converter.initialize_pipeline(InputFormat.PDF)
# from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
# pipeline_options = VlmPipelineOptions(
#     accelerator_options=AcceleratorOptions(
#         num_threads=12, device=AcceleratorDevice.CUDA
#     ),
#     vlm_options=a,
# )

# converter = DocumentConverter(
#     format_options={
#         InputFormat.PDF: PdfFormatOption(
#             pipeline_cls=VlmPipeline, pipeline_options=pipeline_options
#         ),
#     }
# )

result = converter.convert(source=source)
doc = result.document
markdown_content = doc.export_to_markdown()
print(doc.export_to_text())
print(doc.export_to_doctags())
print(result.document.export_to_markdown())

tables = []
for i, table in enumerate(doc.tables, 1):
    df = table.export_to_dataframe(doc=doc)
    tables.append(df)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)

print(tables)

